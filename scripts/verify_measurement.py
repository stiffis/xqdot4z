"""Verify the measurement window and the protocol counters, not kernel speed.

Expected values are derived from the pipeline's structure, not recorded from a
run: a straight-line kernel of n instructions occupies n+3 cycles, a load-use
hazard adds one, and a taken control transfer adds two. Recording a simulator's
own output as its expectation would prove nothing.
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
PREFIX = "riscv64-linux-gnu-"
DEPTH = 3  # decode-to-writeback distance: acceptance leads retirement by three cycles


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition: raise RuntimeError(message)


def sources():
    files = [ROOT / "scripts/verify_measurement.py", ROOT / "docs/EXPERIMENT_PROTOCOL.md",
             ROOT / "rtl/xqdot4z.v", ROOT / "rtl/packed/xqdot4.v"]
    for pattern in ("kuntur/rtl/*.v", "tests/benchmarks/*.sv", "isa/*.inc"):
        files.extend(ROOT.glob(pattern))
    return sorted(set(files))


def li(reg, value):
    value &= 0xffffffff
    low = value & 4095
    if low >= 2048: low -= 4096
    return f"lui x{reg},0x{((value-low) >> 12) & 0xfffff:x}\naddi x{reg},x{reg},{low}\n"


BRANCH, JAL, JALR = 0x63, 0x6f, 0x67


def straight(instructions, stores, writes, loads=0):
    """A kernel with no hazard and no taken transfer retires one per cycle."""
    return dict(cycles=instructions + DEPTH, retired=instructions, retired_kernel=instructions,
                retired_stores=stores, retired_loads=loads, register_writes=writes,
                stall_load_use=0, stall_fault_hold=0, flush_taken_control=0,
                retired_branches=0, retired_jumps=0,
                data_read_bytes=4*loads, data_write_bytes=4*stores)


def classify(trace, binary, begin, text_end):
    """Retired branches come from decoding the trace, not from a pipeline flag:
    a branch that falls through retires but never raises PCSrcE."""
    counts = dict(retired_branches=0, retired_jumps=0)
    for pc in trace:
        if not begin <= pc <= text_end: continue
        opcode = int.from_bytes(binary[pc:pc+4], "little") & 0x7f
        if opcode == BRANCH: counts["retired_branches"] += 1
        elif opcode in (JAL, JALR): counts["retired_jumps"] += 1
    return counts


def programs():
    """Each case states why its expectation holds, independently of any run."""
    cases = []
    # The window opens on the first kernel instruction, so a kernel placed at
    # _start has nothing older in flight and retired equals retired_kernel.
    cases.append(dict(name="straight_four", enables=(0, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\naddi x1,x0,5\naddi x2,x0,7\nadd x3,x1,x2\n"
                           "kernel_end:\nsw x3,0(x0)\nebreak\n",
                      expected=straight(4, 1, 3),
                      rationale="Four instructions, no hazard: 4+3 cycles, three register writes."))
    cases.append(dict(name="straight_seven", enables=(0, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\naddi x1,x0,1\naddi x2,x0,2\naddi x3,x0,3\n"
                           "add x4,x1,x2\nadd x5,x4,x3\nadd x6,x5,x5\n"
                           "kernel_end:\nsw x6,0(x0)\nebreak\n",
                      expected=straight(7, 1, 6),
                      rationale="Same rule at a different length: cycles track n, not a constant."))
    # One load-use pair: exactly one stall cycle, so exactly one cycle more.
    cases.append(dict(name="load_use_stall", enables=(0, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\nsw x0,0(x0)\nlw x1,0(x0)\naddi x2,x1,1\n"
                           "kernel_end:\nsw x2,4(x0)\nebreak\n",
                      expected=dict(straight(4, 2, 2, loads=1), cycles=4+DEPTH+1, stall_load_use=1),
                      rationale="The consumer of a load stalls one cycle; nothing else changes."))
    # The same four instructions with the hazard broken by an independent one.
    cases.append(dict(name="load_use_separated", enables=(0, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\nsw x0,0(x0)\nlw x1,0(x0)\naddi x3,x0,7\naddi x2,x1,1\n"
                           "kernel_end:\nsw x2,4(x0)\nebreak\n",
                      expected=straight(5, 2, 3, loads=1),
                      rationale="Separating the pair removes the stall: the differential is the stall itself."))
    # A taken branch discards two fetched slots, so it costs two cycles.
    cases.append(dict(name="taken_branch", enables=(0, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\naddi x1,x0,0\nbeq x1,x0,tgt\naddi x2,x0,99\n"
                           "tgt:\naddi x3,x0,3\nkernel_end:\nsw x3,0(x0)\nebreak\n",
                      expected=dict(straight(4, 1, 2), cycles=4+DEPTH+2, flush_taken_control=1, retired_branches=1),
                      rationale="Four instructions retire; the skipped one is flushed and costs two "
                                "cycles. It writes no register, so the flush is visible in the write count."))
    cases.append(dict(name="not_taken_branch", enables=(0, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\naddi x1,x0,1\nbeq x1,x0,tgt\naddi x3,x0,3\n"
                           "tgt:\nkernel_end:\nsw x3,0(x0)\nebreak\n",
                      expected=dict(straight(4, 1, 2), retired_branches=1),
                      rationale="A branch that falls through costs nothing: the counter separates taken from executed."))
    # A loop closes the window at the last output store. One prolog instruction
    # is still in flight when the window opens, so it retires inside it.
    iterations, body_size = 3, 3
    cases.append(dict(name="loop_three_rows", enables=(0, 0, 0), text_end="loop_end",
                      body="addi x5,x0,3\nkernel_begin:\naddi x5,x5,-1\n"
                           "kernel_end:\nsw x5,0(x0)\nloop_end:\nbne x5,x0,kernel_begin\nebreak\n",
                      expected=dict(cycles=15, retired=iterations*body_size,
                                    retired_kernel=iterations*body_size - 1,
                                    retired_stores=iterations, retired_loads=0,
                                    register_writes=iterations + 1, stall_load_use=0,
                                    stall_fault_hold=0, flush_taken_control=iterations-1,
                                    retired_branches=iterations-1, retired_jumps=0,
                                    data_read_bytes=0, data_write_bytes=4*iterations),
                      rationale="Three iterations store three times and take the branch twice. The "
                                "window closes at the last store, so the final branch has not retired, "
                                "and the prolog instruction accepted before the window retires inside it."))
    # The harness must measure the extension path, not only base instructions.
    cases.append(dict(name="qdot_straight", enables=(1, 0, 0), text_end="kernel_end",
                      body="kernel_begin:\n" + li(1, 0x78f04a95) + li(2, 0x02ff7f80) +
                           "xqdot4zi x3,x1,x2,8,0\nxqdot4zi x4,x1,x2,15,1\nadd x5,x3,x4\n"
                           "kernel_end:\nsw x5,0(x0)\nebreak\n",
                      expected=straight(8, 1, 7),
                      rationale="The fused operation executes in E without its own wait, so a kernel "
                                "using it obeys the same straight-line rule."))
    return cases


def identities(name, observed, window):
    """Structural relations that must hold for every case, whatever the counts."""
    require(observed["cycles"] == window[1] - window[0] + 1, f"{name}: cycles disagree with the window")
    require(observed["retired_kernel"] <= observed["retired"], f"{name}: kernel retirements exceed the total")
    require(observed["retired"] - observed["retired_kernel"] <= DEPTH,
            f"{name}: more in-flight instructions than pipeline depth")
    require(observed["register_writes"] <= observed["retired"],
            f"{name}: register writes counted as instructions")
    require(observed["stall_fault_hold"] == 0, f"{name}: a fault held the measured kernel")
    require(observed["data_write_bytes"] == 4*observed["retired_stores"], f"{name}: store bytes")
    require(observed["data_read_bytes"] == 4*observed["retired_loads"], f"{name}: load bytes")
    require(observed["cycles"] >= observed["retired"], f"{name}: more retirements than cycles")
    # The window is fully explained by kernel retirements, the pipeline fill,
    # load-use stalls and taken redirections. Anything else is unaccounted time.
    require(observed["cycles"] == observed["retired_kernel"] + DEPTH +
            observed["stall_load_use"] + 2*observed["flush_taken_control"],
            f"{name}: cycles not accounted for by retirements, depth, stalls and redirections")


def parse(log, name):
    require("MEASURE_PASS" in log, f"{name}: window did not close")
    observed, trace, window = {}, [], None
    for line in log.splitlines():
        parts = line.strip().split("|")
        if parts[0] == "MEASURE" and len(parts) == 3: observed[parts[1]] = int(parts[2])
        elif parts[0] == "RETIRED" and len(parts) == 2: trace.append(int(parts[1], 16))
        elif parts[0] == "WINDOW" and len(parts) == 3: window = (int(parts[1]), int(parts[2]))
    require(window is not None, f"{name}: no window record")
    return observed, trace, window


def main():
    report = dict(status="fail", timestamp_utc=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "Z",
                  scope="Measurement window and counter contract, not kernel performance",
                  python=sys.version, platform=__import__("platform").platform())
    out = ROOT / "tests/benchmarks/results" / report["timestamp_utc"]
    out.mkdir(parents=True, exist_ok=True)
    logs = {}

    def run(name, command, fail=False):
        finished = subprocess.run([str(x) for x in command], capture_output=True, text=True, cwd=out)
        log = finished.stdout + finished.stderr
        (out / f"{name}.log").write_text(log)
        logs[name] = log
        if fail: require(finished.returncode != 0, f"{name}: expected failure")
        else: require(finished.returncode == 0, f"{name}: {log[-400:]}")
        return log

    try:
        report["sources_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
        report["tools"] = {}
        for tool, flag in (("iverilog", "-V"), ("verilator", "--version"), (PREFIX + "as", "--version"),
                           (PREFIX + "ld", "--version"), (PREFIX + "objcopy", "--version"),
                           (PREFIX + "nm", "--version")):
            require(shutil.which(tool), f"Missing tool: {tool}")
            report["tools"][tool] = subprocess.run([tool, flag], capture_output=True,
                                                   text=True).stdout.splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-measure-") as temporary:
            build = Path(temporary)
            rtl = sorted((ROOT / "kuntur/rtl").glob("*.v")) + [ROOT / "rtl/xqdot4z.v", ROOT / "rtl/packed/xqdot4.v"]
            bench = ROOT / "tests/benchmarks/tb_measure.sv"

            def simulators(enables, bench_file, tag):
                qdot, mul, packed = enables
                binary = build / f"sim_{tag}.vvp"
                run(f"iverilog_{tag}", ["iverilog", "-g2012", "-s", "tb_measure",
                                        f"-Ptb_measure.ENABLE_QDOT={qdot}", f"-Ptb_measure.ENABLE_MUL={mul}",
                                        f"-Ptb_measure.ENABLE_PACKED={packed}", "-o", binary, *rtl, bench_file])
                obj = build / f"obj_{tag}"
                run(f"verilator_{tag}", ["verilator", "--binary", "--timing", "--timescale", "1ns/1ps",
                                         "--top-module", "tb_measure", f"-GENABLE_QDOT={qdot}",
                                         f"-GENABLE_MUL={mul}", f"-GENABLE_PACKED={packed}",
                                         "--Mdir", obj, "-j", "1", *rtl, bench_file])
                return {"iverilog": ["vvp", binary], "verilator": [obj / "Vtb_measure"]}

            def assemble(name, body):
                source = out / f"{name}.S"
                source.write_text('.include "xqdot4zi.inc"\n.option norelax\n.option norvc\n'
                                  '.text\n.global _start\n_start:\n' + body)
                run(name + "_as", [PREFIX + "as", "-I", ROOT / "isa", "-march=rv32ic", "-mabi=ilp32",
                                   "-mno-relax", "-o", build / f"{name}.o", source])
                run(name + "_ld", [PREFIX + "ld", "-m", "elf32lriscv", "--no-relax", "-Ttext=0",
                                   "-o", out / f"{name}.elf", build / f"{name}.o"])
                run(name + "_objcopy", [PREFIX + "objcopy", "-O", "binary", "-j", ".text",
                                        out / f"{name}.elf", out / f"{name}.bin"])
                symbols = run(name + "_nm", [PREFIX + "nm", "-n", out / f"{name}.elf"])
                labels = {m[2]: int(m[0], 16) for line in symbols.splitlines() if len(m := line.split()) == 3}
                data = (out / f"{name}.bin").read_bytes()
                mem = out / f"{name}.mem"
                mem.write_text("".join(f"{int.from_bytes(data[i:i+4],'little'):08x}\n"
                                       for i in range(0, len(data), 4)))
                return labels, len(data) // 4, mem

            commands = {}
            report["programs"] = {}
            for case in programs():
                name = case["name"]
                labels, words, mem = assemble(name, case["body"])
                for label in ("kernel_begin", "kernel_end", case["text_end"]):
                    require(label in labels, f"{name}: missing {label}")
                window = ["+PROGRAM=" + mem.name, f"+WORDS={words}", f"+BEGIN_PC={labels['kernel_begin']}",
                          f"+END_PC={labels['kernel_end']}", f"+TEXT_END={labels[case['text_end']]}"]
                if case["enables"] not in commands:
                    commands[case["enables"]] = simulators(case["enables"], bench,
                                                           "".join(str(x) for x in case["enables"]))
                results = {}
                binary = (out / f"{name}.bin").read_bytes()
                for simulator, command in commands[case["enables"]].items():
                    observed, trace, bounds = parse(run(f"{name}_{simulator}",
                                                       [*command, *window, "+TRACE=1"]), name)
                    # Tracing continues past the closing retirement; retirement is
                    # in order, so the window's own entries are the first ones.
                    require(len(trace) >= observed["retired"], f"{name}: trace shorter than retirements")
                    trace = trace[:observed["retired"]]
                    observed.update(classify(trace, binary, labels["kernel_begin"], labels[case["text_end"]]))
                    identities(name, observed, bounds)
                    require(observed == case["expected"],
                            f"{name}/{simulator}: expected {case['expected']}, observed {observed}")
                    results[simulator] = observed
                require(results["iverilog"] == results["verilator"], f"{name}: simulators disagree")
                # Static code size belongs to the runner: it reads the linked text.
                code_bytes = labels[case["text_end"]] + 4 - labels["kernel_begin"]
                report["programs"][name] = dict(window=window[2:], code_bytes=code_bytes,
                                                rationale=case["rationale"], counters=results["iverilog"])
            require(len(report["programs"]) == 8, "Incomplete measurement battery")

            # The differential is the point of the pair: one stall, one cycle.
            stalled = report["programs"]["load_use_stall"]["counters"]
            separated = report["programs"]["load_use_separated"]["counters"]
            require(stalled["stall_load_use"] - separated["stall_load_use"] == 1 and
                    stalled["cycles"] - separated["cycles"] == 0 and
                    separated["retired"] - stalled["retired"] == 1,
                    "Load-use differential not isolated")
            report["differentials"] = dict(load_use_stall_cycles=1, taken_control_cycles=2)

            # Negative controls: the harness must refuse a window it cannot place.
            broken = 0
            probe = report["programs"]["straight_four"]
            _, words, mem = assemble("control_probe", programs()[0]["body"])
            for tag, extra in (("no_open", ["+BEGIN_PC=4096", "+END_PC=4096", "+TEXT_END=4096"]),
                               ("no_close", ["+BEGIN_PC=0", "+END_PC=4096", "+TEXT_END=4096"]),
                               ("inverted", ["+BEGIN_PC=12", "+END_PC=0", "+TEXT_END=12"])):
                run(f"control_{tag}", ["vvp", build / "sim_000.vvp", "+PROGRAM=control_probe.mem",
                                       f"+WORDS={words}", *extra], fail=True)
                require("MEASURE_FAIL" in logs[f"control_{tag}"], f"control {tag}: wrong failure")
                broken += 1
            report["negative_controls"] = broken

            # Mutations of the harness itself: a counter nobody can break is not
            # evidence. Each must make a case that passes above fail.
            original = bench.read_text()
            mutations = {
                "count_stall_as_retirement": ("if (retire) begin\n        w_retired=w_retired+1;",
                                              "if (retire || dut.rvpipe.HazardStallF) begin\n        w_retired=w_retired+1;"),
                "attribute_every_retirement": ("if (in_kernel(retirepc)) w_kernel", "if (1) w_kernel"),
                "close_on_first_store": ("if (retire && retirepc==32'(end_pc)) begin",
                                         "if (retire && retirepc==32'(end_pc) && !closed) begin"),
                "ignore_load_use_stall": ("if (dut.rvpipe.HazardStallF) w_stall_load_use=w_stall_load_use+1;",
                                          "if (1'b0) w_stall_load_use=w_stall_load_use+1;"),
            }
            detected = {}
            for tag, (before, after) in mutations.items():
                require(before in original, f"mutation {tag}: anchor not found")
                mutant = build / f"mutant_{tag}.sv"
                mutant.write_text(original.replace(before, after, 1))
                binary = build / f"mutant_{tag}.vvp"
                run(f"mutant_build_{tag}", ["iverilog", "-g2012", "-s", "tb_measure", "-o", binary, *rtl, mutant])
                for case in programs():
                    if case["enables"] != (0, 0, 0): continue
                    labels, words, mem = assemble(case["name"], case["body"])
                    log = run(f"mutant_{tag}_{case['name']}",
                              ["vvp", binary, "+PROGRAM=" + mem.name, f"+WORDS={words}",
                               f"+BEGIN_PC={labels['kernel_begin']}", f"+END_PC={labels['kernel_end']}",
                               f"+TEXT_END={labels[case['text_end']]}", "+TRACE=1"])
                    observed, trace, _ = parse(log, case["name"])
                    trace = trace[:observed["retired"]]
                    observed.update(classify(trace, (out / f"{case['name']}.bin").read_bytes(),
                                             labels["kernel_begin"], labels[case["text_end"]]))
                    if observed != case["expected"]:
                        detected[tag] = f"{case['name']}: {observed} != {case['expected']}"
                        break
                require(tag in detected, f"mutation {tag} went undetected")
            report["mutations_detected"] = detected
            require(len(detected) == 4, "Every harness mutation must be detected")

        report["status"] = "pass"
    finally:
        report["artifacts_sha256"] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*"))
                                      if p.is_file() and p.name != "summary.json"}
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(("PASS" if report["status"] == "pass" else "FAIL") + f": measurement evidence in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
