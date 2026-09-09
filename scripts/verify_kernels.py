"""Verify that the paired kernels compute the contract's subtotals.

This checks correctness and the instruction mix, which is the gate M4 requires
before any comparison: every variant must return the same integers for the same
tensors. Counters are recorded because the harness reports them, not because a
comparison is being drawn here. No speedup is computed.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "scripts"))
from tensors import (DMEM_WORDS, layout, tensors, zero_points, expected_outputs,
                     activation_sum, pack_activations)
from kernels import VARIANTS, setup
from verify_measurement import PREFIX, DEPTH, sha, require, parse

SHAPES = [1, 4, 16]
K = G = 32
SEEDS = [20260908, 20260909]
SETTINGS = [("zc_controls", 0), ("zc_controls", 8), ("zc_controls", 15), ("zs_balanced_u4", 0)]

# One opcode allowlist per variant: it proves D never multiplies and that
# neither variant reaches for the other's custom space.
LUI, OP_IMM, OP, LOAD, STORE, SYSTEM, CUSTOM0, CUSTOM1 = 0x37, 0x13, 0x33, 0x03, 0x23, 0x73, 0x0b, 0x2b
BASE = {LUI, OP_IMM, OP, LOAD, STORE, SYSTEM}
ALLOWED = {"D": BASE | {CUSTOM0}, "B3": BASE | {CUSTOM1}}
MULTIPLY_ALLOWED = {"D": False, "B3": True}


def sources():
    files = [ROOT / "scripts/verify_kernels.py", ROOT / "benchmarks/kernels.py",
             ROOT / "benchmarks/tensors.py", ROOT / "benchmarks/campaign.json",
             ROOT / "docs/EXPERIMENT_PROTOCOL.md", ROOT / "tests/benchmarks/tb_measure.sv",
             ROOT / "rtl/xqdot4z.v", ROOT / "rtl/packed/xqdot4.v"]
    files.extend(ROOT.glob("kuntur/rtl/*.v"))
    return sorted(set(files))


def check_opcodes(name, variant, binary, begin, end):
    """Decode the kernel text; an unexpected opcode fails the case."""
    counts = {}
    for address in range(begin, end + 4, 4):
        word = int.from_bytes(binary[address:address + 4], "little")
        opcode = word & 0x7f
        require(opcode in ALLOWED[variant], f"{name}: opcode {opcode:#04x} outside the {variant} allowlist")
        multiply = opcode == OP and (word >> 25) == 1
        require(MULTIPLY_ALLOWED[variant] or not multiply, f"{name}: {variant} must not multiply")
        key = f"{opcode:#04x}" + ("/mul" if multiply else "")
        counts[key] = counts.get(key, 0) + 1
    return counts


def stores(log):
    return [(int(parts[1], 16), int(parts[2], 16)) for line in log.splitlines()
            if (parts := line.strip().split("|"))[0] == "STORE" and len(parts) == 3]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "Z"
    report = dict(status="fail", timestamp_utc=stamp,
                  scope="Paired kernel correctness and instruction mix, not a performance comparison",
                  python=sys.version, platform=__import__("platform").platform(),
                  shapes=SHAPES, k=K, g=G, seeds=SEEDS,
                  settings=[list(s) for s in SETTINGS], variants=sorted(VARIANTS))
    out = ROOT / "tests/benchmarks/kernel_results" / stamp
    out.mkdir(parents=True, exist_ok=True)

    def run(name, command):
        finished = subprocess.run([str(x) for x in command], capture_output=True, text=True, cwd=out)
        log = finished.stdout + finished.stderr
        (out / f"{name}.log").write_text(log)
        require(finished.returncode == 0, f"{name}: {log[-400:]}")
        return log

    try:
        report["sources_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
        report["tools"] = {}
        for tool, flag in (("iverilog", "-V"), ("verilator", "--version"), (PREFIX + "as", "--version")):
            require(shutil.which(tool), f"Missing tool: {tool}")
            report["tools"][tool] = subprocess.run([tool, flag], capture_output=True,
                                                   text=True).stdout.splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-kernels-") as temporary:
            build = Path(temporary)
            rtl = sorted((ROOT / "kuntur/rtl").glob("*.v")) + [ROOT / "rtl/xqdot4z.v", ROOT / "rtl/packed/xqdot4.v"]
            bench = ROOT / "tests/benchmarks/tb_measure.sv"
            commands = {}
            for variant, spec in sorted(VARIANTS.items()):
                qdot, mul, packed = spec["enables"]
                binary = build / f"sim_{variant}.vvp"
                run(f"iverilog_{variant}", ["iverilog", "-g2012", "-s", "tb_measure",
                                            f"-Ptb_measure.ENABLE_QDOT={qdot}", f"-Ptb_measure.ENABLE_MUL={mul}",
                                            f"-Ptb_measure.ENABLE_PACKED={packed}", "-o", binary, *rtl, bench])
                obj = build / f"obj_{variant}"
                run(f"verilator_{variant}", ["verilator", "--binary", "--timing", "--timescale", "1ns/1ps",
                                             "--top-module", "tb_measure", f"-GENABLE_QDOT={qdot}",
                                             f"-GENABLE_MUL={mul}", f"-GENABLE_PACKED={packed}",
                                             "--Mdir", obj, "-j", "2", *rtl, bench])
                commands[variant] = {"iverilog": ["vvp", binary], "verilator": [obj / "Vtb_measure"]}

            report["cases"] = {}
            agreements = 0
            for rows in SHAPES:
                for seed in SEEDS:
                    activations, weights = tensors(seed, rows, K)
                    plan = layout(rows, K)
                    for profile, setting in SETTINGS:
                        zeros = zero_points(profile, setting, rows, K // G)
                        oracle = expected_outputs(weights, activations, zeros)
                        produced = {}
                        for variant, spec in sorted(VARIANTS.items()):
                            name = f"{variant}_n{rows}_s{seed}_{profile}_{setting}"
                            body = setup(activations, weights, plan)
                            body += spec["builder"](rows, K, zeros, plan) + "ebreak\n"
                            source = out / f"{name}.S"
                            source.write_text(f'.include "{spec["include"]}"\n.option norelax\n'
                                              '.option norvc\n.text\n.global _start\n_start:\n' + body)
                            run(name + "_as", [PREFIX + "as", "-I", ROOT / "isa", "-I", ROOT / "isa/packed",
                                               "-march=rv32imc", "-mabi=ilp32", "-mno-relax",
                                               "-o", build / f"{name}.o", source])
                            run(name + "_ld", [PREFIX + "ld", "-m", "elf32lriscv", "--no-relax", "-Ttext=0",
                                               "-o", out / f"{name}.elf", build / f"{name}.o"])
                            run(name + "_objcopy", [PREFIX + "objcopy", "-O", "binary", "-j", ".text",
                                                    out / f"{name}.elf", out / f"{name}.bin"])
                            symbols = run(name + "_nm", [PREFIX + "nm", "-n", out / f"{name}.elf"])
                            labels = {m[2]: int(m[0], 16) for line in symbols.splitlines()
                                      if len(m := line.split()) == 3}
                            data = (out / f"{name}.bin").read_bytes()
                            mem = out / f"{name}.mem"
                            mem.write_text("".join(f"{int.from_bytes(data[i:i+4],'little'):08x}\n"
                                                   for i in range(0, len(data), 4)))
                            mix = check_opcodes(name, variant, data, labels["kernel_begin"], labels["kernel_end"])
                            window = ["+PROGRAM=" + mem.name, f"+WORDS={len(data)//4}",
                                      f"+BEGIN_PC={labels['kernel_begin']}", f"+END_PC={labels['kernel_end']}",
                                      f"+TEXT_END={labels['kernel_end']}", "+TRACE=1"]
                            results = {}
                            for simulator, command in commands[variant].items():
                                log = run(f"{name}_{simulator}", [*command, *window])
                                observed, _, bounds = parse(log, name)
                                require(observed["cycles"] == observed["retired_kernel"] + DEPTH +
                                        observed["stall_load_use"] + 2*observed["flush_taken_control"],
                                        f"{name}: unaccounted cycles")
                                written = [value for address, value in stores(log)
                                           if address >= plan["outputs"]]
                                require(len(written) == rows, f"{name}: expected {rows} outputs")
                                signed = [v - (1 << 32) if v >> 31 else v for v in written]
                                require(signed == oracle, f"{name}/{simulator}: {signed} != {oracle}")
                                results[simulator] = observed
                            require(results["iverilog"] == results["verilator"], f"{name}: simulators disagree")
                            produced[variant] = oracle
                            report["cases"][name] = dict(
                                variant=variant, rows=rows, seed=seed, profile=profile, setting=setting,
                                zero_points=[row[0] for row in zeros], activation_sum=activation_sum(activations),
                                code_bytes=labels["kernel_end"] + 4 - labels["kernel_begin"],
                                instruction_mix=mix, outputs=oracle, counters=results["iverilog"])
                        # The M4 gate: the variants must return the same integers.
                        require(len(set(map(tuple, produced.values()))) == 1,
                                f"n{rows}_s{seed}_{profile}_{setting}: variants disagree")
                        agreements += 1
            report["paired_agreements"] = agreements
            require(agreements == len(SHAPES) * len(SEEDS) * len(SETTINGS), "Incomplete pairing")
            require(len(report["cases"]) == agreements * len(VARIANTS), "Incomplete case inventory")
            # B3 must pay a correction D does not, and only D uses custom-0.
            for name, case in report["cases"].items():
                multiplies = case["instruction_mix"].get("0x33/mul", 0)
                if case["variant"] == "D":
                    require(multiplies == 0 and f"{CUSTOM0:#04x}" in case["instruction_mix"], name)
                else:
                    shared = len(set(case["zero_points"])) == 1
                    require(multiplies == (1 if shared else case["rows"]),
                            f"{name}: correction reuse does not follow the declared schedule")
        report["status"] = "pass"
    finally:
        report["artifacts_sha256"] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*"))
                                      if p.is_file() and p.name != "summary.json"}
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(("PASS" if report["status"] == "pass" else "FAIL") + f": kernel evidence in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
