#!/usr/bin/env python3
"""
REACT-X Final Release & Production Deployment Verification Engine
=================================================================
Automates end-to-end operational verification across all production domains:
  1. Production Configuration & Environment Boundary
  2. Backup & Restore Data Fidelity Verification
  3. 90-Day Retention & Provenance Preservation Verification
  4. Declarative Zero-Code Facility Onboarding (Paradip Complex)
  5. Multi-Facility High-Intensity Soak & Memory Stability
  6. Service Chaos, Outage & Database Recovery
  7. Non-Invasive Industrial Read-Only Safety Boundary (No PLC/DCS/SIS Writes)
  8. Full Backend Core Test Suite Passing

Produces a definitive PASS / FAIL release verdict with empirical metrics.
"""

import sys
import time
import subprocess
import json
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

class ReleaseVerifier:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def run_check(self, name: str, cmd: list, cwd: Path = BACKEND_DIR) -> bool:
        print(f"\n========================================================")
        print(f"[RELEASE CHECK] Running: {name}...")
        print(f"Command: {' '.join(cmd)}")
        print(f"========================================================")
        t0 = time.perf_counter()
        try:
            res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=180)
            elapsed = time.perf_counter() - t0
            passed = (res.returncode == 0)
            
            output_lines = [line for line in (res.stdout + res.stderr).splitlines() if line.strip()]
            preview = "\n".join(output_lines[-10:]) if output_lines else "No output"
            
            if passed:
                print(f"--> [PASS] {name} ({elapsed:.2f}s)")
            else:
                print(f"--> [FAIL] {name} ({elapsed:.2f}s)")
                print(f"Error details:\n{preview}")
                
            self.results.append({
                "check": name,
                "passed": passed,
                "duration_sec": round(elapsed, 2),
                "output_preview": preview
            })
            return passed
        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - t0
            print(f"--> [FAIL] {name} (TIMEOUT after {elapsed:.2f}s)")
            self.results.append({
                "check": name,
                "passed": False,
                "duration_sec": round(elapsed, 2),
                "output_preview": "Command timed out after 180 seconds"
            })
            return False
        except Exception as ex:
            elapsed = time.perf_counter() - t0
            print(f"--> [FAIL] {name} ({ex})")
            self.results.append({
                "check": name,
                "passed": False,
                "duration_sec": round(elapsed, 2),
                "output_preview": str(ex)
            })
            return False

    def summarize(self) -> bool:
        total_time = time.time() - self.start_time
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r["passed"])
        failed_checks = total_checks - passed_checks
        all_passed = (failed_checks == 0)

        print("\n" + "=" * 70)
        print("REACT-X FINAL PRODUCTION RELEASE VERIFICATION REPORT")
        print("=" * 70)
        for r in self.results:
            status_str = "[ PASS ]" if r["passed"] else "[ FAIL ]"
            print(f"{status_str} {r['check']:<50} ({r['duration_sec']}s)")

        print("-" * 70)
        print(f"Total Verifications: {total_checks} | Passed: {passed_checks} | Failed: {failed_checks}")
        print(f"Total Verification Time: {total_time:.2f}s")
        print("=" * 70)

        if all_passed:
            print("\n>>> FINAL VERDICT: PASS — READY FOR PRODUCTION DEPLOYMENT <<<\n")
        else:
            print("\n>>> FINAL VERDICT: FAIL — PRODUCTION BLOCKERS DETECTED <<<\n")

        return all_passed

def main():
    verifier = ReleaseVerifier()

    # 1. Security & Safety Boundary Sweep
    verifier.run_check(
        "Security & Read-Only Industrial Safety Boundary",
        [sys.executable, "-m", "pytest", "test_production_security_sweep.py", "-q"]
    )

    # 2. Database Backup & Restore Cycle
    verifier.run_check(
        "Automated Backup & Restore Fidelity",
        [sys.executable, "-m", "pytest", "test_production_backup_restore.py", "-q"]
    )

    # 3. 90-Day Retention & Provenance Preservation
    verifier.run_check(
        "90-Day Storage Retention & Provenance Preservation",
        [sys.executable, "-m", "pytest", "test_production_retention.py", "-q"]
    )

    # 4. Declarative Zero-Code Facility Onboarding
    verifier.run_check(
        "Declarative Facility Onboarding (Paradip Hub)",
        [sys.executable, "-m", "pytest", "test_facility_onboarding.py", "-q"]
    )

    # 5. Service Recovery & Database Chaos Recovery
    verifier.run_check(
        "Database & Outage Service Recovery",
        [sys.executable, "-m", "pytest", "test_production_service_recovery.py", "-q"]
    )

    # 6. Multi-Facility High-Intensity Soak Test
    verifier.run_check(
        "Multi-Facility Multimodal Soak Test",
        [sys.executable, "-m", "pytest", "test_production_soak.py", "-q"]
    )

    # 7. Core Backend Integration Test Suite
    verifier.run_check(
        "Core Backend Integration Test Suite",
        [sys.executable, "-m", "pytest", "test_backend.py", "-q"]
    )

    success = verifier.summarize()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
