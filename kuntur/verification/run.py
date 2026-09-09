"""Reproducible Kuntur correction regression; original repository is never written.

GNU binutils independently encodes compressed/base instruction pairs. Directed
RTL tests use fatal assertions; pipeline retirement/stores are checked in Python.
"""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "riscv64-linux-gnu-"


def run(cmd, cwd, out, name, timeout=60):
    proc = subprocess.run(list(map(str, cmd)), cwd=cwd, capture_output=True,
                          text=True, timeout=timeout, check=False)
    (out / (name + ".stdout.log")).write_text(proc.stdout)
    (out / (name + ".stderr.log")).write_text(proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"{name}: exit {proc.returncode}; {proc.stderr[-1500:]} {proc.stdout[-1500:]}")
    return proc.stdout


def assemble(text, work, out, name):
    source = work / (name + ".S")
    source.write_text(".option norelax\n.text\n.global _start\n_start:\n" + text + "\n")
    run([PREFIX+"as", "-march=rv32ic", "-mabi=ilp32", "-mno-relax", "-o",
         work/(name+".o"), source], work, out, name+"-as")
    run([PREFIX+"ld", "-m", "elf32lriscv", "--no-relax", "-Ttext=0", "-o",
         work/(name+".elf"), work/(name+".o")], work, out, name+"-ld")
    run([PREFIX+"objcopy", "-O", "binary", "-j", ".text", work/(name+".elf"),
         work/(name+".bin")], work, out, name+"-objcopy")
    symbols = run([PREFIX+"nm", "-n", work/(name+".elf")], work, out, name+"-symbols")
    labels = {m[2]: int(m[0], 16) for line in symbols.splitlines()
              if len(m := line.split()) == 3}
    return (work/(name+".bin")).read_bytes(), labels


def compressed_pairs():
    pairs = []
    def add(c, base): pairs.append((c, base))
    for rd in range(1, 32):
        for imm in range(-32, 32):
            add(f"c.li x{rd},{imm}", f"addi x{rd},x0,{imm}")
            if imm:
                add(f"c.addi x{rd},{imm}", f"addi x{rd},x{rd},{imm}")
                if rd != 2:
                    add(f"c.lui x{rd},{imm & 0xfffff}", f"lui x{rd},{imm & 0xfffff}")
        for shift in range(1, 32):
            add(f"c.slli x{rd},{shift}", f"slli x{rd},x{rd},{shift}")
        for offset in range(0, 256, 4):
            add(f"c.lwsp x{rd},{offset}(sp)", f"lw x{rd},{offset}(sp)")
        add(f"c.jr x{rd}", f"jalr x0,x{rd},0")
        add(f"c.jalr x{rd}", f"jalr x1,x{rd},0")
        for rs in range(1, 32):
            add(f"c.mv x{rd},x{rs}", f"add x{rd},x0,x{rs}")
            add(f"c.add x{rd},x{rs}", f"add x{rd},x{rd},x{rs}")
    for rs in range(32):
        for offset in range(0, 256, 4):
            add(f"c.swsp x{rs},{offset}(sp)", f"sw x{rs},{offset}(sp)")
    for imm in range(-512, 512, 16):
        if imm: add(f"c.addi16sp sp,{imm}", f"addi sp,sp,{imm}")
    for rd in range(8, 16):
        for imm in range(4, 1024, 4):
            add(f"c.addi4spn x{rd},sp,{imm}", f"addi x{rd},sp,{imm}")
        for shift in range(1, 32):
            for op in ("srli", "srai"):
                add(f"c.{op} x{rd},{shift}", f"{op} x{rd},x{rd},{shift}")
        for imm in range(-32, 32):
            add(f"c.andi x{rd},{imm}", f"andi x{rd},x{rd},{imm}")
        for rs in range(8, 16):
            for op in ("sub", "xor", "or", "and"):
                add(f"c.{op} x{rd},x{rs}", f"{op} x{rd},x{rd},x{rs}")
            for offset in range(0, 128, 4):
                add(f"c.lw x{rd},{offset}(x{rs})", f"lw x{rd},{offset}(x{rs})")
                add(f"c.sw x{rd},{offset}(x{rs})", f"sw x{rd},{offset}(x{rs})")
        for offset in range(-256, 256, 2):
            for c, b in (("beqz", "beq"), ("bnez", "bne")):
                add(f"c.{c} x{rd}, . + ({offset})", f"{b} x{rd},x0, . + ({offset})")
    for offset in range(-2048, 2048, 2):
        add(f"c.j . + ({offset})", f"jal x0, . + ({offset})")
        add(f"c.jal . + ({offset})", f"jal x1, . + ({offset})")
    add("c.nop", "addi x0,x0,0")
    add("c.ebreak", "ebreak")
    return pairs


