from stable_baselines3 import PPO
from train_rl import make_env
import numpy as np

# Test with fixed seed for reproducibility
config = {
    'max_steps': 500,
    'world_size': 50.0,
    'num_obstacles': 5,  # Fewer obstacles
    'goal_threshold': 2.0,  # Larger goal radius
    'collision_penalty': -50.0,
    'goal_reward': 100.0,
    'time_penalty': -0.1,
    'clearance_reward': 2.0,
    'clearance_threshold': 2.0,
    'action_smoothness_weight': -0.01,
}

model = PPO.load('/home/mr_nags/aeroforge/models/ppo_drone_final.zip')
eval_env = make_env(config)()

# Run a few episodes with fixed seed
np.random.seed(42)
successes = 0
for ep in range(10):
    obs, _ = eval_env.reset(seed=42+ep)
    done = False
    ep_info = {}
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        done = terminated or truncated
        ep_info = info
    collisions = ep_info.get('collisions', 0)
    goal_dist = ep_info.get('goal_distance', 100)
    clearance = ep_info.get('clearance', 0)
    steps = ep_info.get('step', 0)
    if collisions == 0 and goal_dist < 2.0:
        successes += 1
    print(f'Episode {ep}: dist={goal_dist:.1f}m, collisions={collisions}, clearance={clearance:.1f}m, steps={steps}')

print(f'Success rate: {successes}/10')