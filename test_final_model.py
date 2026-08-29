#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
Test the final trained PPO policy (1M steps)
"""

import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')

from stable_baselines3 import PPO
from train_rl import make_env
import numpy as np

# Load final model (1M steps)
model = PPO.load("/home/mr_nags/aeroforge/models/ppo_drone_final.zip")
print("✅ Loaded final model (1M steps)")

# Create eval env
config = {
    'max_steps': 500,
    'world_size': 50.0,
    'num_obstacles': 10,
    'goal_threshold': 1.0,
    'collision_penalty': -50.0,
    'goal_reward': 100.0,
    'time_penalty': -0.1,
    'clearance_reward': 2.0,
    'clearance_threshold': 2.0,
    'action_smoothness_weight': -0.01,
}

eval_env = make_env(config)()

# Run evaluation
n_episodes = 20
successes = 0
collisions = 0
goal_errors = []
clearances = []
path_lengths = []
flight_times = []
rewards = []

for ep in range(n_episodes):
    obs, _ = eval_env.reset()
    done = False
    ep_reward = 0
    ep_collisions = 0
    ep_min_clearance = float('inf')
    ep_path_length = 0.0
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        done = terminated or truncated
        ep_reward += reward
        
        if hasattr(eval_env, 'collisions'):
            ep_collisions = eval_env.collisions
        if hasattr(eval_env, 'min_clearance'):
            ep_min_clearance = min(ep_min_clearance, eval_env.min_clearance)
        if hasattr(eval_env, 'path_length'):
            ep_path_length = eval_env.path_length
            
    if ep_collisions == 0 and info.get('goal_distance', 100) < 1.0:
        successes += 1
    collisions += ep_collisions
    goal_errors.append(info.get('goal_distance', 0))
    clearances.append(ep_min_clearance if ep_min_clearance != float('inf') else 0)
    path_lengths.append(ep_path_length)
    flight_times.append(info.get('step', 0) * 0.1)
    rewards.append(ep_reward)

print(f"\n📊 Final Model Evaluation ({n_episodes} episodes):")
print(f"  Success Rate: {successes/n_episodes:.0%} ({successes}/{n_episodes})")
print(f"  Avg Collisions: {collisions/n_episodes:.2f}")
print(f"  Avg Goal Error: {np.mean(goal_errors):.2f}m (±{np.std(goal_errors):.2f})")
print(f"  Min Clearance: {np.min(clearances):.2f}m")
print(f"  Mean Clearance: {np.mean(clearances):.2f}m (±{np.std(clearances):.2f})")
print(f"  Avg Path Length: {np.mean(path_lengths):.2f}m")
print(f"  Avg Flight Time: {np.mean(flight_times):.2f}s")
print(f"  Avg Episode Reward: {np.mean(rewards):.2f}")
print(f"  Best Episode Reward: {np.max(rewards):.2f}")

# Check if model is ready
if successes/n_episodes >= 0.5:
    print(f"\n✅ MODEL READY FOR DEPLOYMENT (Success rate >= 50%)")
else:
    print(f"\n⚠️  Model needs more training (Success rate < 50%)")