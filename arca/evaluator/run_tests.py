"""The verification core: clone a repo at a given ref and run its test suite in a
sandbox. Returns (passed: bool, log: str). This is the 'oracle' — objective,
machine-checkable acceptance. For code bounties, the tests ARE the acceptance
criteria: green => release.

Kept deliberately simple and dependency-free (uses git + subprocess). In
production you'd run this in an isolated container with no secrets and a time/CPU
budget.
"""
import subprocess
import tempfile
from pathlib import Path


def run(repo_url: str, ref: str, test_cmd: str, timeout: int = 300):
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "work"
        log = []

        def sh(cmd, **kw):
            log.append("$ " + " ".join(cmd))
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, **kw)
            log.append(p.stdout[-4000:])
            log.append(p.stderr[-2000:])
            return p.returncode

        if sh(["git", "clone", "--depth", "50", repo_url, str(d)]) != 0:
            return False, "\n".join(log) + "\nclone failed"
        if ref and sh(["git", "-C", str(d), "checkout", ref]) != 0:
            return False, "\n".join(log) + "\ncheckout failed"

        code = sh(test_cmd.split(), cwd=str(d))
        passed = code == 0
        log.append(f"\n== test command exit code: {code} -> {'PASS' if passed else 'FAIL'} ==")
        return passed, "\n".join(log)


if __name__ == "__main__":
    import sys
    ok, out = run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "HEAD",
                  sys.argv[3] if len(sys.argv) > 3 else "pytest -q")
    print(out)
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
