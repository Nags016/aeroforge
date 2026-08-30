from stable_baselines3 import SAC, PPO
from train_ultimate import create_vec_env
import numpy as np

def evaluate_model(model_path, algorithm, n_episodes=20):
    print(f'Testing {algorithm} model: {model_path}')
    if algorithm.upper() == "SAC":
        model = SAC.load(model_path)
    else:
        model = PPO.load(model_path)
    
    eval_env = create_vec_env(n_envs=1, curriculum_level=4, normalize=True, add_monitor=False)
    
    successes = 0
    total = 20
    for ep in range(total):
        result = eval_env.reset()
        if isinstance(result, tuple):
            obs = result[0]
        else:
            obs = result
        done = False
        info = {}
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            result = eval_env.step(action)
            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
            else:
                obs, reward, done, info = result
                terminated = done
                truncated = False
            done = terminated or truncated
        if hasattr(eval_env, 'envs'):
            env = eval_env.envs[0]
            while hasattr(env, 'env'):
                env = env.env
            if isinstance(info, list):
                info = info[0]
            if hasattr(env, 'collisions') and env.collisions == 0 and info.get('goal_distance', 100) < 1.0:
                successes += 1
    
    print(f'{algorithm}: {successes}/{total} = {successes/total:.0%} success rate')
    return successes/total

# Test multiple checkpoints
print("=" * 50)
print("EVALUATING CHECKPOINTS")
print("=" * 50)

# Test SAC checkpoints
for path in [
    "/home/mr_nags/aeroforge/models/checkpoints/sac_drone_50000_steps.zip",
    "/home/mr_nags/aeroforge/models/checkpoints/sac_drone_100000_steps.zip",
    "/home/mr_nags/aeroforge/models/checkpoints/sac_drone_400000_steps.zip",
]:
    try:
        evaluate_model(path, "SAC", 20)
    except Exception as e:
        print(f"Error evaluating {path}: {e}")

# Test PPO checkpoints
for path in [
    "/home/mr_nags/aeroforge/models/checkpoints/ppo_drone_200000_steps.zip",
    "/home/mr_nags/aeroforge/models/checkpoints/ppo_drone_400000_steps.zip",
    "/home/mr_nags/aeroforge/models/checkpoints/ppo_drone_800000_steps.zip",
    "/home/mr_nags/aeroforge/models/checkpoints/ppo_drone_1600000_steps.zip",
]:
    try:
        evaluate_model(path, "PPO", 20)
    except Exception as e:
        print(f"Error evaluating {path}: {e}")

# Test best model
print("\nTesting best model:")
evaluate_model("/home/mr_nags/aeroforge/models/best/best_model.zip", "SAC", 20)