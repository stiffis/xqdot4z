"""M3b partial: optional MUL, independently and in Kuntur. No benchmarks."""
import json
import random
import re
import resource
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_integration as integration
from oracle import execute

SEED = 20260911
PREFIX = integration.PREFIX
require, li, sha = integration.require, integration.li, integration.sha
EDGES = (0, 1, 2, 0x7f, 0x80, 0x7fff, 0x8000, 0x7fffffff,
         0x80000000, 0xfffffffe, 0xffffffff, 0xaaaaaaaa)


def sources():
    files = set(integration.sources())
    files.update(ROOT.glob("tests/scalar/*.sv"))
    files.update((ROOT / "scripts/verify_scalar.py", ROOT / "isa/scalar/SPEC.md"))
    return sorted(files)


def vectors():
    # Exhaustive only over sign-extended S8 pairs, not the full 32-bit domain.
    pairs = [(a & 0xffffffff, b & 0xffffffff) for a in range(-128,128) for b in range(-128,128)]
    pairs += [(a,b) for a in EDGES for b in EDGES]
    pairs += [(1 << a, 1 << b) for a in range(32) for b in range(32)]
    rng = random.Random(SEED)
    pairs += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(20000)]
    # Unsigned arbitrary precision here; the instruction oracle uses signed.
    return "".join(f"{a:08x} {b:08x} {(a*b) % (1<<32):08x}\n" for a,b in pairs)


def programs():
    cases = []
    setup = li(1,0xfffffff9)+li(2,0x12345678)
    mul = "mul x3,x1,x2\n"
    def add(name, body, q, m=1, stalls=0):
        cases.append(dict(name=f"{name}_m{m}q{q}",body=body,q=q,m=m,stalls=stalls))
    rng = random.Random(SEED)
    pairs = [(a,b) for a in EDGES for b in EDGES]
    pairs += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(512)]
    numeric = "".join(li(1,a)+li(2,b)+mul+"sw x3,0(x0)\n" for a,b in pairs)
    for q in (0,1):
        add("forwarding",setup+mul+"mul x4,x3,x2\nmul x5,x1,x4\nadd x6,x5,x3\n"
            "sw x6,0(x0)\nmul x7,x1,x2\naddi x0,x0,0\nmul x8,x7,x7\nsw x8,4(x0)\n",q)
        add("load_a",setup+"sw x1,0(x0)\nlw x5,0(x0)\nmul x6,x5,x2\nsw x6,4(x0)\n",q,stalls=1)
        add("load_b",setup+"sw x2,0(x0)\nlw x5,0(x0)\nmul x6,x1,x5\nsw x6,4(x0)\n",q,stalls=1)
        add("load_both",setup+"sw x2,0(x0)\nlw x5,0(x0)\nmul x6,x5,x5\nsw x6,4(x0)\n",q,stalls=1)
        add("aliases_x0",setup+"mul x1,x1,x2\nmul x2,x1,x2\nmul x2,x2,x2\n"
            "mul x0,x1,x2\nmul x3,x0,x2\nmul x4,x1,x0\nsw x2,0(x0)\nsw x3,4(x0)\nsw x4,8(x0)\n",q)
        add("branch_taken",setup+"mul x3,x0,x2\nbeq x3,x0,target\n"+mul+
            "sw x3,0(x0)\ntarget:\naddi x4,x0,7\nsw x4,4(x0)\n",q)
        add("branch_not_taken",setup+mul+"beq x3,x0,bad\nsw x3,0(x0)\njal x0,end\n"
            "bad:\n.word 0x0220c1b3\nend:\naddi x4,x0,7\n",q)
        add("jalr_consumer",setup+"mul x3,x0,x2\njalr x0,x3,%lo(target)\n"+mul+
            "sw x3,0(x0)\ntarget:\naddi x4,x0,7\nsw x4,4(x0)\n",q)
        add("compressed_crossing",setup+".option rvc\nc.nop\n.option norvc\n"+mul+
            ".option rvc\nc.li x8,-7\nc.addi x8,1\n.option norvc\nmul x4,x3,x8\nsw x4,0(x0)\n",q)
        add("older_mul_drains",setup+mul+".word 0x0220c233\nmul x5,x1,x2\nsw x5,0(x0)\n",q)
        add("reset_in_execute",setup+"addi x3,x0,99\n"+"addi x0,x0,0\n"*5+
            "reset_mul:\n"+mul+"sw x3,0(x0)\n",q)
        add("numeric",numeric,q)
        add("disabled",setup+mul+"sw x3,0(x0)\n",q,m=0)
        for f3 in range(1,8):
            word=(1 << 25) | (2 << 20) | (1 << 15) | (f3 << 12) | (3 << 7) | 0x33
            add(f"unsupported_m_f3_{f3}",setup+f".word 0x{word:08x}\nsw x3,0(x0)\n",q)
        for m in (0,1):
            add("base",setup+"add x3,x1,x2\nsw x3,0(x0)\nlw x4,0(x0)\nadd x5,x4,x4\nsw x5,4(x0)\n",q,m,1)
            add("wrong_path","jal x0,target\n"+mul+".word 0x0220c233\ntarget:\naddi x3,x0,7\nsw x3,0(x0)\n",q,m)
    add("mixed",li(1,0x78f04a95)+li(2,0x02ff7f80)+
        "xqdot4zi x3,x1,x2,8,1\nmul x4,x3,x2\nxqdot4zi x5,x4,x3,15,0\n"
        "mul x6,x5,x5\nxqdot4zi x7,x1,x6,0,1\nsw x7,0(x0)\n"
        "lw x8,0(x0)\nmul x9,x8,x6\nxqdot4zi x10,x9,x8,8,0\nsw x10,4(x0)\n",1,stalls=1)
    return cases


