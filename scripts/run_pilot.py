"""Run the pre-registered pilot: does changing the tensors change the timing?

The pilot is not a comparison between variants. It holds the program, the
layout, the zero points, the core and the measurement events fixed, changes only
the tensor seed, and asks whether the six declared signals move. Equal totals
would not prove independence, so the record states what was compared and what
was found, and nothing more.
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
from tensors import layout, tensors, zero_points, expected_outputs
from kernels import VARIANTS, setup, required_row_bodies
from verify_measurement import PREFIX, DEPTH, sha, require, parse
from verify_kernels import check_opcodes, stores, BRANCH, JAL

SIGNALS = ["cycles", "retired_instructions", "retired_pc_opcode_trace",
           "branch_outcomes", "stall_breakdown", "data_address_trace"]
HELD_FIXED = ["text_hash", "data_layout", "zero_point_matrix",
              "core_configuration", "memory_model", "measurement_events"]


def sources():
    files = [ROOT / "scripts/run_pilot.py", ROOT / "benchmarks/kernels.py",
             ROOT / "benchmarks/tensors.py", ROOT / "benchmarks/campaign.json",
             ROOT / "docs/EXPERIMENT_PROTOCOL.md", ROOT / "tests/benchmarks/tb_measure.sv",
             ROOT / "rtl/xqdot4z.v", ROOT / "rtl/packed/xqdot4.v"]
    files.extend(ROOT.glob("kuntur/rtl/*.v"))
    return sorted(set(files))


def traces(log, binary, begin, text_end):
    """The declared signals, all derived from one traced run."""
    retired, loads_stores, branches = [], [], []
    for line in log.splitlines():
        parts = line.strip().split("|")
        if parts[0] == "RETIRED" and len(parts) == 2:
            retired.append(int(parts[1], 16))
        elif parts[0] == "STORE" and len(parts) == 3:
            loads_stores.append(("S", int(parts[1], 16)))
        elif parts[0] == "LOAD" and len(parts) == 2:
            loads_stores.append(("L", int(parts[1], 16)))
    opcodes = []
    for pc in retired:
        word = int.from_bytes(binary[pc:pc+4], "little") if begin <= pc <= text_end else 0
        opcodes.append((pc, word & 0x7f))
    # A branch outcome is visible in the trace: the next retired instruction is
    # either the fall-through or somewhere else, which is the taken case.
    for index, (pc, opcode) in enumerate(opcodes[:-1]):
        if opcode == BRANCH:
            branches.append((pc, opcodes[index + 1][0] != pc + 4))
    return dict(retired_pc_opcode_trace=opcodes, branch_outcomes=branches,
                data_address_trace=loads_stores)


def main():
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    pilot = manifest["seed_policy"]["pilot"]
    require(pilot["status"] == "blocked_until_kernels_and_counters_are_verified" or
            pilot["status"] == "executed", "Unexpected pilot status")
    rows, k, g = pilot["N"], pilot["K"], pilot["G"]
    seeds = pilot["tensor_seeds"]
    require(len(seeds) == 2, "The pilot compares exactly one seed pair")
    cases = [("zc_controls", v) for v in pilot["zc_values"]] + \
            [("zs_balanced_u4", p) for p in pilot["zs_phases"]]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "Z"
    out = ROOT / "tests/benchmarks/pilot_results" / stamp
    out.mkdir(parents=True, exist_ok=True)
    report = dict(status="fail", timestamp_utc=stamp,
                  scope="Tensor sensitivity of the declared signals, not a comparison between variants",
                  python=sys.version, platform=__import__("platform").platform(),
                  rows=rows, k=k, g=g, seeds=seeds, variants=sorted(VARIANTS),
                  settings=[list(c) for c in cases], signals=SIGNALS, held_fixed=HELD_FIXED,
                  equal_totals_prove_input_independence=False)

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
        with tempfile.TemporaryDirectory(prefix="xqdot4z-pilot-") as temporary:
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
                                             "--Mdir", obj, "-j", "1", *rtl, bench])
                commands[variant] = {"iverilog": ["vvp", binary], "verilator": [obj / "Vtb_measure"]}

            report["cases"], report["pairs"] = {}, {}
            plan = layout(rows, k)
            for profile, setting in cases:
                zeros = zero_points(profile, setting, rows, k // g)
                for variant, spec in sorted(VARIANTS.items()):
                    observations = {}
                    for seed in seeds:
                        activations, weights = tensors(seed, rows, k)
                        oracle = expected_outputs(weights, activations, zeros)
                        name = f"{variant}_n{rows}_s{seed}_{profile}_{setting}"
                        body = setup(activations, weights, zeros, plan)
                        body += spec["builder"](rows, k, zeros, plan, "derived") + "ebreak\n"
                        source = out / f"{name}.S"
                        include = f'.include "{spec["include"]}"\n' if spec["include"] else ""
                        source.write_text(include + '.option norelax\n.option norvc\n'
                                          '.text\n.global _start\n_start:\n' + body)
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
                        text_end = labels["kernel_text_end"] - 4
                        begin, close = labels["kernel_begin"], labels["kernel_end"]
                        window = ["+PROGRAM=" + mem.name, f"+WORDS={len(data)//4}",
                                  f"+BEGIN_PC={begin}", f"+END_PC={close}",
                                  f"+TEXT_END={text_end}", "+TRACE=1"]
                        results = {}
                        for simulator, command in commands[variant].items():
                            log = run(f"{name}_{simulator}", [*command, *window])
                            observed, _, _ = parse(log, name)
                            written = [v for address, v in stores(log) if address >= plan["outputs"]]
                            signed = [v - (1 << 32) if v >> 31 else v for v in written]
                            require(signed == oracle, f"{name}/{simulator}: outputs differ from the oracle")
                            results[simulator] = dict(counters=observed,
                                                      **traces(log, data, begin, text_end))
                        require(results["iverilog"] == results["verilator"], f"{name}: simulators disagree")
                        signals = results["iverilog"]
                        observations[seed] = dict(
                            cycles=signals["counters"]["cycles"],
                            retired_instructions=signals["counters"]["retired"],
                            retired_pc_opcode_trace=signals["retired_pc_opcode_trace"],
                            branch_outcomes=signals["branch_outcomes"],
                            stall_breakdown=dict(load_use=signals["counters"]["stall_load_use"],
                                                 fault_hold=signals["counters"]["stall_fault_hold"],
                                                 flush_taken_control=signals["counters"]["flush_taken_control"]),
                            data_address_trace=signals["data_address_trace"],
                            held=dict(text_hash=hashlib.sha256(data[begin:text_end + 4]).hexdigest(),
                                      data_layout=plan, zero_point_matrix=zeros,
                                      core_configuration=list(spec["enables"]),
                                      memory_model=dict(imem_words=32768, dmem_words=1024),
                                      measurement_events=[begin, close, text_end]),
                            outputs=oracle,
                            row_bodies=check_opcodes(name, variant, data, begin, text_end).get("0x23", 0))
                        report["cases"][name] = {key: value for key, value in observations[seed].items()
                                                 if key not in ("retired_pc_opcode_trace",
                                                                "data_address_trace", "branch_outcomes")}
                    first, second = (observations[s] for s in seeds)
                    for item in HELD_FIXED:
                        require(first["held"][item] == second["held"][item],
                                f"{variant}/{profile}/{setting}: {item} was not held fixed")
                    pair = f"{variant}_n{rows}_{profile}_{setting}"
                    report["pairs"][pair] = dict(
                        variant=variant, profile=profile, setting=setting, seeds=seeds,
                        equal={signal: first[signal] == second[signal] for signal in SIGNALS},
                        outputs_differ=first["outputs"] != second["outputs"],
                        required_row_bodies=required_row_bodies(variant, zeros))
            require(len(report["cases"]) == 32, "The pilot is a fixed 32-case subset")
            require(len(report["pairs"]) == 16, "Sixteen seed pairs")
            report["signals_equal_in_every_pair"] = sorted(
                s for s in SIGNALS if all(p["equal"][s] for p in report["pairs"].values()))
            report["signals_differing_somewhere"] = sorted(set(SIGNALS) - set(report["signals_equal_in_every_pair"]))
            report["outputs_differ_in_every_pair"] = all(p["outputs_differ"] for p in report["pairs"].values())
        report["status"] = "pass"
    finally:
        report["artifacts_sha256"] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*"))
                                      if p.is_file() and p.name != "summary.json"}
        (out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(("PASS" if report["status"] == "pass" else "FAIL") + f": pilot evidence in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
