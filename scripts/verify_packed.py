"""Verify isolated B3 arithmetic and factored reconstruction; no CPU/benchmarks."""
import copy
import itertools
import json
import platform
import random
import re
import resource
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "scripts"))
from model import xqdot4z as model
from verify_rtl import reference_evidence, require, sha

SEED = 20260912
COUNTS = dict(m1_vectors=2068, single_term_lane_placements=32768,
              mixed_extrema=8192, random_dot_products=20000,
              unused_half_vectors=2048, single_input_bit_transitions=130,
              z_sweep=1024, matrix_blocks=1680)
MUTATIONS = {
    "signed_u4_weights": ("$signed({1'b0, selected_weights[4*lane +: 4]})",
                          "$signed(selected_weights[4*lane +: 4])"),
    "unsigned_activations": ("wire signed [7:0] activation", "wire [7:0] activation"),
    "ignore_half": ("half ? weights_word[31:16] : weights_word[15:0]", "weights_word[15:0]"),
    "zero_extend_result": ("{{17{subtotal[14]}}, subtotal}", "{17'b0, subtotal}"),
}


def sources():
    files = {ROOT/p for p in ("scripts/verify_packed.py", "scripts/verify_rtl.py",
                              "rtl/xqdot4z.v", "rtl/packed/SPEC.md")}
    for pattern in ("rtl/packed/*.v", "tests/packed/*.sv", "model/*.py"):
        files.update(ROOT.glob(pattern))
    return sorted(files)


def signed(bits):
    return bits if bits < (1 << 31) else bits - (1 << 32)


