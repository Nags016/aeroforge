import torch
print('CUDA:', torch.cuda.is_available())
import stable_baselines3
print('SB3 OK')
import gymnasium
print('Gym OK')