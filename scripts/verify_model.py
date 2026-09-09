"""Run M1 tests and export a deterministic, hashed reference-vector sample."""

import hashlib
import importlib
import io
import json
import platform
import random
import struct
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model import xqdot4z as model

VECTOR_SEED = 20260908
VECTOR_RANDOM_WORD_PAIRS = 1024


def input_files():
    files = [ROOT / "model/SPEC.md", ROOT / "scripts/verify_model.py"]
    for pattern in ("model/*.py", "tests/test_xqdot4z.py", "tests/data/qdot4z_examples.json"):
        files.extend(ROOT.glob(pattern))
    return sorted(set(files))


def export_vectors(out):
    """Five hex columns for a future SV $fscanf; JSONL keeps signed results too."""
    examples = json.loads((ROOT / "tests/data/qdot4z_examples.json").read_text())
    operands = [(case["name"], int(case["weights_word"], 16),
                 int(case["activations_word"], 16), case["zero_point"], case["half"],
                 case["expected_signed"]) for case in examples["cases"]]
    for position in range(8):
        for activation in (-128, 127):
            # Directed lane markers exercise both halves and signs.
            operands.append((f"lane_{position}_a{activation}", 15 << (4 * position),
                             struct.pack("b", activation)[0] << (8 * (position % 4)),
                             8, position // 4, 7 * activation))
    rng = random.Random(VECTOR_SEED)
    for i in range(VECTOR_RANDOM_WORD_PAIRS):
        word, acts, z = rng.getrandbits(32), rng.getrandbits(32), rng.randrange(16)
        # Independent extraction: reversed hex digits and struct signed bytes.
        weights = [int(nibble, 16) for nibble in f"{word:08x}"[::-1]]
        activations = struct.unpack("4b", acts.to_bytes(4, "little"))
        for half in (0, 1):
            selected = weights[4 * half:4 * half + 4]
            expected = sum(w * a for w, a in zip(selected, activations)) - z * sum(activations)
            operands.append((f"random_{i}_half{half}", word, acts, z, half, expected))
    with (out / "vectors.txt").open("w") as text_file, (out / "vectors.jsonl").open("w") as json_file:
        for name, word, acts, z, half, expected in operands:
            actual = model.qdot4z(word, acts, z, half)
            if actual != expected:
                raise RuntimeError(f"Export oracle mismatch: {name}")
            bits = int.from_bytes(struct.pack("<i", expected), "little")
            if model.qdot4z_bits(word, acts, z, half) != bits:
                raise RuntimeError(f"Export encoding mismatch: {name}")
            text_file.write(f"{word:08x} {acts:08x} {z:x} {half:x} {bits:08x}\n")
            json_file.write(json.dumps({
                "name": name, "weights_word": f"{word:08x}", "activations_word": f"{acts:08x}",
                "zero_point": z, "half": half, "expected_signed": expected,
                "expected_u32": f"{bits:08x}"
            }, sort_keys=True) + "\n")
    return len(operands)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "model/results" / stamp
    out.mkdir(parents=True, exist_ok=False)
    summary = {
        "status": "running", "timestamp_utc": stamp, "contract_version": model.CONTRACT_VERSION,
        "scope": "Python numerical reference only; no RTL or performance verification",
        "python": sys.version, "platform": platform.platform(),
        "command": "python3 scripts/verify_model.py",
        "sources_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in input_files()},
    }
    stream = io.StringIO()
    try:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_xqdot4z.py")
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        summary["unittest"] = {
            "tests_run": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "skipped": len(result.skipped),
        }
        test_module = importlib.import_module("test_xqdot4z")
        summary["test_seed"] = test_module.SEED
        summary["completed_counts"] = dict(test_module.COMPLETED_COUNTS)
        if not result.wasSuccessful() or result.skipped or result.testsRun == 0:
            raise RuntimeError("Numerical-contract tests failed or were skipped")
        summary["exported_vectors"] = export_vectors(out)
        summary["vector_seed"] = VECTOR_SEED
        summary["vector_random_word_pairs"] = VECTOR_RANDOM_WORD_PAIRS
        summary["status"] = "pass"
    except Exception as error:
        summary["status"] = "fail"
        summary["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (out / "unittest.log").write_text(stream.getvalue())
        summary["artifacts_sha256"] = {
            name: hashlib.sha256((out / name).read_bytes()).hexdigest()
            for name in ("unittest.log", "vectors.txt", "vectors.jsonl") if (out / name).is_file()}
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(stream.getvalue(), end="")
        print("Evidence:", out)
        print("Status:", summary["status"])


if __name__ == "__main__":
    main()