def make_vectors(path, pinned):
    counts = dict.fromkeys(COUNTS,0)
    lines = []
    def emit(group,w,a,z,h,expected_p=None,expected_d=None):
        weights = [int(n,16) for n in f"{w:08x}"[::-1]][4*h:4*h+4]
        acts = struct.unpack("4b",a.to_bytes(4,"little"))
        p = sum(x*y for x,y in zip(weights,acts))
        d = p-z*sum(acts)
        require(expected_p is None or p==expected_p,"Directed P mismatch")
        require(expected_d is None or d==expected_d,"Directed d mismatch")
        require(model.qdot4z(w,a,0,h)==p and model.qdot4z(w,a,z,h)==d,"M1 mismatch")
        require(-7680<=p<=7620 and -7680<=d<=7680,"Result range")
        index = len(lines)
        lines.append(f"{w:08x} {a:08x} {z:x} {h:x} {p & 0xffffffff:08x} {d & 0xffffffff:08x}\n")
        counts[group]+=1
        return index

    for line in pinned.read_text().splitlines():
        w,a,z,h,d = (int(field,16) for field in line.split())
        emit("m1_vectors",w,a,z,h,expected_d=signed(d))
    for w,a,position in itertools.product(range(16),range(-128,128),range(8)):
        emit("single_term_lane_placements",w << (4*position),
             (a & 255) << (8*(position%4)),8,position//4,w*a,(w-8)*a)
    for z,h,wm,am in itertools.product(range(16),range(2),range(16),range(16)):
        weights = [15 if wm & (1 << i) else 0 for i in range(4)]
        acts = [-128 if am & (1 << i) else 127 for i in range(4)]
        w = (sum(x << (4*i) for i,x in enumerate(weights)) << (16*h)) | (0x5a5a << (16*(1-h)))
        a = int.from_bytes(struct.pack("4b",*acts),"little")
        emit("mixed_extrema",w,a,z,h)
    rng = random.Random(SEED)
    for _ in range(10000):
        w,a,z = rng.getrandbits(32),rng.getrandbits(32),rng.randrange(16)
        for h in (0,1): emit("random_dot_products",w,a,z,h)
    for _ in range(1024):
        w,a,z,h = rng.getrandbits(32),rng.getrandbits(32),rng.randrange(16),rng.randrange(2)
        emit("unused_half_vectors",w,a,z,h)
        emit("unused_half_vectors",w ^ (0xffff << (16*(1-h))),a,z,h)
    base = [0x78f04a95,0x02ff7f80,8,0]
    for port,width in ((0,32),(1,32),(3,1)):
        for bit in range(width):
            emit("single_input_bit_transitions",*base)
            changed = base.copy(); changed[port] ^= 1 << bit
            emit("single_input_bit_transitions",*changed)
    for _ in range(32):
        w,a = rng.getrandbits(32),rng.getrandbits(32)
        for h,z in itertools.product(range(2),range(16)):
            emit("z_sweep",w,a,z,h)

    matrix_start = len(lines)
    fixtures = []
    for n,g,mode in itertools.product((1,4,16),(8,32),("z0","z8","z15","row_group")):
        k,groups = 2*g,2
        acts = [rng.randrange(-128,128) for _ in range(k)]
        weights = [[rng.randrange(16) for _ in range(k)] for _ in range(n)]
        # One activation vector shared by all rows; retain one Sa per group.
        sums = [sum(acts[group*g:(group+1)*g]) for group in range(groups)]
        case = dict(name=f"n{n}_g{g}_{mode}",n=n,k=k,g=g,groups=groups,
                    zero_point_mode=mode,activations=acts,weights=weights,
                    activation_sums=sums,outputs=[])
        for row,group in itertools.product(range(n),range(groups)):
            z = (row+7*group)%16 if mode=="row_group" else int(mode[1:])
            begin,end = group*g,(group+1)*g
            indices = []
            for start in range(begin,end,4):
                base_word = start-start%8
                w = sum(x << (4*i) for i,x in enumerate(weights[row][base_word:base_word+8]))
                a = int.from_bytes(struct.pack("4b",*acts[start:start+4]),"little")
                indices.append(emit("matrix_blocks",w,a,z,(start%8)//4))
            direct = sum((weights[row][i]-z)*acts[i] for i in range(begin,end))
            factored = sum(weights[row][i]*acts[i] for i in range(begin,end))-z*sums[group]
            require(direct==factored,"Matrix reference mismatch")
            case["outputs"].append(dict(row=row,group=group,z=z,indices=indices,expected=direct))
        fixtures.append(case)
    require(counts==COUNTS,f"Incomplete B3 campaign: {counts}")
    path.write_text("".join(lines))
    return counts,matrix_start,fixtures


def observations(log, start, total):
    require(f"PACKED_PASS checked={total}" in log and "PACKED_FAIL" not in log,"Incomplete packed simulation")
    records = re.findall(r"PACKED_OBS\|(\d+)\|([0-9a-f]{8})\|([0-9a-f]{8})",log)
    require([int(row[0]) for row in records]==list(range(start,total)),"Missing/duplicate/out-of-order matrix block")
    return {int(index):(signed(int(p,16)),signed(int(d,16))) for index,p,d in records}


def check_matrices(fixtures, observed, vectors):
    outputs,distinct_sums,used = 0,0,[]
    for case in fixtures:
        g,n,k,groups = (case[key] for key in ("g","n","k","groups"))
        acts,weights = case["activations"],case["weights"]
        require(k==g*groups and g%8==0 and len(acts)==k,"Matrix dimensions")
        require(len(weights)==n and all(len(row)==k for row in weights),"Weight dimensions")
        require(all(type(a) is int and -128<=a<=127 for a in acts),"Activation range")
        require(all(type(w) is int and 0<=w<=15 for row in weights for w in row),"Weight range")
        sums = [sum(acts[group*g:(group+1)*g]) for group in range(groups)]
        require(sums==case["activation_sums"],"Wrong activation group sum")
        distinct_sums+=groups
        require([(o["row"],o["group"]) for o in case["outputs"]]==
                list(itertools.product(range(n),range(groups))),"Missing/duplicate matrix output")
        for output in case["outputs"]:
            row,group,z = (output[key] for key in ("row","group","z"))
            require(type(z) is int and 0<=z<=15,"Zero-point range")
            begin,end = group*g,(group+1)*g
            indices = output["indices"]
            require(len(indices)==g//4,"Missing matrix block")
            for start,index in zip(range(begin,end,4),indices):
                base_word = start-start%8
                w = sum(x << (4*i) for i,x in enumerate(weights[row][base_word:base_word+8]))
                a = int.from_bytes(struct.pack("4b",*acts[start:start+4]),"little")
                require(vectors[index][:4]==[w,a,z,(start%8)//4],"Matrix block/input binding mismatch")
            direct = sum((weights[row][i]-z)*acts[i] for i in range(begin,end))
            p = sum(observed[i][0] for i in indices)
            d = sum(observed[i][1] for i in indices)
            require(output["expected"]==direct,"Matrix reference mismatch")
            require(p-z*sums[group]==d==direct,"RTL matrix reconstruction mismatch")
            used.extend(indices); outputs+=1
    require(len(used)==len(set(used)) and set(used)==set(observed),"Matrix block coverage mismatch")
    return dict(cases=len(fixtures),group_outputs=outputs,distinct_vector_group_sums=distinct_sums,rtl_blocks=len(used))


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT/"tests/packed/results"/stamp
    out.mkdir(parents=True,exist_ok=False)
    report = dict(status="running",timestamp_utc=stamp,seed=SEED,contract_version="0.1",
                  scope="Isolated B3 arithmetic and host-side reconstruction; no CPU integration or performance",
                  python=sys.version,platform=platform.platform(),commands=[],simulators={},
                  sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
    def run(name,args,fail=False):
        args=list(map(str,args))
        p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=180)
        log=p.stdout+p.stderr
        (out/f"{name}.log").write_text(log)
        report["commands"].append(dict(name=name,argv=args,returncode=p.returncode))
        require(p.returncode!=0 if fail else p.returncode==0,f"{name}: unexpected exit; see log")
        return log
    try:
        pinned,reference=reference_evidence()
        report["reference"]=reference
        state_path=ROOT/"docs/RTL_STATE.json"
        state=json.loads(state_path.read_text())
        evidence=ROOT/state["evidence"]
        require(sha(evidence)==state["evidence_sha256"],"Stale M2 evidence")
        m2=json.loads(evidence.read_text())
        require(m2["status"]=="pass","M2 not verified")
        for name,digest in m2["sources_sha256"].items():
            require(sha(ROOT/name)==digest,f"Stale M2 source: {name}")
        report["fused_reference"]=dict(state="docs/RTL_STATE.json",state_sha256=sha(state_path),
                                       evidence=state["evidence"],evidence_sha256=sha(evidence))
        report["tools"]={}
        for tool,flag in (("iverilog","-V"),("verilator","--version"),("make","--version"),("g++","--version")):
            report["tools"][tool]=run("version_"+tool,[tool,flag]).splitlines()[0]
        vectors_path=out/"vectors.txt"
        counts,start,fixtures=make_vectors(vectors_path,pinned)
        total=sum(counts.values())
        report.update(completed_counts=counts,vectors_count=total,matrix_trace_start=start)
        (out/"matrix_cases.json").write_text(json.dumps(fixtures,indent=2)+"\n")
        vector_fields=[[int(x,16) for x in line.split()] for line in vectors_path.read_text().splitlines()]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-packed-") as temporary:
            build=Path(temporary)
            unit=ROOT/"rtl/packed/xqdot4.v"
            fused=ROOT/"rtl/xqdot4z.v"
            bench=ROOT/"tests/packed/tb_packed.sv"
            run("lint",["verilator","--lint-only","-Wall","--top-module","xqdot4",unit])
            report["lint"]="pass_no_waivers"
            run("iverilog_build",["iverilog","-g2012","-s","tb_packed","-o",build/"packed.vvp",unit,fused,bench])
            run("verilator_build",["verilator","--binary","--timing","--top-module","tb_packed",
                                   "--Mdir",build/"obj","-j","2",unit,fused,bench])
            commands={"iverilog":["vvp",build/"packed.vvp"],"verilator":[build/"obj/Vtb_packed"]}
            valid="00004a95 0102fd04 8 0 00000011 fffffff1\n"
            controls=dict(wrong_p=(valid.replace("00000011","00000012"),1,"packed mismatch"),
                          wrong_d=(valid.replace("fffffff1","fffffff0"),1,"fused mismatch"),
                          empty=("",1,"vector count"),truncated=(valid[:-10]+"\n",1,"malformed"),
                          trailing_partial=(valid+"0",1,"malformed"),extra_field=(valid[:-1]+" 0\n",1,"malformed"),
                          bad_hex=(valid.replace("4a95","4x95"),1,"malformed"),
                          bad_half=(valid.replace(" 8 0 "," 8 2 "),1,"out-of-range"),
                          count_mismatch=(valid,2,"vector count"),missing_file=(None,1,"cannot open"))
            observed_runs={}
            for sim,command in commands.items():
                log=run(sim,[*command,f"+VECTORS={vectors_path}",f"+COUNT={total}",f"+TRACE_FROM={start}"])
                observed=observations(log,start,total)
                matrix_result=check_matrices(fixtures,observed,vector_fields)
                require(matrix_result==dict(cases=24,group_outputs=336,distinct_vector_group_sums=48,rtl_blocks=1680),"Matrix counts")
                detected={}
                for name,(data,count,reason) in controls.items():
                    path=out/f"negative_{name}.txt"
                    if data is not None: path.write_text(data)
                    log=run(f"negative_{name}_{sim}",[*command,f"+VECTORS={path}",f"+COUNT={count}"],fail=True)
                    require(f"PACKED_FAIL {reason}" in log,"Unrelated negative-control failure")
                    detected[name]=reason
                report["simulators"][sim]=dict(checked=total,matrix_reconstruction=matrix_result,negative_controls_detected=detected)
                observed_runs[sim]=observed
                print(f"PASS {sim}: {total} paired vectors, 24 matrix fixtures, 10 negative controls",flush=True)
            require(observed_runs["iverilog"]==observed_runs["verilator"],"Matrix RTL traces differ")
            report["matrix_controls_detected"]={}
            for name,reason in (("wrong_group_sum","Wrong activation group sum"),("missing_block","Missing matrix block")):
                changed=copy.deepcopy(fixtures)
                if name=="wrong_group_sum": changed[0]["activation_sums"][0]+=1
                else: changed[0]["outputs"][0]["indices"].pop()
                (out/f"negative_matrix_{name}.json").write_text(json.dumps(changed,indent=2)+"\n")
                try: check_matrices(changed,observed_runs["iverilog"],vector_fields)
                except RuntimeError as error:
                    require(reason in str(error),"Unrelated matrix negative-control failure")
                    report["matrix_controls_detected"][name]=str(error)
                else: raise RuntimeError(f"Undetected matrix control: {name}")
            report["mutations_detected"]={}
            original=unit.read_text()
            for name,(before,after) in MUTATIONS.items():
                require(original.count(before)==1,f"Mutation site changed: {name}")
                mutant=out/f"mutant_{name}.v"
                mutant.write_text(original.replace(before,after))
                run(name+"_build",["iverilog","-g2012","-s","tb_packed","-o",build/"mutant.vvp",mutant,fused,bench])
                log=run(name,["vvp",build/"mutant.vvp",f"+VECTORS={vectors_path}",f"+COUNT={total}"],fail=True)
                require("PACKED_FAIL packed mismatch" in log,"Unrelated RTL mutation failure")
                report["mutations_detected"][name]="packed arithmetic mismatch"
            for source in sources():
                target=out/"sources"/source.relative_to(ROOT)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
            require(report["sources_sha256"]=={str(p.relative_to(ROOT)):sha(p) for p in sources()},"Sources changed during verification")
            report["status"]="pass"
    except Exception as error:
        report["status"]="fail"; report["error"]=f"{type(error).__name__}: {error}"
        raise
    finally:
        report["artifacts_sha256"]={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
        (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
        print("Evidence:",out,flush=True)
        print("Status:",report["status"],flush=True)


if __name__=="__main__": main()
