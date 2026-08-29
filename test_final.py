#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
Final AeroForge Test Suite - Run before submission
"""

import subprocess
import sys
import json
import os

def run_test(name, cmd, check_output=None):
    """Run a test and report result."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"CMD:  {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(f"✅ PASS")
        if check_output and check_output not in result.stdout:
            print(f"⚠️  WARNING: Expected output '{check_output}' not found")
        return True
    else:
        print(f"❌ FAIL (exit code: {result.returncode})")
        print(f"STDOUT: {result.stdout[:500]}")
        print(f"STDERR: {result.stderr[:500]}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AEROFORGE PRE-SUBMISSION TEST SUITE                        ║
║         Google All Things Agentic Hackathon 2026 - Final Check                ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        ("Unit Tests", 
         "/home/mr_nags/miniconda3/envs/aeroforge/bin/python -m pytest /home/mr_nags/aeroforge/tests/ -v",
         "passed"),
        
        ("CLI Help", 
         "/home/mr_nags/.local/bin/aeroforge --help",
         "Agentic Flight Engineer"),
        
        ("Simple Mission", 
         '/home/mr_nags/.local/bin/aeroforge "Fly from (0,0,2) to (10,10,2) avoiding obstacles"',
         "Mission Complete"),
        
        ("Complex Mission", 
         '/home/mr_nags/.local/bin/aeroforge "Fly from (0,0,2) to (20,15,3) using camera and depth"',
         "Mission Complete"),
        
        ("Ambiguous Mission", 
         '/home/mr_nags/.local/bin/aeroforge "Go to target"',
         "Clarifying Questions"),
        
        ("Visualization Demo", 
         "/home/mr_nags/miniconda3/envs/aeroforge/bin/python /home/mr_nags/aeroforge/terminal_sim.py",
         "Simulation complete"),
        
        ("Experiment Records", 
         "ls /home/mr_nags/aeroforge/experiments/results/",
         "mission_"),
        
        ("Training Checkpoints", 
         "ls /home/mr_nags/aeroforge/models/checkpoints/",
         "ppo_drone"),
        
        ("Best Model", 
         "ls /home/mr_nags/aeroforge/models/best/",
         "best_model"),
        
        ("Project Structure", 
         "find /home/mr_nags/aeroforge -maxdepth 3 -type f -name '*.py' | head -20",
         "agent"),
    ]
    
    results = []
    for name, cmd, check in tests:
        try:
            passed = run_test(name, cmd, check)
            results.append((name, passed))
        except subprocess.TimeoutExpired:
            print(f"⏱️  TIMEOUT")
            results.append((name, False))
        except Exception as e:
            print(f"💥 ERROR: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - READY FOR SUBMISSION!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed - review before submission")
        return 1

if __name__ == "__main__":
    sys.exit(main())