#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
Test loading and evaluating the trained RL policy
"""

import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')

from stable_baselines3 import PPO
from train_rl import make_env

# Load best model
model = PPO.load("/home/mr_nags/aeroforge/models/best/best_model.zip")
print("✅ Loaded best model")

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
n_episodes = 10
successes = 0
collisions = 0
goal_errors = []
clearances = []
path_lengths = []
flight_times = []

for ep in range(n_episodes):
    obs, _ = eval_env.reset()
    done = False
    ep_collisions = 0
    ep_min_clearance = float('inf')
    ep_path_length = 0.0
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        done = terminated or truncated
        
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

print(f"\n📊 Evaluation Results ({n_episodes} episodes):")
print(f"  Success Rate: {successes/n_episodes:.0%}")
print(f"  Avg Collisions: {collisions/n_episodes:.2f}")
print(f"  Avg Goal Error: {sum(goal_errors)/len(goal_errors):.2f}m")
print(f"  Min Clearance: {min(clearances):.2f}m")
print(f"  Mean Clearance: {sum(clearances)/len(clearances):.2f}m")
print(f"  Avg Path Length: {sum(path_lengths)/len(path_lengths):.2f}m")
print(f"  Avg Flight Time: {sum(flight_times)/len(flight_times):.2f}s")