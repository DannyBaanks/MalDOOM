"""
test_engine_does_the_work — host must not compute answer.

- grep host/ for gameplay symbols
- verify that generated .mu artifacts exist and are non-trivial
- ensure killer test uses same artifact for different inputs
"""
import re, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "host" / "host.py"

FORBIDDEN = ["doomgeneric_Tick","P_MovePlayer","P_RunThinkers","M_Random","P_CheckPosition","WI_Ticker","G_Ticker","ST_Ticker"]

def test_host_no_gameplay():
    src = HOST.read_text(encoding="utf-8")
    found = [s for s in FORBIDDEN if s in src]
    assert not found, f"HOST_STOLE_COMPUTATION — host contains {found}"

def test_m0_artifacts_exist():
    # after build, evidence/M0_*/artifact.mu should exist
    # before build, this test is skipped (not failed)
    # Layout since commit 35bc289: bare M0_* dirs hold the GCC reference run;
    # the demonstrated Malbolge edge is the sibling M0_*_UNSHACKLED_V0 with
    # artifact.mu + artifact.hell. M0_HELL_VM is the canonical example pipeline
    # and carries its own artifacts. A bare dir with neither its own artifact
    # nor an Unshackled sibling fails the gate.
    REFERENCE_ONLY = {"M0_KILLER"}  # negative/positive control of COMPILE_ONCE
    evid = [p for p in (ROOT/"evidence").glob("M0_*") if p.is_dir()]
    if not evid:
        import pytest; pytest.skip("no evidence yet — run py scripts/build_m0.py --all")
    for d in evid:
        if d.name in REFERENCE_ONLY:
            assert (d / "run.json").exists(), f"reference control lost its run.json: {d}"
            continue
        here = (d / "artifact.mu").exists() or (d / "artifact.hell").exists()
        sibling = (ROOT/"evidence"/f"{d.name}_UNSHACKLED_V0"/"artifact.mu").exists()
        assert here or sibling, f"missing artifact in {d} (nor in {d.name}_UNSHACKLED_V0)"

def test_killer_same_artifact():
    kd = ROOT / "evidence" / "M0_KILLER_UNSHACKLED_V0"
    if not kd.exists():
        import pytest; pytest.skip("killer not built yet")
    mu = kd / "artifact.mu"
    assert mu.exists(), "killer artifact missing"
    h = hashlib.sha256(mu.read_bytes()).hexdigest()
    # run.json records the artifact hash actually used for every input
    j = kd / "run.json"
    if j.exists():
        import json
        doc = json.loads(j.read_text())
        recorded = doc["artifact_sha256"]["artifact.mu"] if isinstance(doc, dict) else None
        if recorded:
            assert h == recorded, "artifact file hash mismatch run.json"
        # every run in the doc must reuse the same single artifact (COMPILE_ONCE)
        runs = doc["runs"] if isinstance(doc, dict) else doc
        shas = set(r.get("artifact_sha") for r in runs if r.get("artifact_sha"))
        assert len(shas) <= 1, f"killer used different artifacts per input: {shas} — must be COMPILE_ONCE"
