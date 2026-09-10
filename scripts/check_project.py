"""Check pinned evidence and bilingual manuscript consistency; does not simulate."""

import gzip
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_model():
    state = json.loads((ROOT / "docs/MODEL_STATE.json").read_text())
    evidence = ROOT / state["evidence"]
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == state["evidence_sha256"]
    report = json.loads(evidence.read_text())
    assert report["status"] == "pass"
    assert report["contract_version"] == state["contract_version"]
    version = re.search(r'^CONTRACT_VERSION = "([^"]+)"',
                        (ROOT / "model/xqdot4z.py").read_text(), re.M).group(1)
    assert version == state["contract_version"]
    assert f"contrato numérico v{version}" in (ROOT / "model/SPEC.md").read_text()
    inputs = {"model/SPEC.md", "scripts/verify_model.py"}
    for pattern in ("model/*.py", "tests/test_xqdot4z.py", "tests/data/qdot4z_examples.json"):
        inputs.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    assert inputs == set(report["sources_sha256"]), "Numerical-model input inventory changed"
    for name, digest in report["sources_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (
            f"Stale model evidence: {name}; run make model-test and review its evidence")
    for name, digest in report["artifacts_sha256"].items():
        assert hashlib.sha256((evidence.parent / name).read_bytes()).hexdigest() == digest, name
    assert report["unittest"] == {"tests_run": 15, "failures": 0, "errors": 0, "skipped": 0}
    assert report["completed_counts"]["single_term_tuples"] == 65536
    assert report["completed_counts"]["single_term_lane_placements"] == 524288
    assert report["completed_counts"]["random_dot_products"] == 20000
    rows = [json.loads(line) for line in (evidence.parent / "vectors.jsonl").read_text().splitlines()]
    vectors = (evidence.parent / "vectors.txt").read_text().splitlines()
    assert len(rows) == len(vectors) == report["exported_vectors"] == 2068
    for row, vector in zip(rows, vectors):
        fields = [int(token, 16) for token in vector.split()]
        assert fields == [int(row["weights_word"], 16), int(row["activations_word"], 16),
                          row["zero_point"], row["half"], int(row["expected_u32"], 16)]
        assert -7680 <= row["expected_signed"] <= 7680
        assert fields[-1] == row["expected_signed"] % (1 << 32)
    print("OK: numerical contract v0.1, pinned test evidence and 2068 paired reference vectors.")


def check_rtl():
    state = json.loads((ROOT / "docs/RTL_STATE.json").read_text())
    evidence = ROOT / state["evidence"]
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == state["evidence_sha256"]
    report = json.loads(evidence.read_text())
    assert state["milestone"] == "M2" and report["status"] == "pass"
    assert state["status"] == "isolated_rtl_verified"
    assert state["integrated_in_kuntur"] is False
    assert state["performance_measured"] is False
    assert report["contract_version"] == state["contract_version"] == "0.1"
    inputs = {"scripts/verify_rtl.py"}
    for pattern in ("rtl/*.v", "tests/rtl/*.sv"):
        inputs.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    assert inputs == set(report["sources_sha256"]), "Standalone RTL input inventory changed"
    for name, digest in report["sources_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (
            f"Stale M2 evidence: {name}; run make rtl-test and review its evidence")
    reference = report["reference"]
    model_state_path = ROOT / reference["state"]
    assert hashlib.sha256(model_state_path.read_bytes()).hexdigest() == reference["state_sha256"]
    model_state = json.loads(model_state_path.read_text())
    assert reference["evidence"] == model_state["evidence"]
    assert reference["evidence_sha256"] == model_state["evidence_sha256"]
    model_report = json.loads((ROOT / model_state["evidence"]).read_text())
    assert reference["sources_sha256"] == model_report["sources_sha256"]
    pinned_vectors = ROOT / reference["vectors"]
    assert hashlib.sha256(pinned_vectors.read_bytes()).hexdigest() == reference["vectors_sha256"]
    assert report["seed"] == 20260909
    assert report["completed_counts"] == {
        "m1_vectors": 2068, "single_term_lane_placements": 524288,
        "mixed_extrema": 8192, "random_dot_products": 20000,
        "unused_half_vectors": 2048, "single_input_bit_transitions": 138,
    }
    total = sum(report["completed_counts"].values())
    assert report["vectors_count"] == total == 556734
    assert report["lint"] == "pass_no_waivers"
    expected_controls = {"wrong_expected", "empty", "truncated", "trailing_partial",
                         "extra_field", "out_of_range", "count_mismatch", "missing_file"}
    assert set(report["simulators"]) == {"iverilog", "verilator"}
    for simulator in report["simulators"].values():
        assert simulator["status"] == "pass" and simulator["checked"] == total
        assert set(simulator["negative_controls_detected"]) == expected_controls
    assert set(report["mutations_detected"]) == {
        "unsigned_activations", "signed_u4_weights", "ignore_half", "zero_extend_result"}
    artifacts = {p.name for p in evidence.parent.iterdir() if p.is_file() and p.name != "summary.json"}
    assert artifacts == set(report["artifacts_sha256"]), "M2 artifact inventory changed"
    for name, digest in report["artifacts_sha256"].items():
        assert hashlib.sha256((evidence.parent / name).read_bytes()).hexdigest() == digest, name
    digest = hashlib.sha256()
    prefix = []
    lines = 0
    with gzip.open(evidence.parent / "vectors.txt.gz", "rb") as stream:
        for lines, line in enumerate(stream, start=1):
            digest.update(line)
            assert re.fullmatch(rb"[0-9a-f]{8} [0-9a-f]{8} [0-9a-f] [01] [0-9a-f]{8}\n", line)
            bits = int(line.split()[-1], 16)
            signed = bits if bits < (1 << 31) else bits - (1 << 32)
            assert -7680 <= signed <= 7680
            if lines <= 2068:
                prefix.append(line)
    assert lines == total
    assert digest.hexdigest() == report["vectors_uncompressed_sha256"]
    assert b"".join(prefix) == pinned_vectors.read_bytes(), "M1 vector prefix changed"
    print("OK: M2 hashes, 556734 vectors per simulator, 8 controls each and 4 RTL mutations.")
    return total