def compare(log, expected, name):
    result = integration.compare(log,expected,name)
    muls = [[int(x,16) for x in row] for row in re.findall(
        r"MEXEC\|([0-9a-f]+)\|([0-9a-f]+)\|([0-9a-f]+)\|\d+\|\d+",log)]
    require(muls==expected["muls"],f"{name}: MUL execute operand mismatch")
    result["muls"] = len(muls)
    return result


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "tests/scalar/results" / stamp
    out.mkdir(parents=True,exist_ok=False)
    report = dict(status="running",timestamp_utc=stamp,seed=SEED,
                  scope="M3b partial: functional scalar MUL, not full comparison variants",
                  sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()},
                  commands=[],unit={},programs={})
    def run(name,args,fail=False):
        args = list(map(str,args))
        p = subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=180)
        log = p.stdout+p.stderr
        (out/f"{name}.log").write_text(log)
        report["commands"].append(dict(name=name,argv=args,returncode=p.returncode))
        require((p.returncode!=0) if fail else (p.returncode==0),f"{name}: unexpected exit; see log")
        return log
    try:
        report["tools"] = {}
        for tool,flag in (("iverilog","-V"),("verilator","--version"),(PREFIX+"as","--version"),
                          (PREFIX+"ld","--version"),(PREFIX+"objcopy","--version"),(PREFIX+"nm","--version")):
            report["tools"][tool] = run("version_"+tool,[tool,flag]).splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-mul-") as temporary:
            build = Path(temporary)
            unit = ROOT/"kuntur/rtl/scalar_mul.v"
            bench = ROOT/"tests/scalar/tb_scalar_mul.sv"
            data = vectors()
            vector_path = out/"vectors.txt"
            vector_path.write_text(data)
            count = len(data.splitlines())
            require(count==86704,"Unexpected unit vector count")
            report["unit_counts"] = dict(s8_pairs=65536,edge_pairs=144,power_pairs=1024,random_pairs=20000)
            run("unit_lint",["verilator","--lint-only","-Wall","--top-module","scalar_mul",unit])
            report["unit_lint"] = "pass_no_waivers"
            run("unit_iverilog_build",["iverilog","-g2012","-s","tb_scalar_mul","-o",build/"unit.vvp",unit,bench])
            run("unit_verilator_build",["verilator","--binary","--timing","--timescale","1ns/1ps","--top-module",
                                       "tb_scalar_mul","--Mdir",build/"unitobj","-j","2",unit,bench])
            unit_commands = {"iverilog":["vvp",build/"unit.vvp"],"verilator":[build/"unitobj/Vtb_scalar_mul"]}
            controls = dict(wrong_expected=("00000002 00000003 00000007\n",1),empty=("",1),
                            truncated=("00000002 00000003\n",1),extra_field=("00000002 00000003 00000006 0\n",1),
                            bad_hex=("0000000x 00000003 00000006\n",1),count_mismatch=(data.splitlines()[0]+"\n",2),
                            trailing_partial=("00000002 00000003 00000006\n0",1),missing_file=(None,1))
            for sim,command in unit_commands.items():
                log=run("unit_"+sim,[*command,f"+VECTORS={vector_path}",f"+COUNT={count}"])
                require(f"MUL_PASS checked={count}" in log,"Incomplete MUL unit verification")
                detected=[]
                for name,(fixture,n) in controls.items():
                    path=out/f"negative_{name}.txt"
                    if fixture is not None: path.write_text(fixture)
                    log=run(f"negative_{name}_{sim}",[*command,f"+VECTORS={path}",f"+COUNT={n}"],fail=True)
                    require("MUL_FAIL" in log,"Unrelated negative-control failure")
                    detected.append(name)
                report["unit"][sim]=dict(checked=count,negative_controls_detected=detected)
            report["unit_mutations_detected"]={}
            original=unit.read_text()
            for name,expression in (("add_instead_of_mul","lhs + rhs"),("truncate_inputs_16","lhs[15:0] * rhs[15:0]")):
                mutant=out/f"mutant_{name}.v"
                require(original.count("lhs * rhs")==1,"Unit mutation site changed")
                mutant.write_text(original.replace("lhs * rhs",expression))
                run(name+"_build",["iverilog","-g2012","-s","tb_scalar_mul","-o",build/"mutunit.vvp",mutant,bench])
                log=run(name,["vvp",build/"mutunit.vvp",f"+VECTORS={vector_path}",f"+COUNT={count}"],fail=True)
                require("MUL_FAIL mismatch" in log,"Unrelated unit mutation failure")
                report["unit_mutations_detected"][name]="arithmetic mismatch"
            print(f"PASS MUL unit: {count} vectors per simulator, 8 controls each, 2 mutations",flush=True)

            policy=ROOT/"kuntur/rtl/instruction_policy.v"
            decode_bench=ROOT/"tests/scalar/tb_mul_decode.sv"
            run("decode_build",["iverilog","-g2012","-s","tb_mul_decode","-o",build/"decode.vvp",policy,decode_bench])
            log=run("decode",["vvp",build/"decode.vvp"])
            require("MUL_DECODE_PASS checked=131072" in log,"Incomplete decode checks")
            report["decoder_checks"]=131072
            rtl=sorted((ROOT/"kuntur/rtl").glob("*.v"))+[ROOT/"rtl/xqdot4z.v"]
            bench=ROOT/"tests/integration/tb_integration.sv"
            commands={}
            for m in (0,1):
                for q in (0,1):
                    config=f"m{m}q{q}"
                    run(f"lint_{config}",["verilator","--lint-only","--timing","--timescale","1ns/1ps","-DSYNTHESIS","-Wall",
                                          "-Wno-VARHIDDEN","-Wno-UNUSEDSIGNAL","--top-module","top",
                                          f"-GENABLE_MUL={m}",f"-GENABLE_XQDOT4Z={q}",*rtl])
                    binary=build/f"{config}.vvp"
                    run(f"iverilog_build_{config}",["iverilog","-g2012","-s","tb_integration",f"-Ptb_integration.ENABLE={q}",
                                                    f"-Ptb_integration.ENABLE_MUL={m}","-o",binary,*rtl,bench])
                    commands[("iverilog",m,q)]=["vvp",binary]
                    obj=build/config
                    run(f"verilator_build_{config}",["verilator","--binary","--timing","--timescale","1ns/1ps",
                                                     "--top-module","tb_integration",f"-GENABLE={q}",f"-GENABLE_MUL={m}",
                                                     "--Mdir",obj,"-j","2",*rtl,bench])
                    commands[("verilator",m,q)]=[obj/"Vtb_integration"]
                    print("PASS build/lint:",config,flush=True)
            def assemble(name,body,prolog=True):
                source=out/f"{name}.S"
                initialization="".join(f"addi x{i},x0,0\n" for i in range(1,32)) if prolog else ""
                source.write_text('.include "xqdot4zi.inc"\n.option norelax\n.option norvc\n.text\n.global _start\n_start:\n'+initialization+body)
                run(name+"_as",[PREFIX+"as","-I",ROOT/"isa","-march=rv32imc","-mabi=ilp32","-mno-relax","-o",build/f"{name}.o",source])
                run(name+"_ld",[PREFIX+"ld","-m","elf32lriscv","--no-relax","-Ttext=0","-o",out/f"{name}.elf",build/f"{name}.o"])
                run(name+"_objcopy",[PREFIX+"objcopy","-O","binary","-j",".text",out/f"{name}.elf",out/f"{name}.bin"])
                symbols=run(name+"_nm",[PREFIX+"nm","-n",out/f"{name}.elf"])
                labels={fields[2]:int(fields[0],16) for line in symbols.splitlines() if len(fields:=line.split())==3}
                return (out/f"{name}.bin").read_bytes(),labels
            encodings=[(d,a,b) for d in range(32) for a in range(32) for b in range(32)]
            encoded,_=assemble("encoding","".join(f"mul x{d},x{a},x{b}\n" for d,a,b in encodings),False)
            require(len(encoded)==4*len(encodings),"MUL encoding length")
            for i,(d,a,b) in enumerate(encodings):
                require(int.from_bytes(encoded[4*i:4*i+4],"little")==
                        (0x02000033 | (b<<20) | (a<<15) | (d<<7)),"GNU MUL encoding mismatch")
            report["encoding_pairs"]=len(encodings)
            forwarding={sim:[set(),set()] for sim in ("iverilog","verilator")}
            for case in programs():
                name=case["name"]
                binary,labels=assemble(name,case["body"]+"ebreak\n")
                reset_pc=labels.get("reset_mul")
                expected=execute(binary,case["q"],stop_before=reset_pc-8 if reset_pc is not None else None,mul_enabled=bool(case["m"]))
                if reset_pc is not None: expected["fault"]=[3,0]
                (out/f"{name}.expected.json").write_text(json.dumps(expected,indent=2)+"\n")
                padded=binary+bytes(-len(binary)%4)
                require(len(padded)<=8192*4,"Program too large")
                mem=out/f"{name}.mem"
                mem.write_text("".join(f"{int.from_bytes(padded[i:i+4],'little'):08x}\n" for i in range(0,len(padded),4)))
                args=[f"+PROGRAM={mem}",f"+WORDS={len(padded)//4}"]
                if reset_pc is not None: args.append(f"+RESET_PC={reset_pc}")
                results={}
                for sim in ("iverilog","verilator"):
                    log=run(f"{name}_{sim}",[*commands[(sim,case["m"],case["q"])],*args])
                    results[sim]=compare(log,expected,name+"_"+sim)
                    require(results[sim]["stalls"]==case["stalls"],f"{name}: unexpected stalls")
                    if reset_pc is not None: require("RESET_PASS" in log,"Missing reset control")
                    for a,b in re.findall(r"MEXEC\|[^\n]+\|(\d+)\|(\d+)\n",log):
                        forwarding[sim][0].add(int(a)); forwarding[sim][1].add(int(b))
                report["programs"][name]=dict(enable_mul=case["m"],enable_xqdot4z=case["q"],
                                             program_bytes=len(binary),reset=reset_pc is not None,simulators=results)
                print("PASS scalar integration:",name,flush=True)
            require(len(report["programs"])==49,"Program inventory changed")
            for sim,coverage in forwarding.items():
                require(coverage==[{0,1,2},{0,1,2}],f"Incomplete MUL forwarding coverage: {sim}")
            report["forwarding_coverage"]={sim:dict(lhs=sorted(a),rhs=sorted(b)) for sim,(a,b) in forwarding.items()}
            for q in (0,1):
                require(report["programs"][f"numeric_m1q{q}"]["simulators"]["iverilog"]["muls"]==656,"Numeric coverage")
            base=report["programs"]["base_m0q0"]["simulators"]
            require(all(case["simulators"]==base for name,case in report["programs"].items() if name.startswith("base_")),"Base configuration mismatch")
            # Controlled faults must be detected by comparison, not a simulator crash.
            report["pipeline_mutations_detected"]={}
            datapath=ROOT/"kuntur/rtl/datapath.v"
            original=datapath.read_text()
            for name,before,after in (("no_mul_lhs_forwarding",".lhs(SrcAE)",".lhs(RD1E)"),
                                      ("no_mul_rhs_forwarding",".rhs(WriteDataE)",".rhs(RD2E)")):
                require(original.count(before)==1,"MUL mutation site changed")
                mutant=out/f"mutant_{name}.v"
                mutant.write_text(original.replace(before,after))
                run(name+"_build",["iverilog","-g2012","-s","tb_integration","-Ptb_integration.ENABLE=1",
                                  "-Ptb_integration.ENABLE_MUL=1","-o",build/"mutpipe.vvp",
                                  *[mutant if p==datapath else p for p in rtl],bench])
                name_case="forwarding_m1q1"
                words=len((out/f"{name_case}.mem").read_text().splitlines())
                log=run(name,["vvp",build/"mutpipe.vvp",f"+PROGRAM={out/f'{name_case}.mem'}",f"+WORDS={words}"])
                expected=json.loads((out/f"{name_case}.expected.json").read_text())
                require("M3_PASS diagnostic stop" in log,"Mutant did not finish normally")
                try: compare(log,expected,name)
                except RuntimeError as error:
                    require("mismatch" in str(error),"Unexpected mutation failure")
                    report["pipeline_mutations_detected"][name]=str(error)
                else: raise RuntimeError(f"Undetected mutation: {name}")
            for path in sources():
                target=out/"sources"/path.relative_to(ROOT)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
            require(report["sources_sha256"]=={str(p.relative_to(ROOT)):sha(p) for p in sources()},"Sources changed during verification")
            report["status"]="pass"
    except Exception as error:
        report["status"]="fail"
        report["error"]=f"{type(error).__name__}: {error}"
        raise
    finally:
        report["artifacts_sha256"]={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
        (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
        print("Evidence:",out,flush=True)
        print("Status:",report["status"],flush=True)


if __name__ == "__main__":
    main()
