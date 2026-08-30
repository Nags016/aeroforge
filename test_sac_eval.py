from stable_baselines3 import SAC
from train_ultimate import create_vec_env
import numpy as np

# Test SAC best model
print('Testing SAC best model...')
model = SAC.load('/home/mr_nags/aeroforge/models/best/best_model.zip')
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
        # info is a list in vectorized environments
        if isinstance(info, list):
            info = info[0]
        if hasattr(env, 'collisions') and env.collisions == 0 and info.get('goal_distance', 100) < 1.0:
            successes += 1

print(f'SAC: {successes}/{total} = {successes/total:.0%} success rate')