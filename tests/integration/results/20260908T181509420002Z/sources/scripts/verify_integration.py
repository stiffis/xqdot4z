"""Verify the optional immediate-only XQDot4Z integration (M3a), not speedup."""
import hashlib
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
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "tests/integration"))
from isa.xqdot4zi import encode, decode, VERSION
from oracle import execute

PREFIX = "riscv64-linux-gnu-"
SEED = 20260910


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition: raise RuntimeError(message)


def sources():
    files = [ROOT / "scripts/verify_integration.py", ROOT / "isa/SPEC.md", ROOT / "rtl/xqdot4z.v"]
    for pattern in ("isa/*.py", "isa/*.inc", "tests/integration/*.py", "tests/integration/*.sv",
                    "kuntur/rtl/*.v", "model/*.py"):
        files.extend(ROOT.glob(pattern))
    return sorted(set(files))


def li(reg, value):
    value &= 0xffffffff
    low = value & 4095
    if low >= 2048: low -= 4096
    return f"lui x{reg},0x{((value-low) >> 12) & 0xfffff:x}\naddi x{reg},x{reg},{low}\n"


def programs():
    setup = li(1,0x78f04a95)+li(2,0x02ff7f80)
    q = lambda rd,a,b,z=8,h=0: f"xqdot4zi x{rd},x{a},x{b},{z},{h}\n"
    baseline = setup+"add x3,x1,x2\nsw x3,0(x0)\nlw x4,0(x0)\nadd x5,x4,x4\nsw x5,4(x0)\n"
    cases = [
        dict(name="base_on",body=baseline,enabled=1,stalls=1),
        dict(name="base_off",body=baseline,enabled=0,stalls=1),
        dict(name="forwarding",body=setup+q(3,1,2)+q(4,3,2,15,1)+q(5,1,4,0,0)+
             "add x6,x5,x3\nsw x6,0(x0)\n"+q(7,1,2)+"addi x0,x0,0\n"+
             q(8,7,7)+"sw x8,4(x0)\n",enabled=1,stalls=0),
        dict(name="load_weights",body=setup+"sw x1,0(x0)\nlw x5,0(x0)\n"+q(6,5,2)+
             "sw x6,4(x0)\n",enabled=1,stalls=1),
        dict(name="load_activations",body=setup+"sw x2,0(x0)\nlw x5,0(x0)\n"+q(6,1,5,15,1)+
             "sw x6,4(x0)\n",enabled=1,stalls=1),
        dict(name="load_both",body=setup+"sw x2,0(x0)\nlw x5,0(x0)\n"+q(6,5,5,15,1)+
             "sw x6,4(x0)\n",enabled=1,stalls=1),
        dict(name="aliases_x0",body=setup+q(1,1,2)+q(2,1,2,15,1)+q(2,2,2,0,1)+
             q(0,1,2)+q(3,0,2)+q(4,1,0)+"sw x0,0(x0)\nsw x2,4(x0)\nsw x3,8(x0)\nsw x4,12(x0)\n",
             enabled=1,stalls=0),
        dict(name="branch_consumer",body=setup+q(3,0,2,0)+"beq x3,x0,target\n"+
             q(4,1,2,15,1)+"sw x4,0(x0)\ntarget:\n"+q(5,1,2)+"sw x5,4(x0)\n",enabled=1,stalls=0),
        dict(name="branch_not_taken",body=setup+q(3,1,2)+"beq x3,x0,bad\n"+
             q(4,1,2,15,1)+"jal x0,end\nbad:\n.word 0x0600000b\nend:\nsw x4,0(x0)\n",enabled=1,stalls=0),
        dict(name="jalr_consumer",body=setup+q(3,0,2,0)+"jalr x0,x3,%lo(target)\n"+
             q(4,1,2)+"sw x4,0(x0)\ntarget:\n"+q(5,1,2,15,1)+"sw x5,4(x0)\n",enabled=1,stalls=0),
        dict(name="compressed_crossing",body=setup+".option rvc\nc.nop\n.option norvc\n"+
             q(3,1,2)+".option rvc\nc.li x8,-7\nc.addi x8,1\n.option norvc\n"+
             q(4,1,8,15,1)+"sw x3,0(x0)\nsw x4,4(x0)\n",enabled=1,stalls=0),
        dict(name="older_qdot_drains",body=setup+q(3,1,2)+".word 0x0600000b\n"+q(4,1,2),enabled=1,stalls=0),
        dict(name="reset_in_execute",body=setup+"addi x3,x0,99\n"+"addi x0,x0,0\n"*5+
             "reset_q:\n"+q(3,1,2)+"sw x3,0(x0)\n",enabled=1,stalls=0,reset=True),
    ]
    for enabled in (0,1):
        cases.append(dict(name=f"wrong_path_{enabled}",body="jal x0,target\n"+q(3,1,2)+
                          ".word 0x0600000b\ntarget:\naddi x3,x0,7\nsw x3,0(x0)\n",enabled=enabled,stalls=0))
    for z,h in ((0,0),(8,1),(15,0),(15,1)):
        cases.append(dict(name=f"disabled_z{z}_h{h}",body=setup+q(3,1,2,z,h)+"sw x3,0(x0)\n",enabled=0,stalls=0))
    for bit in (12,13,14,25,26):
        word = encode(3,1,2,8,1) | (1 << bit)
        cases.append(dict(name=f"reserved_bit{bit}",body=setup+f".word 0x{word:08x}\nsw x3,0(x0)\n",enabled=1,stalls=0))
    body = []
    for z in range(16):
        for h in (0,1):
            body.append(setup+q(3,1,2,z,h)+"sw x3,0(x0)\n")
    rng = random.Random(SEED)
    for _ in range(512):
        w,a,z = rng.getrandbits(32),rng.getrandbits(32),rng.randrange(16)
        for h in (0,1):
            body.append(li(1,w)+li(2,a)+q(3,1,2,z,h)+"sw x3,0(x0)\n")
    cases.append(dict(name="all_z_h_random",body="".join(body),enabled=1,stalls=0))
    return cases


