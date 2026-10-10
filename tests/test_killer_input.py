"""
test_killer_input — runtime-unknown input test.

The killer program reads n, computes deterministic result, outputs it.
Host only delivers n. Same .mu must give correct output for different n
without recompilation.

This test is the gate for RUNTIME_STATEFUL_EXECUTION_DEMONSTRATED.
"""
import subprocess, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def run_mu(mu: Path, inp: str, vm: Path):
    # vm is Unshackled binary or python wrapper; we try both
    if not vm.exists():
        import pytest; pytest.skip(f"VM not built: {vm}")
    # try C binary first
    cmd = [str(vm), str(mu)]
    r = subprocess.run(cmd, input=inp.encode(), capture_output=True, timeout=10)
    return r.stdout, r.stderr, r.returncode

def test_killer():
    # The COMPILE_ONCE artifact lives in M0_KILLER_UNSHACKLED_V0 (EIR->HeLL->mu).
    # evidence/M0_KILLER is the GCC reference/negative control: source.c +
    # observed bins, no .mu by design.
    kd = ROOT / "evidence" / "M0_KILLER_UNSHACKLED_V0"
    if not kd.exists():
        import pytest; pytest.skip("killer not built")
    mu = kd / "artifact.mu"
    vm = ROOT / "vendor" / "Unshackled"
    if not vm.exists():
        import pytest; pytest.skip(f"VM not built: {vm}")
    runj = kd / "run.json"
    if runj.exists():
        doc = json.loads(runj.read_text())
        runs = doc["runs"] if isinstance(doc, dict) else doc
        for r in runs:
            inp = r["input"]; expected = r["expected"]
            # re-run to verify host didn't hardcode
            out, err, code = run_mu(mu, inp, vm)
        # expected is ASCII string in run.json; compare after trimming the
        # trailing newline both sides (Unshackled emits \n; Windows observed \r\n)
        out_s = out.decode(errors="replace").strip()
        assert out_s == expected.strip(), f"input={inp!r} expected={expected!r} got={out_s!r} (host may have stolen computation)"
    else:
        import pytest; pytest.skip("no run.json")
