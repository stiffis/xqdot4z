"""B3 ISA/pipeline verification, with bounded CPU correction fixtures; no speedup."""
import itertools
import json
import platform
import re
import resource
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
sys.path.insert(0,str(ROOT / "tests/packed_integration"))
import verify_scalar as scalar
from oracle import execute
from programs import programs, matrix_fixtures, SEED
from isa.packed.xqdot4 import encode, decode, VERSION

require, sha, PREFIX = scalar.require, scalar.sha, scalar.PREFIX
CONFIGS = list(itertools.product(range(2),repeat=3)) # MUL, D, B3


def sources():
    files = set(scalar.sources())
    files.update(ROOT/p for p in ("scripts/verify_packed_integration.py", "isa/packed/SPEC.md", "rtl/packed/xqdot4.v"))
    for pattern in ("isa/packed/*.py", "isa/packed/*.inc", "tests/packed_integration/*.py", "tests/packed_integration/*.sv"):
        files.update(ROOT.glob(pattern))
    return sorted(files)


def compare(log, expected, name):
    result = scalar.compare(log,expected,name)
    observed = [[int(x,16) for x in row] for row in re.findall(
        r"PEXEC\|([0-9a-f]+)\|([0-9a-f]+)\|([0-9a-f]+)\|([0-9a-f]+)\|\d+\|\d+",log)]
    require(observed==expected["packed_dots"],f"{name}: packed execute operands/selector mismatch")
    result["packed_dots"] = len(observed)
    return result


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT/"tests/packed_integration/results"/stamp
    out.mkdir(parents=True,exist_ok=False)
    report = dict(status="running",timestamp_utc=stamp,isa_version=VERSION,seed=SEED,
                  scope="B3 ISA and CPU correctness fixtures, not performance evaluation",
                  python=sys.version,platform=platform.platform(),configurations=CONFIGS,
                  sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()},commands=[],programs={})
    def run(name,args,fail=False):
        args = list(map(str,args))
        p = subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=240)
        log = p.stdout+p.stderr
        (out/f"{name}.log").write_text(log)
        report["commands"].append(dict(name=name,argv=args,returncode=p.returncode))
        require(p.returncode!=0 if fail else p.returncode==0,f"{name}: unexpected exit; see log")
        return log
    try:
        report["reference_states"]={}
        for name in ("MODEL_STATE","RTL_STATE","PACKED_STATE"):
            path = ROOT/f"docs/{name}.json"
            state = json.loads(path.read_text()); evidence = ROOT/state["evidence"]
            require(sha(evidence)==state["evidence_sha256"],f"Stale reference: {name}")
            ref = json.loads(evidence.read_text())
            require(ref["status"]=="pass",f"Unverified reference: {name}")
            for source,digest in ref["sources_sha256"].items():
                require(sha(ROOT/source)==digest,f"Stale reference source: {source}")
            report["reference_states"][name]=dict(state=state,state_sha256=sha(path))
        report["tools"]={}
        for tool,flag in (("iverilog","-V"),("verilator","--version"),("make","--version"),("g++","--version"),
                          (PREFIX+"as","--version"),(PREFIX+"ld","--version"),(PREFIX+"objcopy","--version"),(PREFIX+"nm","--version")):
            report["tools"][tool]=run("version_"+tool,[tool,flag]).splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-b3-cpu-") as temporary:
            build = Path(temporary)
            def assemble(name,body,prolog=True):
                source = out/f"{name}.S"
                initialization = "".join(f"addi x{i},x0,0\n" for i in range(1,32)) if prolog else ""
                source.write_text('.include "xqdot4zi.inc"\n.include "xqdot4.inc"\n.option norelax\n.option norvc\n.text\n.global _start\n_start:\n'+initialization+body)
                run(name+"_as",[PREFIX+"as","-I",ROOT/"isa","-I",ROOT/"isa/packed","-march=rv32imc","-mabi=ilp32",
                               "-mno-relax","-o",build/f"{name}.o",source])
                run(name+"_ld",[PREFIX+"ld","-m","elf32lriscv","--no-relax","-Ttext=0","-o",out/f"{name}.elf",build/f"{name}.o"])
                run(name+"_objcopy",[PREFIX+"objcopy","-O","binary","-j",".text",out/f"{name}.elf",out/f"{name}.bin"])
                symbols = run(name+"_nm",[PREFIX+"nm","-n",out/f"{name}.elf"])
                labels = {fields[2]:int(fields[0],16) for line in symbols.splitlines() if len(fields:=line.split())==3}
                return (out/f"{name}.bin").read_bytes(),labels

            combinations = list(itertools.product(range(32),range(32),range(32),range(2)))
            data,_ = assemble("encoding","".join(f"xqdot4 x{d},x{a},x{b},{h}\n" for d,a,b,h in combinations),False)
            require(len(data)==4*len(combinations),"Encoding length")
            for i,args in enumerate(combinations):
                word = int.from_bytes(data[4*i:4*i+4],"little")
                require(word==encode(*args) and list(decode(word).values())==list(args),"GNU encoding/roundtrip mismatch")
            report["encoding_pairs"]=len(combinations)
            invalid = [(-1,1,2,0),(32,1,2,0),(3,-1,2,0),(3,32,2,0),(3,1,-1,0),(3,1,32,0),
                       (3,1,2,-1),(3,1,2,2),(True,1,2,0)]
            for args in invalid:
                try: encode(*args)
                except (ValueError,TypeError): pass
                else: raise RuntimeError("Encoder accepted invalid input")
            report["encoder_rejections"]=len(invalid)
            decoded=0
            for opcode,f7,f3 in itertools.product((0x0b,0x2b),range(128),range(8)):
                word = (f7<<25) | (2<<20) | (1<<15) | (f3<<12) | (3<<7) | opcode
                valid = opcode==0x2b and f7 in (0,4) and f3==0
                try: fields=decode(word)
                except ValueError: require(not valid,"Decoder rejected legal encoding")
                else: require(valid and fields==dict(rd=3,rs1=1,rs2=2,half=f7//4),"Decoder accepted reserved encoding")
                decoded+=1
            report["python_decoder_checks"]=decoded
            for i,h in enumerate((-1,2)):
                fixture=out/f"bad_macro_{i}.S"
                fixture.write_text(f'.include "xqdot4.inc"\nxqdot4 x3,x1,x2,{h}\n')
                log=run(f"bad_macro_{i}",[PREFIX+"as","-I",ROOT/"isa/packed","-march=rv32ic","-mabi=ilp32",
                                          "-o",build/"bad.o",fixture],fail=True)
                require("xqdot4:" in log,"Unrelated macro failure")
            report["macro_rejections"]=2
            run("decode_build",["iverilog","-g2012","-s","tb_packed_decode","-o",build/"decode.vvp",
                                ROOT/"kuntur/rtl/instruction_policy.v",ROOT/"tests/packed_integration/tb_packed_decode.sv"])
            require("PACKED_DECODE_PASS checked=524288" in run("decode",["vvp",build/"decode.vvp"]),"Decode coverage")
            report["decoder_checks"]=524288
            print("PASS B3 encoding and decode",flush=True)

            rtl = sorted((ROOT/"kuntur/rtl").glob("*.v"))+[ROOT/"rtl/xqdot4z.v",ROOT/"rtl/packed/xqdot4.v"]
            bench = ROOT/"tests/integration/tb_integration.sv"
            commands={}
            for m,q,p in CONFIGS:
                cfg=f"m{m}q{q}p{p}"
                run(f"lint_{cfg}",["verilator","--lint-only","--timing","--timescale","1ns/1ps","-DSYNTHESIS","-Wall",
                                   "-Wno-VARHIDDEN","-Wno-UNUSEDSIGNAL","--top-module","top",
                                   f"-GENABLE_MUL={m}",f"-GENABLE_XQDOT4Z={q}",f"-GENABLE_XQDOT4={p}",*rtl])
                binary=build/f"{cfg}.vvp"
                run(f"iverilog_build_{cfg}",["iverilog","-g2012","-s","tb_integration",f"-Ptb_integration.ENABLE={q}",
                                             f"-Ptb_integration.ENABLE_MUL={m}",f"-Ptb_integration.ENABLE_PACKED={p}","-o",binary,*rtl,bench])
                commands[("iverilog",m,q,p)]=["vvp",binary]
                obj=build/cfg
                run(f"verilator_build_{cfg}",["verilator","--binary","--timing","--timescale","1ns/1ps","--top-module",
                                              "tb_integration",f"-GENABLE={q}",f"-GENABLE_MUL={m}",f"-GENABLE_PACKED={p}",
                                              "--Mdir",obj,"-j","2",*rtl,bench])
                commands[("verilator",m,q,p)]=[obj/"Vtb_integration"]
                print("PASS build/lint:",cfg,flush=True)
            forwarding={sim:{f"m{m}q{q}p1":[set(),set()] for m,q in itertools.product(range(2),repeat=2)}
                        for sim in ("iverilog","verilator")}
            fixtures={f["name"]:f for f in matrix_fixtures()}
            (out/"matrix_fixtures.json").write_text(json.dumps(fixtures,indent=2)+"\n")
            for case in programs():
                name=case["name"]
                data,labels=assemble(name,case["body"]+"ebreak\n")
                reset_pc=labels.get("reset_packed")
                expected=execute(data,case["q"],stop_before=reset_pc-8 if reset_pc is not None else None,
                                 mul_enabled=bool(case["m"]),packed_enabled=bool(case["p"]))
                if reset_pc is not None: expected["fault"]=[3,0]
                if "matrix" in case:
                    fixture=fixtures[case["matrix"]]
                    want=[[64+4*i,v & 0xffffffff] for i,v in enumerate(fixture["expected"])]
                    require(expected["stores"][-2:]==want,"CPU matrix oracle/tensor mismatch")
                    if case["fused"]: require(len(expected["qdots"])==4,"D matrix dot count")
                    else:
                        require(expected["regs"][11]==(fixture["activation_sum"] & 0xffffffff),"Sa reconstruction mismatch")
                        require(len(expected["packed_dots"])==6 and len(expected["muls"])==2,"B3 matrix operation count")
                (out/f"{name}.expected.json").write_text(json.dumps(expected,indent=2)+"\n")
                padded=data+bytes(-len(data)%4)
                require(len(padded)<=8192*4,"Program too large")
                mem=out/f"{name}.mem"
                mem.write_text("".join(f"{int.from_bytes(padded[i:i+4],'little'):08x}\n" for i in range(0,len(padded),4)))
                args=[f"+PROGRAM={mem}",f"+WORDS={len(padded)//4}"]
                if reset_pc is not None: args.append(f"+RESET_PC={reset_pc}")
                results={}
                for sim in ("iverilog","verilator"):
                    log=run(f"{name}_{sim}",[*commands[(sim,case["m"],case["q"],case["p"])],*args])
                    results[sim]=compare(log,expected,name+"_"+sim)
                    require(results[sim]["stalls"]==case["stalls"],f"{name}: unexpected stalls")
                    if reset_pc is not None: require("RESET_PASS" in log,"Missing reset control")
                    if case["p"]:
                        cfg=f"m{case['m']}q{case['q']}p1"
                        for a,b in re.findall(r"PEXEC\|[^\n]+\|(\d+)\|(\d+)\n",log):
                            forwarding[sim][cfg][0].add(int(a)); forwarding[sim][cfg][1].add(int(b))
                report["programs"][name]=dict(config=[case["m"],case["q"],case["p"]],program_bytes=len(data),
                                             reset=reset_pc is not None,matrix=case.get("matrix"),simulators=results)
                print("PASS B3 integration:",name,flush=True)
            require(len(report["programs"])==123,"Program inventory changed")
            for sim,configs in forwarding.items():
                for cfg,coverage in configs.items(): require(coverage==[{0,1,2},{0,1,2}],f"Missing forwarding {sim}/{cfg}")
            report["forwarding_coverage"]={sim:{cfg:dict(weights=sorted(a),activations=sorted(b)) for cfg,(a,b) in configs.items()}
                                           for sim,configs in forwarding.items()}
            base=report["programs"]["base_m0q0p0"]["simulators"]
            require(all(case["simulators"]==base for name,case in report["programs"].items() if name.startswith("base_")),"Base config mismatch")
            report["matrix_pairs"]={}
            for name,fixture in fixtures.items():
                b3_name,d_name=f"{name}_b3_m1q0p1",f"{name}_d_m1q1p0"
                b3=json.loads((out/f"{b3_name}.expected.json").read_text())
                d=json.loads((out/f"{d_name}.expected.json").read_text())
                require(b3["stores"]==d["stores"],"Paired CPU matrix stores differ")
                report["matrix_pairs"][name]=dict(b3=b3_name,d=d_name,outputs=b3["stores"][-2:],
                                                 activation_sum=fixture["activation_sum"],correction_location="kuntur")
            for m,q in itertools.product(range(2),repeat=2):
                require(report["programs"][f"numeric_m{m}q{q}p1"]["simulators"]["iverilog"]["packed_dots"]==1032,"Numeric coverage")
            report["mutations_detected"]={}
            datapath=ROOT/"kuntur/rtl/datapath.v"; original=datapath.read_text()
            mutations={
                "no_packed_weights_forwarding": ("xqdot4 packed_dot(\n      .weights_word(SrcAE)","xqdot4 packed_dot(\n      .weights_word(RD1E)"),
                "no_packed_activations_forwarding": (
                    "xqdot4 packed_dot(\n      .weights_word(SrcAE), .activations_word(WriteDataE)",
                    "xqdot4 packed_dot(\n      .weights_word(SrcAE), .activations_word(RD2E)"),
                "ignore_packed_half": (".d({PackedD, InstrD[27]})",".d({PackedD, 1'b0})"),
            }
            for name,(before,after) in mutations.items():
                require(original.count(before)==1,f"Mutation site changed: {name}")
                mutant=out/f"mutant_{name}.v"; mutant.write_text(original.replace(before,after))
                run(name+"_build",["iverilog","-g2012","-s","tb_integration","-Ptb_integration.ENABLE=1",
                                  "-Ptb_integration.ENABLE_MUL=1","-Ptb_integration.ENABLE_PACKED=1","-o",build/"mutant.vvp",
                                  *[mutant if p==datapath else p for p in rtl],bench])
                fixture="forwarding_m1q1p1"; mem=out/f"{fixture}.mem"
                log=run(name,["vvp",build/"mutant.vvp",f"+PROGRAM={mem}",f"+WORDS={len(mem.read_text().splitlines())}"])
                require("M3_PASS diagnostic stop" in log,"Mutant must finish normally")
                expected=json.loads((out/f"{fixture}.expected.json").read_text())
                try: compare(log,expected,name)
                except RuntimeError as error:
                    require("mismatch" in str(error),"Unrelated mutation failure")
                    report["mutations_detected"][name]=str(error)
                else: raise RuntimeError(f"Undetected mutation: {name}")
            for source in sources():
                target=out/"sources"/source.relative_to(ROOT)
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
            require(report["sources_sha256"]=={str(p.relative_to(ROOT)):sha(p) for p in sources()},"Sources changed during verification")
            report["status"]="pass"
    except Exception as error:
        report["status"]="fail"; report["error"]=f"{type(error).__name__}: {error}"
        raise
    finally:
        report["artifacts_sha256"]={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
        (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
        print("Evidence:",out,flush=True); print("Status:",report["status"],flush=True)


if __name__=="__main__": main()