def compare(log, expected, name):
    require("M3_PASS diagnostic stop" in log and "M3_FAIL" not in log, f"{name}: incomplete simulation")
    retired = [[int(pc,16),int(rd),int(val,16)] for pc,rd,val in
               re.findall(r"RETIRE\|([0-9a-f]+)\|(\d+)\|([0-9a-f]+)",log)]
    stores = [[int(a,16),int(b,16)] for a,b in re.findall(r"STORE\|([0-9a-f]+)\|([0-9a-f]+)",log)]
    fault = re.findall(r"FAULT\|(\d+)\|([0-9a-f]+)",log)
    regs = {int(r):int(v,16) for r,v in re.findall(r"REG\|(\d+)\|([0-9a-f]+)",log)}
    qdots = [[int(x,16) for x in row[:5]] for row in
             re.findall(r"QEXEC\|([0-9a-f]+)\|([0-9a-f]+)\|([0-9a-f]+)\|([0-9a-f]+)\|([0-9a-f]+)\|(\d+)\|(\d+)",log)]
    require(retired == expected["retired"], f"{name}: retirement/writeback mismatch")
    require(stores == expected["stores"], f"{name}: store mismatch")
    require(len(fault)==1 and [int(fault[0][0]),int(fault[0][1],16)]==expected["fault"], f"{name}: fault mismatch")
    require(regs == {i:expected["regs"][i] for i in range(1,32)}, f"{name}: final registers mismatch")
    require(qdots == expected["qdots"], f"{name}: execute operands/metadata mismatch")
    return dict(retired=len(retired),stores=len(stores),qdots=len(qdots),stalls=log.splitlines().count("STALL"))


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "tests/integration/results" / stamp
    out.mkdir(parents=True,exist_ok=False)
    report = dict(status="running",timestamp_utc=stamp,isa_version=VERSION,seed=SEED,
                  scope="M3a immediate-only ISA integration; no performance evaluation",
                  sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()},commands=[],programs={})
    def run(name,args,cwd=ROOT,fail=False):
        args=list(map(str,args))
        p=subprocess.run(args,cwd=cwd,text=True,capture_output=True,timeout=180)
        log=p.stdout+p.stderr
        (out / f"{name}.log").write_text(log)
        report["commands"].append(dict(name=name,argv=args,returncode=p.returncode))
        require((p.returncode!=0) if fail else (p.returncode==0),f"{name}: unexpected exit; see log")
        return log
    try:
        report["reference_states"]={}
        for name in ("MODEL_STATE","RTL_STATE"):
            state_path=ROOT/f"docs/{name}.json"
            state=json.loads(state_path.read_text()); evidence=ROOT/state["evidence"]
            require(sha(evidence)==state["evidence_sha256"],f"Stale {name} evidence")
            ref=json.loads(evidence.read_text())
            require(ref["status"]=="pass",f"Unverified {name}")
            for source,digest in ref["sources_sha256"].items():
                require(sha(ROOT/source)==digest,f"Stale reference source {source}")
            report["reference_states"][name]=dict(state=state,evidence_sha256=sha(evidence),state_sha256=sha(state_path))
        report["tools"]={}
        for tool,flag in (("iverilog","-V"),("verilator","--version"),(PREFIX+"as","--version"),
                          (PREFIX+"ld","--version"),(PREFIX+"objcopy","--version"),(PREFIX+"nm","--version")):
            report["tools"][tool]=run("version_"+tool,[tool,flag]).splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-m3-") as temporary:
            build=Path(temporary)
            rtl=sorted((ROOT/"kuntur/rtl").glob("*.v"))+[ROOT/"rtl/xqdot4z.v"]
            def assemble(name,body,prolog=True):
                source=out/f"{name}.S"
                initialization="".join(f"addi x{i},x0,0\n" for i in range(1,32)) if prolog else ""
                source.write_text('.include "xqdot4zi.inc"\n.option norelax\n.option norvc\n.text\n.global _start\n_start:\n'+initialization+body)
                run(name+"_as",[PREFIX+"as","-I",ROOT/"isa","-march=rv32ic","-mabi=ilp32","-mno-relax","-o",build/f"{name}.o",source])
                run(name+"_ld",[PREFIX+"ld","-m","elf32lriscv","--no-relax","-Ttext=0","-o",out/f"{name}.elf",build/f"{name}.o"])
                run(name+"_objcopy",[PREFIX+"objcopy","-O","binary","-j",".text",out/f"{name}.elf",out/f"{name}.bin"])
                symbols=run(name+"_nm",[PREFIX+"nm","-n",out/f"{name}.elf"])
                labels={m[2]:int(m[0],16) for line in symbols.splitlines() if len(m:=line.split())==3}
                return (out/f"{name}.bin").read_bytes(),labels

            combinations=[(rd,(rd+7)%32,31-rd,z,h) for z in range(16) for h in (0,1) for rd in range(32)]
            data,_=assemble("encoding","".join(f"xqdot4zi x{d},x{a},x{b},{z},{h}\n" for d,a,b,z,h in combinations),False)
            require(len(data)==4*len(combinations),"Encoding length")
            for i,args in enumerate(combinations):
                word=int.from_bytes(data[4*i:4*i+4],"little")
                require(word==encode(*args),"GNU encoding mismatch")
                require(list(decode(word).values())==list(args),"Encoding roundtrip")
            report["encoding_pairs"]=len(combinations)
            invalid=[(-1,1,2,8,0),(32,1,2,8,0),(3,-1,2,8,0),(3,1,32,8,0),
                     (3,1,2,-1,0),(3,1,2,16,0),(3,1,2,8,-1),(3,1,2,8,2),(True,1,2,8,0)]
            for args in invalid:
                try: encode(*args)
                except (ValueError,TypeError): pass
                else: raise RuntimeError("Encoder accepted invalid inputs")
            report["encoder_rejections"]=len(invalid)
            for i,(z,h) in enumerate(((-1,0),(16,0),(0,-1),(0,2))):
                fixture=out/f"bad_macro_{i}.S"
                fixture.write_text(f'.include "xqdot4zi.inc"\nxqdot4zi x3,x1,x2,{z},{h}\n')
                log=run(f"bad_macro_{i}",[PREFIX+"as","-I",ROOT/"isa","-march=rv32ic","-mabi=ilp32","-o",build/"bad.o",fixture],fail=True)
                require("xqdot4zi:" in log,"Unexpected macro failure")
            report["macro_rejections"]=4
            run("decode_build",["iverilog","-g2012","-s","tb_decode","-o",build/"decode.vvp",
                                ROOT/"kuntur/rtl/instruction_policy.v",ROOT/"tests/integration/tb_decode.sv"])
            require("DECODE_PASS checked=32768" in run("decode",["vvp",build/"decode.vvp"]),"Decode coverage")
            report["decoder_checks"]=32768
            bench=ROOT/"tests/integration/tb_integration.sv"
            commands={}
            for enabled in (0,1):
                run(f"lint_{enabled}",["verilator","--lint-only","--timing","--timescale","1ns/1ps","-DSYNTHESIS","-Wall",
                                      "-Wno-VARHIDDEN","-Wno-UNUSEDSIGNAL","--top-module","top",f"-GENABLE_XQDOT4Z={enabled}",*rtl])
                binary=build/f"sim{enabled}.vvp"
                run(f"iverilog_build_{enabled}",["iverilog","-g2012","-s","tb_integration",f"-Ptb_integration.ENABLE={enabled}","-o",binary,*rtl,bench])
                commands[("iverilog",enabled)]=["vvp",binary]
                obj=build/f"obj{enabled}"
                run(f"verilator_build_{enabled}",["verilator","--binary","--timing","--timescale","1ns/1ps","--top-module","tb_integration",
                                                  f"-GENABLE={enabled}","--Mdir",obj,"-j","2",*rtl,bench])
                commands[("verilator",enabled)]=[obj/"Vtb_integration"]
            all_forward_a,all_forward_b=set(),set()
            for case in programs():
                name=case["name"]
                data,labels=assemble(name,case["body"]+"ebreak\n")
                reset_pc=labels.get("reset_q")
                if reset_pc is not None:
                    # Reset asserted as Q enters E cancels the two older M/W
                    # instructions too; both are explicit NOPs in this program.
                    expected=execute(data,case["enabled"],stop_before=reset_pc-8)
                    expected["fault"]=[3,0]
                else: expected=execute(data,case["enabled"])
                (out/f"{name}.expected.json").write_text(json.dumps(expected,indent=2)+"\n")
                padded=data+bytes(-len(data)%4)
                require(len(padded)<=8192*4,"Program exceeds test memory")
                mem=out/f"{name}.mem"
                mem.write_text("".join(f"{int.from_bytes(padded[i:i+4],'little'):08x}\n" for i in range(0,len(padded),4)))
                args=[f"+PROGRAM={mem}",f"+WORDS={len(padded)//4}"]
                if reset_pc is not None: args.append(f"+RESET_PC={reset_pc}")
                results={}
                for simulator in ("iverilog","verilator"):
                    log=run(f"{name}_{simulator}",[*commands[(simulator,case["enabled"])],*args])
                    results[simulator]=compare(log,expected,name+"_"+simulator)
                    require(results[simulator]["stalls"]==case["stalls"],f"{name}: unexpected load-use stalls")
                    if reset_pc is not None: require("RESET_PASS" in log,"Reset control missing")
                    for a,b in re.findall(r"QEXEC\|[^\n]+\|(\d+)\|(\d+)\n",log):
                        all_forward_a.add(int(a)); all_forward_b.add(int(b))
                report["programs"][name]=dict(enabled=case["enabled"],program_bytes=len(data),simulators=results,reset=reset_pc is not None)
                print("PASS integration:",name,flush=True)
            require(all_forward_a==all_forward_b=={0,1,2},"Missing QDot forwarding source coverage")
            report["forwarding_coverage"]={"weights":sorted(all_forward_a),"activations":sorted(all_forward_b)}
            require(report["programs"]["all_z_h_random"]["simulators"]["iverilog"]["qdots"]==1056,"Incomplete numeric integration campaign")
            require(report["programs"]["base_on"]["simulators"]==report["programs"]["base_off"]["simulators"],"Base on/off summary differs")
            # Preserve exact current sources as well as their hashes for future review.
            for path in sources():
                target=out/"sources"/path.relative_to(ROOT)
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)
            report["status"]="pass"
    except Exception as error:
        report["status"]="fail"; report["error"]=f"{type(error).__name__}: {error}"
        raise
    finally:
        report["artifacts_sha256"]={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
        (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
        print("Evidence:",out,flush=True); print("Status:",report["status"],flush=True)


if __name__=="__main__": main()
