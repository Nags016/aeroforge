#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
AeroForge Hackathon Demo Video Script
Record this sequence for submission video
"""

import subprocess
import time
import os

def run_cmd(cmd, description):
    """Run a command and show it for the demo."""
    print(f"\n{'='*70}")
    print(f"🎬 DEMO: {description}")
    print(f"$ {cmd}")
    print(f"{'='*70}\n")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"[stderr] {result.stderr}")
    return result

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AEROFORGE HACKATHON DEMO RECORDING                         ║
║         Google All Things Agentic Hackathon 2026 - Taskmaster                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    
This script records the key demo flows for the submission video.
Run each section and narrate as you go.
""")
    
    # Demo 1: CLI Help & Features
    run_cmd("aeroforge --help", "Show CLI help and features")
    time.sleep(2)
    
    # Demo 2: Simple Mission
    run_cmd('aeroforge "Fly from (0,0,2) to (10,10,2) avoiding obstacles"', 
            "Simple waypoint mission with obstacle avoidance")
    time.sleep(2)
    
    # Demo 3: Complex Mission
    run_cmd('aeroforge "Fly from (0,0,2) to (20,15,3) using camera and depth to avoid dynamic obstacles with 2.5m clearance, minimize energy and time"',
            "Complex mission with sensors, dynamic obstacles, multi-objective")
    time.sleep(2)
    
    # Demo 4: Ambiguous Mission (shows clarifying questions)
    run_cmd('aeroforge "Go to the target area"',
            "Ambiguous mission - triggers clarifying questions")
    time.sleep(2)
    
    # Demo 5: Interactive Mode
    print("\n🎬 DEMO: Interactive Mode (manual demo)")
    print("$ aeroforge --interactive")
    print("  (Show: type mission, see full pipeline, run another, exit)")
    time.sleep(3)
    
    # Demo 6: Terminal Visualization
    run_cmd("timeout 10 python terminal_sim.py", 
            "Terminal-based flight visualization (ASCII/ANSI)")
    time.sleep(2)
    
    # Demo 7: Show RL Training
    print("\n🎬 DEMO: RL Training in Progress")
    print("$ python train_rl.py --algorithm ppo --timesteps 1000000")
    print("  (Show TensorBoard: tensorboard --logdir logs/tensorboard)")
    print("  (Show checkpoints in models/checkpoints/)")
    time.sleep(2)
    
    # Demo 8: Show Experiment Results
    run_cmd("ls -la experiments/results/", "Show experiment records")
    time.sleep(1)
    
    run_cmd("cat experiments/results/mission_mission_001_full.json | head -50",
            "Show full experiment JSON record")
    time.sleep(2)
    
    # Demo 9: Code Structure
    run_cmd("tree -L 3 -I '__pycache__|*.pyc|.venv|.git|logs|models' /home/mr_nags/aeroforge",
            "Show project structure")
    time.sleep(2)
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        DEMO COMPLETE                                          ║
║                                                                              ║
║  Key talking points for video:                                               ║
║  1. "Natural language in, validated flight policy out"                      ║
║  2. "5 specialized agents, not a chatbot"                                    ║
║  3. "Classical + RL hybrid strategies"                                       ║
║  4. "Iterative experiment cycle with bounded mutations"                     ║
║  5. "Independent safety verification"                                        ║
║  6. "Crash recovery: .ulg → log-analyser.app → auto-fix"                    ║
║  7. "Beautiful terminal UX like Hermes/Kiro/Codex"                          ║
║  8. "Works offline with mock sim, scales to real Gazebo/PX4"                ║
║  9. "RL training on consumer GPU (GTX 1650)"                                ║
║  10. "Google Cloud ready: ADK, Firestore, Cloud Storage scaffolded"         ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    main()