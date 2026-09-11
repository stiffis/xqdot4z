"""Run the registered campaign: every planned case, its headline codegen.

The inventory already fixes which cases exist and what they must produce, so
this runs them and records what each one cost. Every planned case gets a
terminal status and is retained, including failures, because a case that is
merely absent would make the campaign look complete when it is not.

No speedup is computed here. Cycles, retirements, stalls and sizes are recorded
per case and reported per profile and phase; combining regimes into one number
is refused by the manifest and is not done anywhere in this file.
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
from tensors import layout, tensors, zero_points
from kernels import VARIANTS, setup, required_row_bodies, strength_reduction
from verify_measurement import PREFIX, DEPTH, sha, require, parse
from verify_kernels import check_opcodes, stores

TIMEOUT = 900


def sources():
    files = [ROOT / "scripts/run_campaign.py", ROOT / "benchmarks/kernels.py",
             ROOT / "benchmarks/tensors.py", ROOT / "benchmarks/campaign.json",
             ROOT / "benchmarks/inventory.json", ROOT / "docs/EXPERIMENT_PROTOCOL.md",
             ROOT / "tests/benchmarks/tb_measure.sv",
             ROOT / "rtl/xqdot4z.v", ROOT / "rtl/packed/xqdot4.v"]
    files.extend(ROOT.glob("kuntur/rtl/*.v"))
    return sorted(set(files))


def main():
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    require(manifest["status"] == "registered", "The campaign runs only from a registered design")
    require(manifest["execution_blockers"] == [], "Execution blockers remain")
    inventory = json.loads((ROOT / "benchmarks/inventory.json").read_text())
    state = json.loads((ROOT / "docs/INVENTORY_STATE.json").read_text())
    require(sha(ROOT / state["inventory"]) == state["inventory_sha256"],
            "The inventory does not match its pin")
    k, g = inventory["k"], inventory["g"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "Z"
    out = ROOT / "results/campaign" / stamp
    out.mkdir(parents=True, exist_ok=True)
    report = dict(status="fail", run_id=stamp, timestamp_utc=stamp,
                  protocol_version=manifest["protocol_version"],
                  manifest_version=manifest["manifest_version"],
                  campaign_id=manifest["campaign_id"], variant="all",
                  config=dict(k=k, g=g, shapes=inventory["shapes"], seeds=inventory["seeds"]),
                  scope="Every planned case under its headline codegen; no speedup is computed",
                  python=sys.version, platform=__import__("platform").platform(),
                  planned_cases=len(inventory["cases"]), commands=[], cases={})

    def run(name, command, timeout=TIMEOUT):
        finished = subprocess.run([str(x) for x in command], capture_output=True,
                                  text=True, cwd=out, timeout=timeout)
        log = finished.stdout + finished.stderr
        (out / f"{name}.log").write_text(log)
        require(finished.returncode == 0, f"{name}: {log[-300:]}")
        return log

    try:
        report["sources_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
        report["tools"] = {}
        for tool, flag in (("iverilog", "-V"), ("verilator", "--version"), (PREFIX + "as", "--version")):
            require(shutil.which(tool), f"Missing tool: {tool}")
            report["tools"][tool] = subprocess.run([tool, flag], capture_output=True,
                                                   text=True).stdout.splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-campaign-") as temporary:
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

            for index, (case_id, entry) in enumerate(sorted(inventory["cases"].items())):
                group = inventory["groups"][entry["group"]]
                rows, seed = group["rows"], group["seed"]
                variant, spec = entry["variant"], VARIANTS[entry["variant"]]
                plan = layout(rows, k)
                zeros = group["zero_point_matrix"]
                record = dict(case=case_id, variant=variant, rows=rows, seed=seed,
                              profile=group["profile"], setting=group["setting"],
                              input_sha256=entry["sha256"], status="unsupported")
                try:
                    activations, weights = tensors(seed, rows, k)
                    body = setup(activations, weights, zeros, plan)
                    body += spec["builder"](rows, k, zeros, plan, "derived") + "ebreak\n"
                    source = out / f"{case_id}.S"
                    include = f'.include "{spec["include"]}"\n' if spec["include"] else ""
                    source.write_text(include + '.option norelax\n.option norvc\n'
                                      '.text\n.global _start\n_start:\n' + body)
                    run(case_id + "_as", [PREFIX + "as", "-I", ROOT / "isa", "-I", ROOT / "isa/packed",
                                          "-march=rv32imc", "-mabi=ilp32", "-mno-relax",
                                          "-o", build / f"{case_id}.o", source])
                    run(case_id + "_ld", [PREFIX + "ld", "-m", "elf32lriscv", "--no-relax", "-Ttext=0",
                                          "-o", build / f"{case_id}.elf", build / f"{case_id}.o"])
                    run(case_id + "_objcopy", [PREFIX + "objcopy", "-O", "binary", "-j", ".text",
                                               build / f"{case_id}.elf", build / f"{case_id}.bin"])
                    symbols = run(case_id + "_nm", [PREFIX + "nm", "-n", build / f"{case_id}.elf"])
                    labels = {m[2]: int(m[0], 16) for line in symbols.splitlines()
                              if len(m := line.split()) == 3}
                    data = (build / f"{case_id}.bin").read_bytes()
                    mem = out / f"{case_id}.mem"
                    mem.write_text("".join(f"{int.from_bytes(data[i:i+4],'little'):08x}\n"
                                           for i in range(0, len(data), 4)))
                    text_end = labels["kernel_text_end"] - 4
                    begin = labels["kernel_begin"]
                    mix = check_opcodes(case_id, variant, data, begin, text_end)
                    window = ["+PROGRAM=" + mem.name, f"+WORDS={len(data)//4}",
                              f"+BEGIN_PC={begin}", f"+END_PC={labels['kernel_end']}",
                              f"+TEXT_END={text_end}", "+TRACE=1"]
                    results = {}
                    for simulator, command in commands[variant].items():
                        log = run(f"{case_id}_{simulator}", [*command, *window])
                        observed, _, _ = parse(log, case_id)
                        require(observed["cycles"] == observed["retired_kernel"] + DEPTH +
                                observed["stall_load_use"] + 2*observed["flush_taken_control"],
                                f"{case_id}: unaccounted cycles")
                        written = [v for address, v in stores(log) if address >= plan["outputs"]]
                        signed = [v - (1 << 32) if v >> 31 else v for v in written]
                        require(signed == group["expected_group_outputs"],
                                f"{case_id}/{simulator}: outputs differ from the inventory")
                        results[simulator] = observed
                    require(results["iverilog"] == results["verilator"], f"{case_id}: simulators disagree")
                    counters = results["iverilog"]
                    record.update(status="pass", counters=counters,
                                  code_bytes=text_end + 4 - begin, instruction_mix=mix,
                                  required_row_bodies=required_row_bodies(variant, zeros),
                                  row_bodies_emitted=mix.get("0x23", 0),
                                  strength_reduction=strength_reduction(zeros[0][0])
                                                     if len({r[0] for r in zeros}) == 1
                                                     else "declined_no_dispatch",
                                  effective_z_histogram=group["effective_z_histogram"],
                                  long_branch_expansion="0x6f" in mix)
                except subprocess.TimeoutExpired:
                    record["status"] = "timeout"
                except Exception as error:  # retained, never dropped
                    record.update(status="fail", error=str(error)[:300])
                report["cases"][case_id] = record
                if (index + 1) % 200 == 0:
                    print(f"  {index + 1}/{len(inventory['cases'])} cases", flush=True)

            missing = set(inventory["cases"]) - set(report["cases"])
            report["missing_cases"] = sorted(missing)
            report["completeness"] = "complete" if not missing else "incomplete_campaign_not_silent_exclusion"
            report["status_counts"] = {}
            for case in report["cases"].values():
                report["status_counts"][case["status"]] = report["status_counts"].get(case["status"], 0) + 1
            require(not missing, "Every planned case must appear, passing or not")
            report["speedup_computed"] = False
            report["global_speedup_across_z_profiles"] = None
        report["status"] = "pass" if report["status_counts"].get("pass") == len(inventory["cases"]) else "partial"
    finally:
        report["artifacts_sha256"] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*"))
                                      if p.is_file() and p.name != "summary.json"}
        (out / "summary.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
        print(f"{report['status'].upper()}: campaign evidence in {out}")
        print(f"status counts: {report.get('status_counts')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
