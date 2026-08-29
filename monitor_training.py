#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
Monitor RL training progress
"""

import time
import os
from pathlib import Path

def monitor_training():
    """Monitor both training processes."""
    print("🧠 Monitoring RL Training Progress")
    print("=" * 60)
    
    ppo_log = Path("/home/mr_nags/aeroforge/logs/tensorboard/PPO_2")
    sac_log = Path("/home/mr_nags/aeroforge/logs/tensorboard/SAC_1")
    checkpoints = Path("/home/mr_nags/aeroforge/models/checkpoints")
    best = Path("/home/mr_nags/aeroforge/models/best")
    
    while True:
        os.system('clear')
        print("🧠 RL TRAINING MONITOR")
        print("=" * 60)
        print(f"Time: {time.strftime('%H:%M:%S')}")
        print()
        
        # Check checkpoints
        if checkpoints.exists():
            ckpts = sorted(checkpoints.glob("*.zip"))
            if ckpts:
                latest = ckpts[-1]
                size_mb = latest.stat().st_size / 1024 / 1024
                print(f"📦 Checkpoints: {len(ckpts)} | Latest: {latest.name} ({size_mb:.1f} MB)")
        
        # Check best models
        if best.exists():
            best_models = list(best.glob("*.zip"))
            if best_models:
                for bm in best_models:
                    size_mb = bm.stat().st_size / 1024 / 1024
                    mtime = time.strftime('%H:%M:%S', time.localtime(bm.stat().st_mtime))
                    print(f"⭐ Best model: {bm.name} ({size_mb:.1f} MB, updated {mtime})")
        
        # TensorBoard hint
        print()
        print("📊 View TensorBoard:")
        print("   tensorboard --logdir /home/mr_nags/aeroforge/logs/tensorboard")
        
        print()
        print("Press Ctrl+C to stop monitoring (training continues in background)")
        time.sleep(30)

if __name__ == "__main__":
    try:
        monitor_training()
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped. Training continues in background.")