"""M2: standalone combinational RTL versus the frozen M1 numerical reference."""

import gzip
import hashlib
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
sys.path.insert(0, str(ROOT))
from model import xqdot4z as model

SEED = 20260909
SOURCES = ("rtl/xqdot4z.v", "tests/rtl/tb_xqdot4z.sv", "scripts/verify_rtl.py")
EXPECTED_COUNTS = {
    "m1_vectors": 2068,
    "single_term_lane_placements": 524288,
    "mixed_extrema": 8192,
    "random_dot_products": 20000,
    "unused_half_vectors": 2048,
    "single_input_bit_transitions": 138,
}
MUTATIONS = {
    "unsigned_activations": ("wire signed [7:0] activation", "wire [7:0] activation"),
    "signed_u4_weights": ("$signed({1'b0, selected_weights[4*lane +: 4]})",
                          "$signed(selected_weights[4*lane +: 4])"),
    "ignore_half": ("half ? weights_word[31:16] : weights_word[15:0]",
                    "weights_word[15:0]"),
    "zero_extend_result": ("{{17{subtotal[14]}}, subtotal}", "{17'b0, subtotal}"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def reference_evidence():
    state_path = ROOT / "docs/MODEL_STATE.json"
    state = json.loads(state_path.read_text())
    path = ROOT / state["evidence"]
    require(sha(path) == state["evidence_sha256"], "M1 evidence hash mismatch")
    report = json.loads(path.read_text())
    require(report["status"] == "pass", "M1 is not verified")
    require(report["contract_version"] == model.CONTRACT_VERSION, "M1 version mismatch")
    for name, digest in report["sources_sha256"].items():
        require(sha(ROOT / name) == digest, f"Stale M1 source: {name}")
    vectors = path.parent / "vectors.txt"
    require(sha(vectors) == report["artifacts_sha256"]["vectors.txt"], "M1 vectors changed")
    return vectors, {
        "state": str(state_path.relative_to(ROOT)), "state_sha256": sha(state_path),
        "evidence": state["evidence"], "evidence_sha256": sha(path),
        "vectors": str(vectors.relative_to(ROOT)), "vectors_sha256": sha(vectors),
        "sources_sha256": report["sources_sha256"],
    }


def make_vectors(path, pinned_vectors):
    counts = {name: 0 for name in EXPECTED_COUNTS}
    with path.open("w") as stream:
        def emit(group, word, acts, z, half, expected=None):
            # Separate extraction and factored arithmetic, not model packing.
            weights = [int(n, 16) for n in f"{word:08x}"[::-1]][4*half:4*half+4]
            activations = struct.unpack("4b", acts.to_bytes(4, "little"))
            factored = sum(w*a for w, a in zip(weights, activations)) - z*sum(activations)
            require(expected is None or expected == factored, f"Directed oracle: {group}")
            require(model.qdot4z(word, acts, z, half) == factored, f"M1 oracle: {group}")
            bits = int.from_bytes(struct.pack("<i", factored), "little")
            require(model.qdot4z_bits(word, acts, z, half) == bits, f"M1 bits: {group}")
            stream.write(f"{word:08x} {acts:08x} {z:x} {half:x} {bits:08x}\n")
            counts[group] += 1

        for line in pinned_vectors.read_text().splitlines():
            require(re.fullmatch(r"[0-9a-f]{8} [0-9a-f]{8} [0-9a-f] [01] [0-9a-f]{8}", line)
                    is not None, "Malformed pinned vector")
            word, acts, z, half, bits = (int(x, 16) for x in line.split())
            expected = struct.unpack("<i", bits.to_bytes(4, "little"))[0]
            emit("m1_vectors", word, acts, z, half, expected)

        # Every legal (w,z,a), each of eight physical weight positions.
        # All other activations are zero: this does not exhaust four-term inputs.
        for w, z, a in itertools.product(range(16), range(16), range(-128, 128)):
            for position in range(8):
                word = (z * 0x11111111 & ~(15 << (4*position))) | w << (4*position)
                acts = (a & 255) << (8*(position % 4))
                emit("single_term_lane_placements", word, acts, z, position // 4, (w-z)*a)

        # Every assignment of low/high extrema to all four lanes, for every z/h.
        for z, half, wm, am in itertools.product(range(16), range(2), range(16), range(16)):
            weights = [15 if wm & (1 << i) else 0 for i in range(4)]
            activations = [-128 if am & (1 << i) else 127 for i in range(4)]
            selected = sum(w << (4*i) for i, w in enumerate(weights))
            word = (selected << (16*half)) | (0x5a5a << (16*(1-half)))
            acts = int.from_bytes(struct.pack("4b", *activations), "little")
            emit("mixed_extrema", word, acts, z, half)

        rng = random.Random(SEED)
        for _ in range(10000):
            word, acts, z = rng.getrandbits(32), rng.getrandbits(32), rng.randrange(16)
            for half in (0, 1):
                emit("random_dot_products", word, acts, z, half)
        for _ in range(1024):
            word, acts = rng.getrandbits(32), rng.getrandbits(32)
            z, half = rng.randrange(16), rng.randrange(2)
            emit("unused_half_vectors", word, acts, z, half)
            emit("unused_half_vectors", word ^ (0xffff << (16*(1-half))), acts, z, half)
        base = [0x78f04a95, 0x02ff7f80, 8, 0]
        for port, width in enumerate((32, 32, 4, 1)):
            for bit in range(width):
                emit("single_input_bit_transitions", *base)
                changed = base.copy()
                changed[port] ^= 1 << bit
                emit("single_input_bit_transitions", *changed)
    require(counts == EXPECTED_COUNTS, f"Incomplete vector generation: {counts}")
    return counts


def main():
    # Expected $fatal from the second simulator must not leave a core dump.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "rtl/results" / stamp
    out.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "running", "timestamp_utc": stamp, "contract_version": model.CONTRACT_VERSION,
        "scope": "M2 isolated combinational RTL; no ISA integration, synthesis or performance",
        "command": "python3 scripts/verify_rtl.py", "python": sys.version,
        "platform": platform.platform(), "seed": SEED,
        "sources_sha256": {name: sha(ROOT / name) for name in SOURCES}, "commands": [],
    }

    def run(name, command, *, expected_failure=None):
        command = [str(arg) for arg in command]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
        (out / f"{name}.log").write_text(result.stdout + result.stderr)
        report["commands"].append({"name": name, "argv": command, "returncode": result.returncode})
        if expected_failure:
            require(result.returncode != 0 and expected_failure in result.stdout + result.stderr,
                    f"{name}: expected failure not detected; see log")
        else:
            require(result.returncode == 0, f"{name}: command failed; see log")
        return result.stdout + result.stderr

    try:
        pinned, reference = reference_evidence()
        report["reference"] = reference
        for tool in ("iverilog", "vvp", "verilator", "g++", "make"):
            require(shutil.which(tool) is not None, f"Missing tool: {tool}")
        report["tools"] = {}
        for name, args in (("iverilog", ["-V"]), ("vvp", ["-V"]),
                           ("verilator", ["--version"]), ("g++", ["--version"]),
                           ("make", ["--version"])):
            report["tools"][name] = run(f"version_{name}", [name, *args]).splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="xqdot4z-m2-") as temporary:
            build = Path(temporary)
            vectors = build / "vectors.txt"
            counts = make_vectors(vectors, pinned)
            total = sum(counts.values())
            report["completed_counts"] = counts
            report["vectors_count"] = total
            report["vectors_uncompressed_sha256"] = sha(vectors)
            # Preserve full stimuli, deterministically compressed, not only seeds.
            with (out / "vectors.txt.gz").open("wb") as archive:
                with gzip.GzipFile(filename="", fileobj=archive, mode="wb", mtime=0) as compressed:
                    with vectors.open("rb") as source:
                        shutil.copyfileobj(source, compressed)
            print(f"Generated {total} oracle-checked vectors", flush=True)
            rtl, bench = ROOT / SOURCES[0], ROOT / SOURCES[1]
            run("lint", ["verilator", "--lint-only", "--Wall", "--top-module", "xqdot4z", rtl])
            report["lint"] = "pass_no_waivers"
            run("iverilog_build", ["iverilog", "-g2012", "-Wall", "-s", "tb_xqdot4z",
                                   "-o", build / "sim.vvp", rtl, bench])
            run("verilator_build", ["verilator", "--binary", "--timing", "--timescale", "1ns/1ps",
                                    "--top-module", "tb_xqdot4z", "--Mdir", build / "obj",
                                    "-j", "2", rtl, bench])
            report["simulators"] = {}
            for simulator, command in (("iverilog", ["vvp", build / "sim.vvp"]),
                                       ("verilator", [build / "obj/Vtb_xqdot4z"])):
                log = run(simulator, [*command, f"+VECTORS={vectors}", f"+COUNT={total}"])
                require(re.findall(r"RTL_PASS checked=(\d+)", log) == [str(total)],
                        f"{simulator}: missing or inconsistent completion marker")
                report["simulators"][simulator] = {"status": "pass", "checked": total}
                print(f"{simulator}: {total} comparisons passed", flush=True)
                controls = {
                    "wrong_expected": ("00000000 00000000 0 0 00000001\n", 1, "RTL_FAIL mismatch"),
                    "empty": ("", 1, "RTL_FAIL vector count"),
                    "truncated": ("00000000 00000000 0\n", 1, "RTL_FAIL malformed"),
                    "trailing_partial": ("00000000 00000000 0 0 00000000\n00000000 0\n",
                                         1, "RTL_FAIL malformed"),
                    "extra_field": ("00000000 00000000 0 0 00000000 0\n", 1, "RTL_FAIL malformed"),
                    "out_of_range": ("00000000 00000000 0 2 00000000\n", 1, "RTL_FAIL out-of-range"),
                    "count_mismatch": ("00000000 00000000 0 0 00000000\n", 2, "RTL_FAIL vector count"),
                }
                detected = []
                for name, (contents, count, marker) in controls.items():
                    fixture = out / f"control_{name}.txt"
                    fixture.write_text(contents)
                    run(f"{simulator}_{name}", [*command, f"+VECTORS={fixture}", f"+COUNT={count}"],
                        expected_failure=marker)
                    detected.append(name)
                run(f"{simulator}_missing_file", [*command, f"+VECTORS={build / 'absent.txt'}", "+COUNT=1"],
                    expected_failure="RTL_FAIL cannot open")
                detected.append("missing_file")
                report["simulators"][simulator]["negative_controls_detected"] = detected

            report["mutations_detected"] = []
            original = rtl.read_text()
            for name, (before, after) in MUTATIONS.items():
                require(original.count(before) == 1, f"Mutation site changed: {name}")
                mutant = out / f"mutant_{name}.v"
                mutant.write_text(original.replace(before, after))
                run(f"mutant_{name}_build", ["iverilog", "-g2012", "-s", "tb_xqdot4z", "-o",
                                           build / "mutant.vvp", mutant, bench])
                run(f"mutant_{name}", ["vvp", build / "mutant.vvp", f"+VECTORS={vectors}",
                                       f"+COUNT={total}"], expected_failure="RTL_FAIL mismatch")
                report["mutations_detected"].append(name)
            report["status"] = "pass"
    except Exception as error:
        report["status"] = "fail"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["artifacts_sha256"] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print("Evidence:", out, flush=True)
        print("Status:", report["status"], flush=True)


if __name__ == "__main__":
    main()
