from train_rl import DroneEnv, make_env
import numpy as np

# Test environment
config = {
    'max_steps': 100,
    'num_obstacles': 5,
}
env = DroneEnv(config)
obs, info = env.reset()
print(f"Observation shape: {obs.shape}")
print(f"Action space: {env.action_space}")
print(f"Observation space: {env.observation_space}")

# Run a few random steps
total_reward = 0
for i in range(20):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    total_reward += reward
    if terminated or truncated:
        print(f"Episode ended at step {i}: terminated={terminated}, truncated={truncated}")
        break
    if i % 5 == 0:
        print(f"Step {i}: pos={env.position}, reward={reward:.2f}, dist={info['goal_distance']:.2f}")

print(f"Total reward: {total_reward:.2f}")
print("Environment test passed!")