def check_integration():
    historical = json.loads((ROOT / "docs/CORE_PRE_M3.json").read_text())
    archive, old_evidence = ROOT / historical["archive"], ROOT / historical["evidence"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == historical["archive_sha256"]
    assert hashlib.sha256(old_evidence.read_bytes()).hexdigest() == historical["evidence_sha256"]
    old_report = json.loads(old_evidence.read_text())
    assert old_report["status"] == "pass"
    with tarfile.open(archive, "r:gz") as frozen:
        members = frozen.getmembers()
        assert len(members) == len(old_report["sources_sha256"])
        assert {m.name for m in members} == set(old_report["sources_sha256"])
        for member in members:
            assert member.isfile()
            assert hashlib.sha256(frozen.extractfile(member).read()).hexdigest() == old_report["sources_sha256"][member.name]
    state_path = ROOT / "docs/INTEGRATION_STATE.json"
    state = json.loads(state_path.read_text())
    evidence = ROOT / state["evidence"]
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == state["evidence_sha256"]
    report = json.loads(evidence.read_text())
    assert state["milestone"] == "M3a" and state["status"] == "immediate_integration_verified"
    assert state["runtime_zero_point_supported"] is False and state["performance_measured"] is False
    assert state["regression_enable_xqdot4"] == 0
    assert report["status"] == "pass" and report["isa_version"] == state["isa_version"] == "0.1"
    inputs = {"scripts/verify_integration.py", "isa/SPEC.md", "rtl/xqdot4z.v"}
    for pattern in ("isa/*.py", "isa/*.inc", "tests/integration/*.py", "tests/integration/*.sv",
                    "kuntur/rtl/*.v", "model/*.py"):
        inputs.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    assert inputs == set(report["sources_sha256"]), "M3a input inventory changed"
    for name, digest in report["sources_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, f"Stale M3a evidence: {name}"
        assert hashlib.sha256((evidence.parent / "sources" / name).read_bytes()).hexdigest() == digest
    for name, reference in report["reference_states"].items():
        path = ROOT / f"docs/{name}.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference["state_sha256"]
        assert json.loads(path.read_text()) == reference["state"]
    assert report["seed"] == 20260910
    assert report["encoding_pairs"] == report["python_decoder_checks"] == 1024
    assert report["decoder_checks"] == 32768
    assert report["encoder_rejections"] == 9 and report["macro_rejections"] == 4
    assert report["forwarding_coverage"] == {"weights": [0,1,2], "activations": [0,1,2]}
    assert set(report["mutations_detected"]) == {"no_weights_forwarding", "ignore_half"}
    assert all("mismatch" in reason for reason in report["mutations_detected"].values())
    assert len(report["programs"]) == 25
    for name, case in report["programs"].items():
        assert set(case["simulators"]) == {"iverilog", "verilator"}
        assert case["simulators"]["iverilog"] == case["simulators"]["verilator"], name
        expected = json.loads((evidence.parent / f"{name}.expected.json").read_text())
        observed = case["simulators"]["iverilog"]
        assert observed["retired"] == len(expected["retired"])
        assert observed["stores"] == len(expected["stores"])
        assert observed["qdots"] == len(expected["qdots"])
    assert report["programs"]["all_z_h_random"]["simulators"]["iverilog"]["qdots"] == 1056
    artifacts = {str(p.relative_to(evidence.parent)) for p in evidence.parent.rglob("*")
                 if p.is_file() and p != evidence}
    assert artifacts == set(report["artifacts_sha256"]), "M3a artifact inventory changed"
    for name, digest in report["artifacts_sha256"].items():
        assert hashlib.sha256((evidence.parent / name).read_bytes()).hexdigest() == digest, name
    print("OK: pre-M3 snapshot, M3a sources/artifacts, 25 programs in two simulators and 2 mutations.")
    return len(report["programs"])


def check_scalar():
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_scalar import sources, programs, compare
    state = json.loads((ROOT / "docs/SCALAR_STATE.json").read_text())
    evidence = ROOT / state["evidence"]
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == state["evidence_sha256"]
    report = json.loads(evidence.read_text())
    assert state["milestone"] == "M3b-partial" and state["status"] == "scalar_mul_verified"
    assert state["enabled_by_default"] is False and state["performance_measured"] is False
    assert state["full_comparison_variants_implemented"] is False
    assert state["full_m_or_zmmul_implemented"] is False
    assert state["regression_enable_xqdot4"] == 0
    assert state["tested_mul_xqdot4z_configurations"] == [[0,0],[0,1],[1,0],[1,1]]
    assert report["status"] == "pass" and report["seed"] == 20260911
    inputs = {str(p.relative_to(ROOT)) for p in sources()}
    assert inputs == set(report["sources_sha256"]), "Scalar input inventory changed"
    for name, digest in report["sources_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, f"Stale MUL evidence: {name}"
        assert hashlib.sha256((evidence.parent / "sources" / name).read_bytes()).hexdigest() == digest
    assert report["unit_counts"] == dict(s8_pairs=65536,edge_pairs=144,power_pairs=1024,random_pairs=20000)
    assert report["unit_lint"] == "pass_no_waivers"
    assert set(report["unit"]) == {"iverilog", "verilator"}
    controls = {"wrong_expected", "empty", "truncated", "extra_field", "bad_hex",
                "count_mismatch", "trailing_partial", "missing_file"}
    for simulator in report["unit"].values():
        assert simulator["checked"] == 86704
        assert set(simulator["negative_controls_detected"]) == controls
    lines = (evidence.parent / "vectors.txt").read_text().splitlines()
    assert len(lines) == 86704
    for line in lines:
        assert re.fullmatch(r"[0-9a-f]{8} [0-9a-f]{8} [0-9a-f]{8}", line)
        a,b,result = (int(field,16) for field in line.split())
        assert result == a*b % (1 << 32)
    assert report["encoding_pairs"] == 32768 and report["decoder_checks"] == 131072
    assert set(report["unit_mutations_detected"]) == {"add_instead_of_mul", "truncate_inputs_16"}
    assert set(report["pipeline_mutations_detected"]) == {"no_mul_lhs_forwarding", "no_mul_rhs_forwarding"}
    assert all("mismatch" in reason for reason in report["pipeline_mutations_detected"].values())
    assert report["forwarding_coverage"] == {
        sim: {"lhs": [0,1,2], "rhs": [0,1,2]} for sim in ("iverilog", "verilator")}
    cases = {case["name"]:case for case in programs()}
    assert len(cases) == 49 and set(cases) == set(report["programs"])
    for name, case in report["programs"].items():
        assert (case["enable_mul"],case["enable_xqdot4z"]) == (cases[name]["m"],cases[name]["q"])
        expected = json.loads((evidence.parent / f"{name}.expected.json").read_text())
        assert set(case["simulators"]) == {"iverilog", "verilator"}
        for sim, observed in case["simulators"].items():
            log = (evidence.parent / f"{name}_{sim}.log").read_text()
            assert compare(log, expected, name) == observed
            assert observed["stalls"] == cases[name]["stalls"]
        assert case["simulators"]["iverilog"] == case["simulators"]["verilator"]
    artifacts = {str(p.relative_to(evidence.parent)) for p in evidence.parent.rglob("*")
                 if p.is_file() and p != evidence}
    assert artifacts == set(report["artifacts_sha256"]), "Scalar artifact inventory changed"
    for name, digest in report["artifacts_sha256"].items():
        assert hashlib.sha256((evidence.parent / name).read_bytes()).hexdigest() == digest, name
    repeated_path = ROOT / state["repeat_evidence"]
    assert hashlib.sha256(repeated_path.read_bytes()).hexdigest() == state["repeat_evidence_sha256"]
    repeated = json.loads(repeated_path.read_text())
    assert repeated["status"] == "pass"
    for key in ("sources_sha256", "tools", "unit_counts", "unit", "programs",
                "encoding_pairs", "decoder_checks", "forwarding_coverage",
                "unit_mutations_detected", "pipeline_mutations_detected"):
        assert report[key] == repeated[key], f"Scalar repeat differs: {key}"
    repeat_files = {str(p.relative_to(repeated_path.parent)) for p in repeated_path.parent.rglob("*")
                    if p.is_file() and p != repeated_path}
    assert repeat_files == set(repeated["artifacts_sha256"])
    for name, digest in repeated["artifacts_sha256"].items():
        assert hashlib.sha256((repeated_path.parent / name).read_bytes()).hexdigest() == digest, name
    def paired_inputs(run):
        return {k:v for k,v in run["artifacts_sha256"].items()
                if k.endswith((".S", ".elf", ".bin", ".mem", ".expected.json")) or k == "vectors.txt"}
    assert paired_inputs(report) == paired_inputs(repeated)
    assert len(paired_inputs(report)) == 249
    print("OK: scalar MUL, 86704 vectors per simulator, 49 programs, 4 configurations and 4 mutations.")
    print("OK: repeated scalar run, identical sources/results and 249 paired input/reference artifacts.")
    return len(cases)


def check_packed():
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_packed import sources, observations, check_matrices, COUNTS
    state = json.loads((ROOT / "docs/PACKED_STATE.json").read_text())
    evidence = ROOT / state["evidence"]
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == state["evidence_sha256"]
    report = json.loads(evidence.read_text())
    assert state["milestone"] == "M3b-partial"
    assert state["status"] == "isolated_packed_rtl_verified"
    assert state["isa_encoding_assigned"] is False and state["integrated_in_kuntur"] is False
    assert state["performance_measured"] is False and state["synthesis_performed"] is False
    assert state["full_comparison_variants_implemented"] is False
    assert state["matrix_reconstruction_location"] == "host_verifier"
    assert report["status"] == "pass" and report["seed"] == 20260912
    assert report["contract_version"] == state["contract_version"] == "0.1"
    assert set(report["sources_sha256"]) == {str(p.relative_to(ROOT)) for p in sources()}
    for name, digest in report["sources_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, f"Stale B3 evidence: {name}"
        assert hashlib.sha256((evidence.parent / "sources" / name).read_bytes()).hexdigest() == digest
    for key in ("reference", "fused_reference"):
        reference = report[key]
        reference_state = ROOT / reference["state"]
        assert hashlib.sha256(reference_state.read_bytes()).hexdigest() == reference["state_sha256"]
        referenced = json.loads(reference_state.read_text())
        assert reference["evidence"] == referenced["evidence"]
        assert reference["evidence_sha256"] == referenced["evidence_sha256"]
    assert report["completed_counts"] == COUNTS
    assert report["vectors_count"] == sum(COUNTS.values()) == 67910
    assert report["matrix_trace_start"] == 66230
    assert report["lint"] == "pass_no_waivers"
    rows = (evidence.parent / "vectors.txt").read_text().splitlines()
    assert len(rows) == 67910
    vectors = []
    for line in rows:
        assert re.fullmatch(r"[0-9a-f]{8} [0-9a-f]{8} [0-9a-f] [01] [0-9a-f]{8} [0-9a-f]{8}",line)
        w,a,z,h,p,d = values = [int(field,16) for field in line.split()]
        weights = [(w >> (4*(i+4*h))) & 15 for i in range(4)]
        acts = [(a >> (8*i)) & 255 for i in range(4)]
        acts = [v if v<128 else v-256 for v in acts]
        expected_p = sum(x*y for x,y in zip(weights,acts))
        assert -7680 <= expected_p <= 7620
        assert p == expected_p % (1 << 32)
        assert d == (expected_p-z*sum(acts)) % (1 << 32)
        vectors.append(values)
    pinned = (ROOT / report["reference"]["vectors"]).read_text().splitlines()
    assert hashlib.sha256((ROOT / report["reference"]["vectors"]).read_bytes()).hexdigest() == report["reference"]["vectors_sha256"]
    assert len(pinned) == 2068
    for old, new in zip(pinned, vectors[:2068]):
        assert [int(field,16) for field in old.split()] == new[:4]+new[5:]
    fixtures = json.loads((evidence.parent / "matrix_cases.json").read_text())
    assert len(fixtures) == 24
    assert {(c["n"],c["g"],c["zero_point_mode"]) for c in fixtures} == {
        (n,g,mode) for n in (1,4,16) for g in (8,32) for mode in ("z0","z8","z15","row_group")}
    for case in fixtures:
        assert case["groups"] == 2
        for output in case["outputs"]:
            mode = case["zero_point_mode"]
            assert output["z"] == ((output["row"]+7*output["group"])%16 if mode == "row_group" else int(mode[1:]))
    controls = {"wrong_p", "wrong_d", "empty", "truncated", "trailing_partial", "extra_field",
                "bad_hex", "bad_half", "count_mismatch", "missing_file"}
    assert set(report["simulators"]) == {"iverilog", "verilator"}
    results = []
    for sim, result in report["simulators"].items():
        assert result["checked"] == 67910
        assert set(result["negative_controls_detected"]) == controls
        log = (evidence.parent / f"{sim}.log").read_text()
        observed = observations(log,66230,67910)
        assert check_matrices(fixtures,observed,vectors) == result["matrix_reconstruction"] == {
            "cases":24,"group_outputs":336,"distinct_vector_group_sums":48,"rtl_blocks":1680}
        results.append(observed)
    assert results[0] == results[1]
    assert set(report["mutations_detected"]) == {"signed_u4_weights", "unsigned_activations", "ignore_half", "zero_extend_result"}
    assert set(report["matrix_controls_detected"]) == {"wrong_group_sum", "missing_block"}
    artifacts = {str(p.relative_to(evidence.parent)) for p in evidence.parent.rglob("*")
                 if p.is_file() and p != evidence}
    assert artifacts == set(report["artifacts_sha256"])
    for name, digest in report["artifacts_sha256"].items():
        assert hashlib.sha256((evidence.parent / name).read_bytes()).hexdigest() == digest, name
    repeated_path = ROOT / state["repeat_evidence"]
    assert hashlib.sha256(repeated_path.read_bytes()).hexdigest() == state["repeat_evidence_sha256"]
    repeated = json.loads(repeated_path.read_text())
    assert repeated["status"] == "pass"
    for key in ("sources_sha256", "tools", "python", "platform", "completed_counts",
                "simulators", "mutations_detected", "matrix_controls_detected",
                "reference", "fused_reference"):
        assert report[key] == repeated[key], f"B3 repeat differs: {key}"
    repeat_files = {str(p.relative_to(repeated_path.parent)) for p in repeated_path.parent.rglob("*")
                    if p.is_file() and p != repeated_path}
    assert repeat_files == set(repeated["artifacts_sha256"])
    for name,digest in repeated["artifacts_sha256"].items():
        assert hashlib.sha256((repeated_path.parent / name).read_bytes()).hexdigest() == digest, name
    for name in ("vectors.txt", "matrix_cases.json"):
        assert report["artifacts_sha256"][name] == repeated["artifacts_sha256"][name]
    print("OK: isolated B3, 67910 paired vectors per simulator and 336 reconstructed matrix group outputs.")
    print("OK: B3 repeated with identical sources, vectors, fixtures and coverage.")
    return report["vectors_count"]


def check_packed_integration():
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_packed_integration import sources, programs, matrix_fixtures, compare, CONFIGS, execute
    state = json.loads((ROOT / "docs/PACKED_INTEGRATION_STATE.json").read_text())
    assert state["milestone"] == "M3b-partial" and state["status"] == "packed_integration_verified"
    assert state["instruction"] == "xqdot4" and state["isa_version"] == "0.1"
    assert state["integrated_in_kuntur"] is True and state["enabled_by_default"] is False
    assert state["performance_measured"] is state["synthesis_performed"] is False
    assert state["full_comparison_variants_implemented"] is False
    assert state["runtime_zero_point_supported_by_d"] is False
    cases = {case["name"]: case for case in programs()}
    fixtures = {fixture["name"]: fixture for fixture in matrix_fixtures()}
    assert len(cases) == 123 and len(fixtures) == 4

    def verify_report(path, digest):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        run = json.loads(path.read_text())
        assert run["status"] == "pass" and run["seed"] == 20260913
        assert run["isa_version"] == state["isa_version"]
        assert run["configurations"] == [list(cfg) for cfg in CONFIGS] == state["configurations_mul_d_b3"]
        assert set(run["sources_sha256"]) == {str(p.relative_to(ROOT)) for p in sources()}
        for name, source_hash in run["sources_sha256"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == source_hash, f"Stale B3 integration: {name}"
            assert hashlib.sha256((path.parent / "sources" / name).read_bytes()).hexdigest() == source_hash
        assert set(run["reference_states"]) == {"MODEL_STATE", "RTL_STATE", "PACKED_STATE"}
        for name, reference in run["reference_states"].items():
            reference_path = ROOT / f"docs/{name}.json"
            assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == reference["state_sha256"]
            assert json.loads(reference_path.read_text()) == reference["state"]
        assert run["encoding_pairs"] == 65536 and run["decoder_checks"] == 524288
        assert run["python_decoder_checks"] == 2048
        assert run["encoder_rejections"] == 9 and run["macro_rejections"] == 2
        assert set(run["mutations_detected"]) == {
            "no_packed_weights_forwarding", "no_packed_activations_forwarding", "ignore_packed_half"}
        assert all("mismatch" in reason for reason in run["mutations_detected"].values())
        coverage = {f"m{m}q{q}p1": dict(weights=[0,1,2], activations=[0,1,2])
                    for m in (0,1) for q in (0,1)}
        assert run["forwarding_coverage"] == {sim: coverage for sim in ("iverilog", "verilator")}
        assert set(run["programs"]) == set(cases)
        for name, case in cases.items():
            result = run["programs"][name]
            assert result["config"] == [case["m"], case["q"], case["p"]]
            binary = (path.parent / f"{name}.bin").read_bytes()
            assert len(binary) == result["program_bytes"]
            symbols = (path.parent / f"{name}_nm.log").read_text()
            reset = re.search(r"^([0-9a-f]+)\s+\w\s+reset_packed$", symbols, re.M)
            reset_pc = int(reset.group(1), 16) if reset else None
            assert result["reset"] == (reset_pc is not None)
            expected = execute(binary, case["q"], stop_before=reset_pc-8 if reset else None,
                               mul_enabled=bool(case["m"]), packed_enabled=bool(case["p"]))
            if reset: expected["fault"] = [3, 0]
            assert json.loads((path.parent / f"{name}.expected.json").read_text()) == expected
            assert set(result["simulators"]) == {"iverilog", "verilator"}
            for sim, observed in result["simulators"].items():
                log = (path.parent / f"{name}_{sim}.log").read_text()
                assert compare(log, expected, name) == observed
                assert observed["stalls"] == case["stalls"]
                if reset: assert "RESET_PASS" in log
            assert result["simulators"]["iverilog"] == result["simulators"]["verilator"]
        assert json.loads((path.parent / "matrix_fixtures.json").read_text()) == fixtures
        assert set(run["matrix_pairs"]) == set(fixtures)
        for name, fixture in fixtures.items():
            pair = run["matrix_pairs"][name]
            assert pair["b3"] == name + "_b3_m1q0p1" and pair["d"] == name + "_d_m1q1p0"
            outputs = [sum((w-z)*a for w,a in zip(row,fixture["activations"]))
                       for row,z in zip(fixture["weights"],fixture["zero_points"])]
            assert outputs == fixture["expected"]
            assert pair["outputs"] == [[64+4*i, v & 0xffffffff] for i,v in enumerate(outputs)]
            assert pair["activation_sum"] == sum(fixture["activations"]) == fixture["activation_sum"]
            assert pair["correction_location"] == "kuntur"
            b3, d = [json.loads((path.parent / f"{pair[key]}.expected.json").read_text()) for key in ("b3", "d")]
            assert b3["stores"] == d["stores"] and b3["stores"][-2:] == pair["outputs"]
            assert b3["regs"][11] == (pair["activation_sum"] & 0xffffffff)
            assert len(b3["packed_dots"]) == 6 and len(b3["muls"]) == 2 and not b3["qdots"]
            assert len(d["qdots"]) == 4 and not d["packed_dots"] and not d["muls"]
        for m in (0,1):
            for q in (0,1):
                assert run["programs"][f"numeric_m{m}q{q}p1"]["simulators"]["iverilog"]["packed_dots"] == 1032
        base = run["programs"]["base_m0q0p0"]["simulators"]
        assert all(result["simulators"] == base for name,result in run["programs"].items() if name.startswith("base_"))
        artifacts = {str(p.relative_to(path.parent)) for p in path.parent.rglob("*") if p.is_file() and p != path}
        assert artifacts == set(run["artifacts_sha256"])
        for name, artifact_hash in run["artifacts_sha256"].items():
            assert hashlib.sha256((path.parent / name).read_bytes()).hexdigest() == artifact_hash, name
        return run

    report = verify_report(ROOT / state["evidence"], state["evidence_sha256"])
    repeated = verify_report(ROOT / state["repeat_evidence"], state["repeat_evidence_sha256"])
    for key in ("sources_sha256", "tools", "python", "platform", "configurations", "reference_states",
                "programs", "matrix_pairs", "forwarding_coverage", "mutations_detected", "encoding_pairs",
                "decoder_checks", "python_decoder_checks", "encoder_rejections", "macro_rejections"):
        assert report[key] == repeated[key], f"B3 integration repeat differs: {key}"
    def paired_inputs(run):
        return {k:v for k,v in run["artifacts_sha256"].items()
                if k.endswith((".S", ".elf", ".bin", ".mem", ".expected.json")) or k == "matrix_fixtures.json"}
    assert paired_inputs(report) == paired_inputs(repeated)
    assert len(paired_inputs(report)) == 621
    print("OK: B3 integration, 123 programs in two simulators, 8 configurations and 3 mutations.")
    print("OK: 4 paired CPU fixtures (8 outputs), oracle replay and 621 repeated input/reference artifacts.")
    return len(cases)


def check_measurement():
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_measurement import programs, sources, identities, DEPTH
    state = json.loads((ROOT / "docs/MEASUREMENT_STATE.json").read_text())
    assert state["status"] == "measurement_contract_verified" and state["protocol_version"] == "0.6"
    assert state["component"] == "measurement_window_and_counters"
    assert state["expectations_derived_from_structure_not_runs"] is True
    assert state["kernels_implemented"] is state["campaign_executed"] is False
    assert state["performance_measured"] is False
    cases = {case["name"]: case for case in programs()}
    assert len(cases) == state["directed_programs"] == 8

    def verify_report(path, digest):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        run = json.loads(path.read_text())
        assert run["status"] == "pass"
        assert set(run["sources_sha256"]) == {str(p.relative_to(ROOT)) for p in sources()}
        for name, source_hash in run["sources_sha256"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == source_hash, f"Stale measurement: {name}"
        assert run["negative_controls"] == 3 and len(run["mutations_detected"]) == 4
        # Capacity is a build constant, not an observable: the same programs
        # must produce the same counters at the campaign capacity.
        assert run["capacity_control"] == dict(battery=2048, campaign=32768, programs=7)
        assert run["differentials"] == dict(load_use_stall_cycles=1, taken_control_cycles=2)
        assert set(run["programs"]) == set(cases)
        for name, case in cases.items():
            observed = run["programs"][name]["counters"]
            # Recompute the contract rather than trusting the recorded expectation.
            assert observed == case["expected"], name
            assert observed["cycles"] == (observed["retired_kernel"] + DEPTH +
                                          observed["stall_load_use"] +
                                          2*observed["flush_taken_control"]), name
            identities(name, observed, (1, observed["cycles"]))
            assert bool(run["programs"][name]["rationale"].strip()), name
        artifacts = {str(p.relative_to(path.parent)) for p in path.parent.rglob("*")
                     if p.is_file() and p != path}
        assert artifacts == set(run["artifacts_sha256"])
        for name, artifact_hash in run["artifacts_sha256"].items():
            assert hashlib.sha256((path.parent / name).read_bytes()).hexdigest() == artifact_hash, name
        return run

    report = verify_report(ROOT / state["evidence"], state["evidence_sha256"])
    repeated = verify_report(ROOT / state["repeat_evidence"], state["repeat_evidence_sha256"])
    for key in ("sources_sha256", "tools", "platform", "programs", "mutations_detected",
                "differentials", "negative_controls"):
        assert report[key] == repeated[key], f"Measurement repeat differs: {key}"
    print("OK: measurement window, 8 directed programs in two simulators, 3 controls and 4 harness mutations.")
    return len(cases)


def check_kernels():
    sys.path.insert(0, str(ROOT / "benchmarks"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_kernels import sources, SHAPES, SEEDS, SETTINGS, CUSTOM0, CUSTOM1, K
    from tensors import tensors, zero_points, expected_outputs
    from kernels import required_row_bodies
    state = json.loads((ROOT / "docs/KERNEL_STATE.json").read_text())
    assert state["status"] == "four_variant_kernels_verified"
    assert state["policy_implemented"] == "shared_tile_resident_skeleton_v2"
    assert state["variants_implemented"] == ["B1", "B2", "B3", "D"] and state["variants_pending"] == []
    assert state["headline_kernels_pending"] is False
    assert state["indirect_dispatch_forbidden"] is True
    assert state["instruction_capacity_words"] == 32768
    assert state["campaign_executed"] is state["pilot_executed"] is False
    assert state["speedup_computed"] is state["performance_comparison_drawn"] is False
    assert state["development_timings_observed"] is True

    def verify_report(path, digest):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        run = json.loads(path.read_text())
        assert run["status"] == "pass"
        assert set(run["sources_sha256"]) == {str(p.relative_to(ROOT)) for p in sources()}
        for name, source_hash in run["sources_sha256"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == source_hash, f"Stale kernels: {name}"
        assert run["paired_agreements"] == len(SHAPES) * len(SEEDS) * len(SETTINGS) == 24
        assert len(run["cases"]) == state["cases"]
        headline = 0
        for name, case in run["cases"].items():
            # Recompute the oracle from the seed rather than trust the record.
            activations, weights = tensors(case["seed"], case["rows"], run["k"])
            zeros = zero_points(case["profile"], case["setting"], case["rows"], run["k"] // run["g"])
            assert case["outputs"] == expected_outputs(weights, activations, zeros), name
            assert [row[0] for row in zeros] == case["zero_points"], name
            assert case["required_row_bodies"] == required_row_bodies(case["variant"], zeros), name
            if case["arm"] == "headline":
                headline += 1
                # The floor is the ISA's, never the implementer's.
                assert case["row_bodies_emitted"] == case["required_row_bodies"], name
            multiplies = case["instruction_mix"].get("0x33/mul", 0)
            opcodes = {int(key.split("/")[0], 16) for key in case["instruction_mix"]}
            # An indirect jump is the signature of dispatch, which the
            # specialization rule declines for every variant.
            assert 0x67 not in opcodes, f"{name}: indirect dispatch"
            if case["variant"] == "D":
                assert multiplies == 0 and CUSTOM0 in opcodes, name
            elif case["variant"] == "B1":
                assert multiplies == 0 and not ({CUSTOM0, CUSTOM1} & opcodes), name
            elif case["variant"] == "B2":
                assert multiplies == K * case["row_bodies_emitted"], name
                assert not ({CUSTOM0, CUSTOM1} & opcodes), name
            elif case["strength_reduction"] == "declined_no_dispatch":
                assert multiplies == case["row_bodies_emitted"], name
            else:
                assert multiplies == {"elide": 0, "no_multiply": 0,
                                      "shift": 0, "multiply": 1}[case["strength_reduction"]], name
        assert headline == 96, "One headline arm per variant and case"
        # Every case must pair D and B3 on the same integers.
        for rows in SHAPES:
            for seed in SEEDS:
                for profile, setting in SETTINGS:
                    tail = f"n{rows}_s{seed}_{profile}_{setting}"
                    outputs = {run["cases"][f"{v}_headline_{tail}"]["outputs"][0]
                               for v in ("B1", "B2", "B3", "D")}
                    assert len(outputs) == 1, tail
        artifacts = {str(p.relative_to(path.parent)) for p in path.parent.rglob("*")
                     if p.is_file() and p != path}
        assert artifacts == set(run["artifacts_sha256"])
        for name, artifact_hash in run["artifacts_sha256"].items():
            assert hashlib.sha256((path.parent / name).read_bytes()).hexdigest() == artifact_hash, name
        return run

    report = verify_report(ROOT / state["evidence"], state["evidence_sha256"])
    repeated = verify_report(ROOT / state["repeat_evidence"], state["repeat_evidence_sha256"])
    for key in ("sources_sha256", "tools", "platform", "cases", "paired_agreements"):
        assert report[key] == repeated[key], f"Kernel repeat differs: {key}"
    print(f"OK: B1, B2, B3 and D under policy v2, 24 four-way agreements over {len(report['cases'])} arms.")
    print("Kernel correctness only; the campaign stays blocked and no speedup is computed.")
    return len(report["cases"])


def check_inventory():
    """Recompute every planned case from its seed; the file is a record, not a source."""
    sys.path.insert(0, str(ROOT / "benchmarks"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from tensors import (tensors, zero_points, expected_outputs, activation_sum,
                         pack_activations, pack_weights)
    from materialize_tensors import digest, settings
    from collections import Counter
    state = json.loads((ROOT / "docs/INVENTORY_STATE.json").read_text())
    assert state["status"] == "inventory_materialized"
    assert state["measurements_taken"] is False
    inventory = ROOT / state["inventory"]
    assert hashlib.sha256(inventory.read_bytes()).hexdigest() == state["inventory_sha256"]
    record = json.loads(inventory.read_text())
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())
    grid = manifest["grid"]
    assert record["manifest_version"] == manifest["manifest_version"]
    assert record["shapes"] == grid["N"] and record["seeds"] == grid["tensor_seeds"]
    assert record["k"] == grid["K"][0] and record["g"] == grid["G"]
    assert record["measurements_taken"] is False
    k, g = record["k"], record["g"]
    declared = list(settings(manifest))

    for rows in grid["N"]:
        for seed in grid["tensor_seeds"]:
            activations, weights = tensors(seed, rows, k)
            entry = record["tensors"][f"n{rows}_s{seed}"]
            assert entry["packed_weights"] == [pack_weights(row) for row in weights]
            assert entry["packed_activations"] == pack_activations(activations)
            assert entry["activation_sum"] == activation_sum(activations)
            assert entry["sha256"] == digest(entry["packed_weights"], entry["packed_activations"])
            for profile, value in declared:
                zeros = zero_points(profile, value, rows, k // g)
                name = f"n{rows}_s{seed}_{profile}_{value}"
                group = record["groups"][name]
                assert group["zero_point_matrix"] == zeros, name
                assert group["expected_group_outputs"] == expected_outputs(weights, activations, zeros), name
                column = [row[0] for row in zeros]
                assert group["effective_z_histogram"] == {
                    str(z): c for z, c in sorted(Counter(column).items())}, name
                assert group["sha256"] == digest(zeros, group["expected_group_outputs"]), name
                for variant in grid["variants"]:
                    case = record["cases"][f"{variant}_{name}"]
                    assert case["group"] == name and case["variant"] == variant
                    assert case["sha256"] == digest(variant, entry["sha256"], group["sha256"])
    planned = len(grid["N"]) * len(grid["tensor_seeds"]) * len(declared) * len(grid["variants"])
    assert len(record["cases"]) == planned == 2280, "The inventory must cover every planned case"
    assert len(record["groups"]) == planned // len(grid["variants"])
    assert len(record["tensors"]) == len(grid["N"]) * len(grid["tensor_seeds"])
    # Identical inputs share a hash by construction: at N=1 there is no varying
    # zero point, so a constant control and the phase of the same value are the
    # same program. That degeneracy is checked, not waved through, and a
    # collision anywhere else would mean two different cases share inputs.
    groups_by_hash = {}
    for name, case in record["cases"].items():
        groups_by_hash.setdefault(case["sha256"], []).append(name)
    degenerate = record["regimes_coincide_at_one_row"]
    shared = set(degenerate["shared_settings"])
    collisions = {h: n for h, n in groups_by_hash.items() if len(n) > 1}
    assert sum(len(n) - 1 for n in collisions.values()) == degenerate["colliding_cases"] == 120
    for names in collisions.values():
        assert len(names) == 2, names
        cases = [record["cases"][n] for n in names]
        groups = [record["groups"][c["group"]] for c in cases]
        assert {c["variant"] for c in cases} == {cases[0]["variant"]}, names
        assert all(g["rows"] == 1 for g in groups), names
        assert {g["profile"] for g in groups} == {"zc_controls", "zs_balanced_u4"}, names
        assert {g["setting"] for g in groups} == {groups[0]["setting"]} and \
            groups[0]["setting"] in shared, names
    print(f"OK: {planned} planned cases materialized, recomputed from their seeds and hashed.")
    print("Inputs only; not one case has been run or measured.")
    return planned


def check_freeze():
    """Re-derive the freeze from the tree; a quiet edit must fail here."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from freeze_policies import IMPLEMENTS, disassemble, sha
    record = json.loads((ROOT / "docs/POLICY_FREEZE.json").read_text())
    assert record["required_before"] == "first_kernel_timing_including_pilot"
    assert record["post_measurement_change"] == (
        "new_version_with_reason_prior_observations_retained_and_affected_pairs_rerun")
    assert record["measurements_taken"] is False
    assert set(record["policies"]) == set(IMPLEMENTS)
    manifest = json.loads((ROOT / "benchmarks/campaign.json").read_text())["optimization"]
    kernels = json.loads((ROOT / "docs/KERNEL_STATE.json").read_text())
    evidence = ROOT / kernels["evidence"]
    report = json.loads(evidence.read_text())
    advice = "; a frozen policy changes only through its declared procedure"
    arms = 0
    for policy_id, entry in record["policies"].items():
        spec = IMPLEMENTS[policy_id]
        assert entry["policy"] == manifest[spec["manifest_key"]], f"{policy_id} policy text changed" + advice
        assert entry["variants"] == spec["variants"]
        assert entry["frozen_files_committed_with_this_record"] is True
        for group in ("generator", "tests"):
            assert set(entry[group]) == set(spec[group]), f"{policy_id} {group} inventory changed" + advice
            for path, digest in entry[group].items():
                assert sha(ROOT / path) == digest, f"{policy_id}: {path} changed since the freeze" + advice
        assert entry["kernel_evidence"] == kernels["evidence"]
        assert entry["kernel_evidence_sha256"] == kernels["evidence_sha256"]
        expected = {name for name, case in report["cases"].items() if case["variant"] in spec["variants"]}
        assert set(entry["arms"]) == expected, f"{policy_id} arm inventory changed" + advice
        for name, pinned in entry["arms"].items():
            assert sha(evidence.parent / f"{name}.S") == pinned["assembly"], name + advice
            assert sha(evidence.parent / f"{name}.bin") == pinned["text"], name + advice
            assert disassemble(evidence.parent / f"{name}.elf") == pinned["disassembly"], name + advice
            arms += 1
    print(f"OK: both policies frozen after {record['parent_git_revision'][:7]}; "
          f"{arms} arm listings, generators and tests re-derived.")
    return arms


def main():
    metadata = (ROOT / "paper/metadata.tex").read_text()
    def macro(name):
        match = re.search(r"\\newcommand\{\\" + name + r"\}\{([^}]+)\}", metadata)
        if not match:
            raise SystemExit(f"Missing metadata: {name}")
        return match.group(1)

    lock = json.loads((ROOT / "baseline/LOCK.json").read_text())
    evidence = ROOT / "audit/results" / macro("AuditRun") / "summary.json"
    report = json.loads(evidence.read_text())
    assert report["commit"] == lock["commit"] == macro("CoreCommit")
    assert int(macro("HistoricalPass")) == report["historical_regression"]["passed"]
    assert int(macro("HistoricalFail")) == report["historical_regression"]["failed"]
    assert report["snapshot_manifest_sha256"] == hashlib.sha256(
        (ROOT / "baseline/SHA256SUMS").read_bytes()).hexdigest()
    assert report["probe_source_sha256"] == hashlib.sha256(
        (ROOT / "audit/tests/tb_observations.sv").read_bytes()).hexdigest()
    assert report["runner_sha256"] == hashlib.sha256(
        (ROOT / "scripts/audit_core.py").read_bytes()).hexdigest()
    probes = report["observations"]
    assert len(probes) == 8
    assert sum(not p["matches"] for p in probes) == 5
    assert all(p["matches"] for p in probes if p["id"] in
               {"c_addi_control", "rv32_passthrough", "real_load_use"})

    state = json.loads((ROOT / "docs/CORE_STATE.json").read_text())
    current_path = ROOT / state["evidence"]
    assert hashlib.sha256(current_path.read_bytes()).hexdigest() == state["evidence_sha256"]
    current = json.loads(current_path.read_text())
    clone = ROOT / state["clone"]
    provenance = json.loads((clone / "UPSTREAM.json").read_text())
    assert provenance["project_name"] == state["core_name"] == "Kuntur"
    assert provenance["project_directory"] == state["clone"] == clone.name
    assert provenance["base_commit"] == state["upstream_commit"] == lock["commit"]
    assert current["status"] == "pass"
    assert state["regression_enable_mul"] == state["regression_enable_xqdot4z"] == state["regression_enable_xqdot4"] == 0
    for name, digest in current["sources_sha256"].items():
        assert hashlib.sha256((clone / name).read_bytes()).hexdigest() == digest, (
            f"Stale correction evidence: {name}; run make core-test and review the new evidence")
    # Detect added test/RTL inputs as well as modifications to known files.
    inputs = {"Makefile", "run_tests.sh"}
    for pattern in ("rtl/*.v", "verification/*.py", "verification/*.sv",
                    "tests/*.v", "tests/programs/*.mem"):
        inputs.update(str(p.relative_to(clone)) for p in clone.glob(pattern))
    assert inputs == set(current["sources_sha256"]), "Verification input inventory changed"
    expected_counts = {"historical": 26, "assembler_pairs": 28461,
                       "decompression_vectors": 28483, "signed_comparisons": 10036}
    for name, count in expected_counts.items():
        assert current["tests"][name] == count
    assert current["tests"]["original_signed_comparison"] == "expected_failure_reproduced"
    assert current["original_alu_sha256"] == hashlib.sha256(
        (ROOT / "baseline/upstream/rtl/alu.v").read_bytes()).hexdigest()
    for name in ("memory", "policy-hazards", "regfile"):
        assert current["tests"][name] == "pass"
    assert current["tests"]["verilator_lint"].startswith("pass")
    check_model()
    rtl_comparisons = check_rtl()
    integration_programs = check_integration()
    scalar_programs = check_scalar()
    packed_vectors = check_packed()
    packed_programs = check_packed_integration()
    check_measurement()
    check_kernels()
    check_inventory()
    check_freeze()
    from check_campaign import check as check_campaign
    check_campaign()

    bodies = []
    for language in ("es", "en"):
        entry = (ROOT / f"paper/main_{language}.tex").read_text()
        assert r"\documentclass[conference,letterpaper]{IEEEtran}" in entry
        assert r"\input{ieee_preamble}" in entry
        assert r"\bibliographystyle{IEEEtran}" in entry
        body = (ROOT / f"paper/content_{language}.tex").read_text()
        assert "Kuntur" in body
        assert f"{rtl_comparisons:,}".replace(",", r"\,") in body, "Paper M2 count differs"
        assert str(integration_programs) in body and "XQDot4Zi" in body, "Paper M3a status missing"
        assert str(scalar_programs) in body and "MUL" in body, "Paper scalar MUL status missing"
        assert f"{packed_vectors:,}".replace(",", r"\,") in body, "Paper B3 count differs"
        assert str(packed_programs) in body and "XQDot4" in body, "Paper B3 integration status missing"
        assert Path(provenance["source_path"]).name.lower() not in body.lower(), (
            f"{language}: use only Kuntur as the processor name in the manuscript")
        bodies.append(body)
        assert len(re.findall(r"\\section\{", body)) == 6
        abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1).strip()
        assert "\n\n" not in abstract, f"{language}: abstract must be one paragraph"
        assert 0 < len(abstract.split()) <= 250, f"{language}: abstract word count"
        assert not re.search(r"\\(?:cite|footnote|begin|\(|\[)|\$", abstract)
        keywords = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", body, re.S).group(1)
        assert 3 <= len(keywords.split(",")) <= 5
        assert r"\input{comparison_figure}" in body
        threats = "Amenazas a la validez" if language == "es" else "Threats to Validity"
        assert "\\subsection{" + threats + "}" in body, "Missing explicit threats-to-validity subsection"
        print(f"OK: {language.upper()} IEEE draft; abstract {len(abstract.split())} words.")
    for pattern in (r"\\cite\{([^}]+)\}", r"\\label\{([^}]+)\}",
                    r"\\begin\{equation\}(.*?)\\end\{equation\}"):
        assert re.findall(pattern, bodies[0], re.S) == re.findall(pattern, bodies[1], re.S), (
            "ES/EN citations, labels or equations differ")

    for tex in (ROOT / "paper").rglob("*.tex"):
        for name in re.findall(r"\\input\{([^}]+)\}", tex.read_text()):
            assert (ROOT / "paper" / (name + ".tex")).is_file(), name
    documents = [ROOT / "README.md", ROOT / "paper/README.md", ROOT / "benchmarks/README.md",
                 clone / "README.md", clone / "docs/CORE_CORRECTIONS.md",
                 clone / "verification/README.md", ROOT / "model/README.md",
                 ROOT / "model/SPEC.md", ROOT / "model/results/README.md",
                 ROOT / "tests/README.md", ROOT / "rtl/README.md", ROOT / "rtl/results/README.md",
                 ROOT / "isa/SPEC.md", ROOT / "tests/integration/README.md",
                 ROOT / "isa/scalar/SPEC.md", ROOT / "tests/scalar/README.md",
                 clone / "docs/SCALAR_MUL.md",
                 ROOT / "rtl/packed/SPEC.md", ROOT / "tests/packed/README.md",
                 ROOT / "isa/packed/SPEC.md", ROOT / "tests/packed_integration/README.md",
                 clone / "docs/PACKED_INTEGRATION.md",
                 *sorted((ROOT / "docs").glob("*.md"))]
    for document in documents:
        for target in re.findall(r"\]\((?!https?://)([^)#]+)(?:#[^)]*)?\)", document.read_text()):
            assert (document.parent / target).exists(), f"Broken link: {document}: {target}"
    schema = json.loads((ROOT / "results/schema.json").read_text())
    assert schema["type"] == "object"
    assert "status" in schema["required"]
    print("OK: snapshot identity, historical metadata and pinned audit evidence.")
    print("OK: three control probes, five documented differences, eight probes total.")
    print("OK: corrected-core evidence, full input hashes and upstream identity.")
    print("OK: bilingual equations/citations, LaTeX inputs, local links and experiment schema.")
    print("This check verifies recorded evidence; it does not rerun simulation or certify ISA conformance.")


if __name__ == "__main__":
    main()