def simulate(top, sources, work, out, name, args=(), params=()):
    binary = work / (name + ".vvp")
    run(["iverilog", "-g2012", "-s", top, *params, "-o", binary, *sources],
        work, out, name+"-compile")
    return run(["vvp", binary, *args], work, out, name)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT/"verification/results"/stamp
    out.mkdir(parents=True)
    summary = {"status": "running", "timestamp_utc": stamp, "tests": {}, "tools": {}}
    inputs = {ROOT/"Makefile", ROOT/"run_tests.sh"}
    for pattern in ("rtl/*.v", "verification/*.py", "verification/*.sv",
                    "tests/*.v", "tests/programs/*.mem"):
        inputs.update(ROOT.glob(pattern))
    summary["sources_sha256"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(inputs)}
    try:
        for tool in ("iverilog", "verilator", PREFIX+"as", PREFIX+"ld", PREFIX+"objcopy", PREFIX+"nm"):
            flag = "-V" if tool == "iverilog" else "--version"
            summary["tools"][tool] = run([tool, flag], ROOT, out, tool+"-version").splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="kuntur-verification-") as tmp:
            work = Path(tmp)
            rtl = sorted((ROOT/"rtl").glob("*.v"))
            # Re-run every historical test without the old stderr filters.
            rows = re.findall(r'"\s*([\w]+)\s*\|\s*([\w.]+)\s*\|\s*([\w.]+)\s*"',
                              (ROOT/"run_tests.sh").read_text())
            if len(rows) != 26: raise RuntimeError("Unexpected historical test inventory")
            for name, image, tb in rows:
                shutil.copy2(ROOT/"tests/programs"/image, work/"riscvtest.mem")
                output = simulate("testbench", [*rtl, ROOT/"tests"/tb], work, out, "legacy-"+name)
                if not re.search(r"succe|\bok\b", output, re.I) or re.search(r"fail|unexpected|timed out|mismatch|fatal", output, re.I):
                    raise RuntimeError("Historical test failed: " + name)
            summary["tests"]["historical"] = len(rows)
            print("PASS historical: 26 (return codes and unfiltered logs)", flush=True)

            pairs = compressed_pairs()
            assembly = "\n".join(f".option rvc\n{c}\n.option norvc\n{base}" for c,base in pairs)
            data, _ = assemble(assembly, work, out, "decompression-oracle")
            if len(data) != 6*len(pairs): raise RuntimeError("Assembler changed pair lengths")
            vectors = []
            for i in range(len(pairs)):
                compressed = int.from_bytes(data[6*i:6*i+2], "little")
                base = int.from_bytes(data[6*i+2:6*i+6], "little")
                if compressed & 3 == 3 or base & 3 != 3: raise RuntimeError("Invalid pair widths")
                vectors.append((base << 32) | (0xa5a50000 | compressed))
            invalid = [0x0000,0x2000,0x6000,0x6001,0x6101,0x8002,0x4002,
                       0x1082,0x9001,0x9401,0x9c01,0x9c21,0xffff & 0xfffe]
            vectors.extend((1<<64) | (0x13<<32) | c for c in invalid)
            # Valid standard HINTs are not rejected as reserved instructions.
            for raw, base in [(0x0001,0x13),(0x0005,0x00100013),(0x4005,0x00100013),
                              (0x8006,0x00100033),(0x9006,0x00100033)]:
                vectors.append((base<<32)|raw)
            for raw in [0x13,0x00100073,0xffffffff,0x02528333]:
                vectors.append((raw<<32)|raw)
            vectorfile=work/"decompression.hex"
            vectorfile.write_text("".join(f"{v:017x}\n" for v in vectors))
            simulate("tb_vectors", [ROOT/"rtl/decompressor.v", ROOT/"verification/tb_vectors.sv"],
                     work,out,"decompression",[f"+vectors={vectorfile}",f"+count={len(vectors)}"])
            summary["tests"]["assembler_pairs"] = len(pairs)
            summary["tests"]["decompression_vectors"] = len(vectors)
            summary["decompression_vectors_sha256"] = hashlib.sha256(vectorfile.read_bytes()).hexdigest()
            print(f"PASS decompression: {len(pairs)} GNU-assembler pairs + {len(vectors)-len(pairs)} controls", flush=True)

            rng=Random(20260908)
            edges=[0,1,0xffffffff,0x7fffffff,0x80000000,0x80000001]
            operands=[(a,b) for a in edges for b in edges]
            operands += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(10000)]
            signed=lambda x: x if x<0x80000000 else x-(1<<32)
            slt=work/"slt.hex"
            slt.write_text("".join(f"{((int(signed(a)<signed(b))<<64)|(a<<32)|b):017x}\n" for a,b in operands))
            simulate("tb_slt",[ROOT/"rtl/alu.v",ROOT/"verification/tb_slt.sv"],work,out,"slt",
                     [f"+vectors={slt}",f"+count={len(operands)}"])
            summary["tests"]["signed_comparisons"]=len(operands)
            # Reproduce the signed-overflow defect on the untouched baseline.
            original_alu = ROOT.parent/"baseline/upstream/rtl/alu.v"
            if original_alu.is_file():
                old_binary=work/"original-slt.vvp"
                run(["iverilog","-g2012","-s","tb_slt","-o",old_binary,original_alu,
                     ROOT/"verification/tb_slt.sv"],work,out,"original-slt-compile")
                old=subprocess.run(["vvp",str(old_binary),f"+vectors={slt}",f"+count={len(operands)}"],
                                   cwd=work,capture_output=True,text=True,timeout=30)
                (out/"original-slt.stdout.log").write_text(old.stdout)
                (out/"original-slt.stderr.log").write_text(old.stderr)
                if not old.returncode or "SLT a=" not in old.stdout:
                    raise RuntimeError("Original SLT defect was not reproduced")
                summary["tests"]["original_signed_comparison"]="expected_failure_reproduced"
                summary["original_alu_sha256"]=hashlib.sha256(original_alu.read_bytes()).hexdigest()
            for name,top,sources in [
                ("policy-hazards","tb_policy_hazards",["instruction_policy.v","hazardunit.v"]),
                ("memory","tb_memory",["imem.v","dmem.v"]),
                ("regfile","tb_regfile",["regfile.v"])]:
                filename = top + ".sv"
                simulate(top,[*[ROOT/"rtl"/s for s in sources],ROOT/"verification"/filename],work,out,name)
                summary["tests"][name]="pass"
            pipeline_cases(work,out,rtl,summary)
            run(["verilator","--lint-only","--timing","-DSYNTHESIS","-Wall",
                 "-Wno-VARHIDDEN","-Wno-UNUSEDSIGNAL","--top-module","top",*rtl],
                work,out,"verilator-lint")
            summary["tests"]["verilator_lint"]="pass; VARHIDDEN/UNUSEDSIGNAL excluded explicitly"
            summary["status"]="pass"
    except Exception as error:
        summary["status"]="fail"; summary["error"]=str(error)
        raise
    finally:
        (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
        print("Evidence:",out)


def pipeline_cases(work,out,rtl,summary):
    normal = [
        "addi sp,x0,64", "c.addi16sp sp,16", "c.addi4spn x8,sp,12", "c.li x5,-7",
        "sw x5,0(x8)", "c.addi16sp sp,-16", "addi x10,x0,7", "sw x10,0(sp)",
        "lw x5,0(sp)", "addi x6,x0,5", "sw x5,4(sp)", "lw x7,0(sp)", "add x9,x7,x7",
        "sw x9,8(sp)", "lui x10,0x80000", "addi x11,x0,1", "slt x12,x10,x11",
        "sw x12,12(sp)", "blt x10,x11,s20", ".word 0x02528333",
        "bge x11,x10,s22", "c.ebreak", "sw x6,16(sp)", "c.ebreak"]
    cases=[
        ("integration",normal,[i for i in range(23) if i not in (19,21)],23,3,64,
         [(92,0xfffffff9),(64,7),(68,7),(72,14),(76,1),(80,5)],1),
        ("illegal-mul",["addi x3,x0,9","addi x1,x0,3","addi x2,x0,4",".word 0x022081b3","sw x3,0(x0)"],
         [0,1,2],3,2,64,[],0),
        ("illegal-compressed",["addi x3,x0,9",".2byte 0x0000","sw x3,0(x0)"],
         [0],1,2,64,[],0),
        ("fetch-boundary",["addi x1,x0,1","c.nop","c.nop"],[0,1,2],None,1,2,[],0)]
    for name,instructions,retired,terminal,cause,words,stores,stalls in cases:
        text="\n".join(f".option {'rvc' if ins.startswith('c.') else 'norvc'}\ns{i}: {ins}"
                       for i,ins in enumerate(instructions))
        data,labels=assemble(text,work,out,name)
        data += bytes((-len(data))%4)
        if len(data)>words*4: raise RuntimeError("Program too large")
        (work/"riscvtest.mem").write_text("".join(f"{int.from_bytes(data[i:i+4],'little'):08x}\n"
                                                  for i in range(0,len(data),4)))
        output=simulate("tb_pipeline",[*rtl,ROOT/"verification/tb_pipeline.sv"],work,out,name,
                        params=[f"-Ptb_pipeline.WORDS={words}"])
        observed=[int(x,16) for x in re.findall(r"RETIRE\|([0-9a-fA-F]+)",output)]
        expected=[labels[f"s{i}"] for i in retired]
        if observed!=expected: raise RuntimeError(f"{name}: retirement expected={expected} observed={observed}")
        observed_stores=[(int(a,16),int(b,16)) for a,b in re.findall(r"STORE\|([0-9a-fA-F]+)\|([0-9a-fA-F]+)",output)]
        if observed_stores!=stores: raise RuntimeError(f"{name}: stores {observed_stores} != {stores}")
        stop=re.search(r"FAULT\|(\d+)\|([0-9a-fA-F]+)",output)
        pc=words*4 if terminal is None else labels[f"s{terminal}"]
        if not stop or (int(stop[1]),int(stop[2],16))!=(cause,pc): raise RuntimeError(f"{name}: wrong diagnostic stop")
        if output.splitlines().count("STALL")!=stalls: raise RuntimeError(f"{name}: wrong stall count")
        if name.startswith("illegal") and "REG3|00000009" not in output:
            raise RuntimeError(f"{name}: illegal instruction corrupted destination")
        summary["tests"][name]={"retired":len(expected),"stores":len(stores),"load_use_stalls":stalls,
                                "fault_cause":cause,"fault_pc":pc}
        print("PASS pipeline:",name,flush=True)


if __name__=="__main__": main()
