#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
AeroForge Ultimate RL Training Pipeline - Optimized for 10-Hour Training
- SAC primary (continuous control) + PPO secondary
- Curriculum learning: 5 levels (hover → waypoint → static obs → dynamic obs → complex)
- Domain randomization for sim-to-real transfer
- Optimized hyperparameters for GTX 1650 4GB
- Checkpointing every 100K steps
- TensorBoard logging
"""

import os
import sys
import time
import json
import numpy as np
import torch
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import SAC, PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor, VecNormalize
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.noise import NormalActionNoise
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

sys.path.insert(0, '/home/mr_nags/aeroforge')

from agent.schemas import Vector3D, Obstacle


def make_env(curriculum_level: int = 0, seed: int = 42, domain_randomize: bool = True, config: dict = None):
    """Create environment factory."""
    def _init():
        env = CurriculumDroneEnv(
            curriculum_level=curriculum_level,
            seed=seed,
            domain_randomize=domain_randomize
        )
        env = Monitor(env)
        return env
    return _init


class CurriculumDroneEnv(gym.Env):
    """Drone environment with curriculum learning and domain randomization."""
    
    def __init__(self, curriculum_level: int = 0, seed: int = 42, domain_randomize: bool = True):
        super().__init__()
        np.random.seed(seed)
        torch.manual_seed(seed)
        
        self.curriculum_level = curriculum_level
        self.domain_randomize = domain_randomize
        self.max_steps = 500
        self.step_count = 0
        
        # Base config - will be modified by curriculum
        self._base_config = {
            'world_size': 50.0,
            'num_obstacles': 0,
            'obstacle_radius_range': [0.5, 3.0],
            'dynamic_obstacle_ratio': 0.0,
            'goal_threshold': 1.0,
            'max_velocity': 10.0,
            'max_acceleration': 5.0,
            'dt': 0.1,
            'wind_strength': 0.0,
            'sensor_noise': 0.0,
        }
        
        # Apply curriculum
        self.config = self._apply_curriculum(self._base_config.copy())
        
        # Observation space: 37 dims
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(37,), dtype=np.float32
        )
        
        # Action space: 3D velocity command [-1, 1]
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(3,), dtype=np.float32
        )
        
        self.reset()
    
    def _apply_curriculum(self, config: Dict) -> Dict:
        """Apply curriculum level modifications."""
        levels = [
            # Level 0: Hover
            {'num_obstacles': 0, 'goal_threshold': 1.5, 'wind_strength': 0.0, 'sensor_noise': 0.0},
            # Level 1: Simple waypoint
            {'num_obstacles': 0, 'goal_threshold': 1.0, 'wind_strength': 0.0, 'sensor_noise': 0.01},
            # Level 2: Static obstacles
            {'num_obstacles': 5, 'obstacle_radius_range': [1.0, 2.0], 'dynamic_obstacle_ratio': 0.0, 'goal_threshold': 1.0, 'wind_strength': 0.1, 'sensor_noise': 0.02},
            # Level 3: Dynamic obstacles
            {'num_obstacles': 8, 'obstacle_radius_range': [0.5, 3.0], 'dynamic_obstacle_ratio': 0.3, 'goal_threshold': 0.8, 'wind_strength': 0.2, 'sensor_noise': 0.03},
            # Level 4: Complex environment
            {'num_obstacles': 12, 'obstacle_radius_range': [0.5, 3.5], 'dynamic_obstacle_ratio': 0.5, 'goal_threshold': 0.5, 'wind_strength': 0.3, 'sensor_noise': 0.05},
        ]
        
        if self.curriculum_level < len(levels):
            config.update(levels[self.curriculum_level])
        
        # Domain randomization
        if self.domain_randomize:
            config['world_size'] *= np.random.uniform(0.8, 1.2)
            config['max_velocity'] *= np.random.uniform(0.8, 1.2)
            config['max_acceleration'] *= np.random.uniform(0.8, 1.2)
            config['wind_strength'] *= np.random.uniform(0.5, 1.5)
            config['sensor_noise'] *= np.random.uniform(0.5, 1.5)
        
        return config
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Randomize config on each reset if domain randomization enabled
        if self.domain_randomize:
            self.config = self._apply_curriculum(self._base_config.copy())
        
        # Random start position
        self.start_pos = np.array([
            np.random.uniform(-self.config['world_size']/4, self.config['world_size']/4),
            np.random.uniform(-self.config['world_size']/4, self.config['world_size']/4),
            np.random.uniform(1.0, 5.0)
        ], dtype=np.float32)
        
        # Random goal position (ensure minimum distance)
        for _ in range(100):
            self.goal_pos = np.array([
                np.random.uniform(-self.config['world_size']/2, self.config['world_size']/2),
                np.random.uniform(-self.config['world_size']/2, self.config['world_size']/2),
                np.random.uniform(1.0, 10.0)
            ], dtype=np.float32)
            if np.linalg.norm(self.goal_pos - self.start_pos) > 5.0:
                break
        
        # Generate obstacles
        self.obstacles = []
        for _ in range(self.config['num_obstacles']):
            is_dynamic = np.random.random() < self.config['dynamic_obstacle_ratio']
            obs = Obstacle(
                position=Vector3D(
                    x=np.random.uniform(-self.config['world_size']/2, self.config['world_size']/2),
                    y=np.random.uniform(-self.config['world_size']/2, self.config['world_size']/2),
                    z=np.random.uniform(0.5, 10.0)
                ),
                radius=np.random.uniform(*self.config['obstacle_radius_range']),
                height=5.0,
                velocity=Vector3D(
                    x=np.random.uniform(-2, 2) if is_dynamic else 0,
                    y=np.random.uniform(-2, 2) if is_dynamic else 0,
                    z=0
                ) if is_dynamic else None,
                obstacle_type="dynamic" if is_dynamic else "static"
            )
            # Ensure not on start/goal
            if (np.linalg.norm([obs.position.x - self.start_pos[0], obs.position.y - self.start_pos[1]]) > 3.0 and
                np.linalg.norm([obs.position.x - self.goal_pos[0], obs.position.y - self.goal_pos[1]]) > 3.0):
                self.obstacles.append(obs)
        
        self.position = self.start_pos.copy()
        self.velocity = np.zeros(3, dtype=np.float32)
        self.prev_action = np.zeros(3, dtype=np.float32)
        self.step_count = 0
        self.total_reward = 0.0
        self.collisions = 0
        self.min_clearance = float('inf')
        self.path_length = 0.0
        self.prev_pos = self.start_pos.copy()
        
        return self._get_obs(), {}
    
    def _get_obs(self):
        """37-dimensional observation."""
        # Position (3)
        pos = self.position
        
        # Velocity (3)
        vel = self.velocity
        
        # Quaternion (4) - simplified
        quat = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        
        # Goal relative (3)
        goal_rel = self.goal_pos - self.position
        
        # 16-ray depth (16)
        depth_rays = self._simulate_depth_rays()
        
        # Previous action (3)
        prev_act = self.prev_action
        
        # Time left (1)
        time_left = 1.0 - (self.step_count / self.max_steps)
        
        # Obstacle info (4): nearest_dist, nearest_angle, count, dynamic_ratio
        nearest_dist, nearest_angle = self._get_nearest_obstacle_info()
        dynamic_count = sum(1 for o in self.obstacles if o.obstacle_type == "dynamic")
        obstacle_info = np.array([
            nearest_dist / self.config['world_size'],
            nearest_angle / np.pi,
            len(self.obstacles) / 20.0,
            dynamic_count / max(1, len(self.obstacles))
        ], dtype=np.float32)
        
        obs = np.concatenate([
            pos, vel, quat, goal_rel, depth_rays, prev_act, 
            [time_left], obstacle_info
        ]).astype(np.float32)
        
        # Add sensor noise
        if self.config['sensor_noise'] > 0:
            noise = np.random.normal(0, self.config['sensor_noise'], obs.shape).astype(np.float32)
            obs = np.clip(obs + noise, -10.0, 10.0)
        
        return np.nan_to_num(obs, nan=0.0, posinf=10.0, neginf=-10.0)
    
    def _simulate_depth_rays(self, num_rays: int = 16) -> np.ndarray:
        """Simulate 16-ray depth sensor."""
        rays = np.ones(num_rays, dtype=np.float32) * 50.0
        
        for i in range(num_rays):
            angle = 2 * np.pi * i / num_rays
            ray_dir = np.array([np.cos(angle), np.sin(angle), 0.0])
            
            for obs in self.obstacles:
                oc = np.array([self.position[0] - obs.position.x, 
                              self.position[1] - obs.position.y])
                ray_2d = ray_dir[:2]
                
                a = np.dot(ray_2d, ray_2d)
                b = 2 * np.dot(oc, ray_2d)
                c = np.dot(oc, oc) - obs.radius**2
                
                disc = b*b - 4*a*c
                if disc > 1e-6:  # Only intersect if disc is significantly positive
                    t = (-b - np.sqrt(disc)) / (2*a)
                    if t > 0 and t < rays[i]:
                        rays[i] = t
                        
        return np.clip(rays / 50.0, 0.0, 1.0)
    
    def _get_nearest_obstacle_info(self):
        min_dist = float('inf')
        min_angle = 0.0
        
        for obs in self.obstacles:
            dx = obs.position.x - self.position[0]
            dy = obs.position.y - self.position[1]
            dist = np.hypot(dx, dy) - obs.radius
            if dist < min_dist:
                min_dist = dist
                min_angle = np.arctan2(dy, dx)
                
        return min_dist if min_dist != float('inf') else 50.0, min_angle
    
    def _check_collision(self) -> bool:
        for obs in self.obstacles:
            dx = self.position[0] - obs.position.x
            dy = self.position[1] - obs.position.y
            dz = self.position[2] - obs.position.z
            dist_xy = np.hypot(dx, dy)
            if dist_xy < obs.radius and abs(dz) < obs.height / 2:
                return True
        return False
    
    def _get_clearance(self) -> float:
        min_clear = float('inf')
        for obs in self.obstacles:
            dx = self.position[0] - obs.position.x
            dy = self.position[1] - obs.position.y
            dist = np.hypot(dx, dy) - obs.radius
            min_clear = min(min_clear, dist)
        return max(0, min_clear)
    
    def step(self, action):
        # Clip action
        action = np.clip(action, -1.0, 1.0)
        
        # Convert to velocity command
        target_vel = action * self.config['max_velocity']
        
        # Apply wind disturbance
        if self.config['wind_strength'] > 0:
            wind = np.random.normal(0, self.config['wind_strength'], 3)
        else:
            wind = np.zeros(3, dtype=np.float32)
        
        # Acceleration limiting
        accel = (target_vel - self.velocity) / self.config['dt'] + wind
        accel_norm = np.linalg.norm(accel)
        if accel_norm > self.config['max_acceleration']:
            accel = accel / accel_norm * self.config['max_acceleration']
        
        self.velocity = self.velocity + accel * self.config['dt']
        
        # Update position
        self.prev_pos = self.position.copy()
        self.position = self.position + self.velocity * self.config['dt']
        
        # Geofence
        self.position = np.clip(self.position, 
                               [-self.config['world_size']/2, -self.config['world_size']/2, 0.1],
                               [self.config['world_size']/2, self.config['world_size']/2, 20.0])
        
        self.path_length += np.linalg.norm(self.position - self.prev_pos)
        self.step_count += 1
        self.prev_action = action.copy()
        
        # Update dynamic obstacles
        for obs in self.obstacles:
            if obs.obstacle_type == "dynamic" and obs.velocity is not None:
                obs.position.x += obs.velocity.x * self.config['dt']
                obs.position.y += obs.velocity.y * self.config['dt']
                # Bounce off walls
                if abs(obs.position.x) > self.config['world_size']/2 - obs.radius:
                    obs.velocity.x *= -1
                    obs.position.x = np.clip(obs.position.x, 
                        -self.config['world_size']/2 + obs.radius, 
                        self.config['world_size']/2 - obs.radius)
                if abs(obs.position.y) > self.config['world_size']/2 - obs.radius:
                    obs.velocity.y *= -1
                    obs.position.y = np.clip(obs.position.y, 
                        -self.config['world_size']/2 + obs.radius, 
                        self.config['world_size']/2 - obs.radius)
                # Ensure velocity is finite
                obs.velocity.x = np.clip(obs.velocity.x, -10.0, 10.0)
                obs.velocity.y = np.clip(obs.velocity.y, -10.0, 10.0)
        
        # Compute reward
        reward = 0.0
        
        # Time penalty
        reward += -0.1
        
        # Goal distance reward (more shaped)
        goal_dist = np.linalg.norm(self.goal_pos - self.position)
        reward += -goal_dist * 0.1  # Reduced from 0.5 for better gradient
        
        # Clearance reward
        clearance = self._get_clearance()
        self.min_clearance = min(self.min_clearance, clearance)
        if clearance > 2.0:
            reward += 2.0 * (clearance - 2.0)
        else:
            reward += -10.0 * (2.0 - clearance)
        
        # Action smoothness
        action_diff = np.linalg.norm(action - self.prev_action)
        reward += -0.01 * action_diff
        
        # Velocity efficiency (penalize high velocity when not needed)
        reward += -0.01 * np.linalg.norm(self.velocity)
        
        # Progress toward goal reward
        prev_goal_dist = np.linalg.norm(self.goal_pos - self.prev_pos)
        progress = prev_goal_dist - goal_dist
        reward += progress * 10.0  # Reward moving toward goal
        
        # Clip reward to prevent NaN
        reward = np.clip(reward, -100.0, 100.0)
        
        # Check collision
        collided = self._check_collision()
        if collided:
            reward += -50.0
            self.collisions += 1
        
        # Check goal reached
        terminated = False
        if goal_dist < self.config['goal_threshold']:
            reward += 100.0
            terminated = True
        
        # Check max steps
        truncated = self.step_count >= self.max_steps
        
        self.total_reward += reward
        
        return self._get_obs(), reward, terminated, truncated, {
            'goal_distance': goal_dist,
            'clearance': clearance,
            'collisions': self.collisions,
            'step': self.step_count,
            'curriculum_level': self.curriculum_level,
        }
    
    def render(self):
        pass


def create_vec_env(n_envs: int = 4, curriculum_level: int = 0, normalize: bool = True, add_monitor: bool = True):
    """Create vectorized environment with normalization."""
    env_fns = [make_env(curriculum_level=curriculum_level, seed=42+i, domain_randomize=True, config={}) 
               for i in range(n_envs)]
    vec_env = DummyVecEnv(env_fns)
    if add_monitor:
        vec_env = VecMonitor(vec_env)
    if normalize:
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.)
    return vec_env


class CurriculumCallback(BaseCallback):
    """Automatically advance curriculum based on performance."""
    
    def __init__(self, vec_env, threshold: float = 0.8, min_episodes: int = 50, verbose: int = 0):
        super().__init__(verbose)
        self.vec_env = vec_env
        self.threshold = threshold
        self.min_episodes = min_episodes
        self.current_level = 0
        self.episode_rewards = []
        self.episodes_at_level = 0
        
    def _on_step(self) -> bool:
        if len(self.model.ep_info_buffer) > 0:
            ep_info = self.model.ep_info_buffer[-1]
            if 'r' in ep_info:
                self.episode_rewards.append(ep_info['r'])
                self.episodes_at_level += 1
                
                # Check if we should advance curriculum
                if (self.episodes_at_level >= self.min_episodes and 
                    self.current_level < 4):
                    
                    recent_rewards = self.episode_rewards[-self.min_episodes:]
                    success_rate = sum(1 for r in recent_rewards if r > 50) / len(recent_rewards)
                    
                    if success_rate >= self.threshold:
                        self.current_level += 1
                        self.episodes_at_level = 0
                        self.episode_rewards = []
                        
                        # Update all environments to new curriculum level
                        for env in self.vec_env.envs:
                            # Unwrap Monitor to get the actual environment
                            actual_env = env
                            while hasattr(actual_env, 'env'):
                                actual_env = actual_env.env
                            actual_env.curriculum_level = self.current_level
                            actual_env.config = actual_env._apply_curriculum(actual_env._base_config.copy())
                        
                        print(f"\n🎓 CURRICULUM ADVANCED TO LEVEL {self.current_level}")
                        print(f"   Success rate: {success_rate:.0%} over {self.min_episodes} episodes")
                        
                        # Save curriculum checkpoint
                        self.model.save(f"/home/mr_nags/aeroforge/models/curriculum/level_{self.current_level}.zip")
        
        return True


class TrainingProgressCallback(BaseCallback):
    """Detailed training progress logging."""
    
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.best_reward = -np.inf
        self.start_time = time.time()
        
    def _on_step(self) -> bool:
        if self.n_calls % 5000 == 0:
            elapsed = time.time() - self.start_time
            hours = elapsed / 3600
            
            if len(self.model.ep_info_buffer) > 10:
                # Convert to list first since ep_info_buffer might not support slicing
                ep_info_list = list(self.model.ep_info_buffer)
                recent = [ep['r'] for ep in ep_info_list[-10:] if 'r' in ep]
                if recent:
                    avg_reward = np.mean(recent)
                    if avg_reward > self.best_reward:
                        self.best_reward = avg_reward
                        print(f"\n[NEW BEST] Avg reward (last 10): {avg_reward:.2f}")
            
            print(f"\n[Progress] Steps: {self.n_calls:,} | Time: {hours:.2f}h | "
                  f"FPS: {self.n_calls/elapsed:.0f} | Best avg: {self.best_reward:.2f}")
        
        return True


def create_vec_env(n_envs: int = 4, curriculum_level: int = 0, normalize: bool = True, add_monitor: bool = True):
    """Create vectorized environment with normalization."""
    env_fns = [make_env(curriculum_level=curriculum_level, seed=42+i, domain_randomize=True, config={}) 
               for i in range(n_envs)]
    vec_env = DummyVecEnv(env_fns)
    if add_monitor:
        vec_env = VecMonitor(vec_env)
    if normalize:
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.)
    return vec_env


def train_sac_optimized(total_timesteps: int = 5_000_000):
    """Train SAC with optimized hyperparameters for continuous control."""
    
    print(f"\n{'='*60}")
    print(f"🚀 STARTING SAC TRAINING - {total_timesteps:,} timesteps")
    print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
    print(f"{'='*60}\n")
    
    # Create directories
    Path("/home/mr_nags/aeroforge/models/checkpoints").mkdir(parents=True, exist_ok=True)
    Path("/home/mr_nags/aeroforge/models/best").mkdir(parents=True, exist_ok=True)
    Path("/home/mr_nags/aeroforge/models/curriculum").mkdir(parents=True, exist_ok=True)
    Path("/home/mr_nags/aeroforge/logs/tensorboard").mkdir(parents=True, exist_ok=True)
    Path("/home/mr_nags/aeroforge/logs/eval").mkdir(parents=True, exist_ok=True)
    
    # Create environments
    n_envs = 4  # Optimal for 4GB GPU
    train_env = create_vec_env(n_envs=n_envs, curriculum_level=0, normalize=True)
    
    # Action noise for exploration
    n_actions = train_env.action_space.shape[-1]
    action_noise = NormalActionNoise(
        mean=np.zeros(n_actions), 
        sigma=0.1 * np.ones(n_actions)
    )
    
    # SAC with optimized hyperparameters
    model = SAC(
        "MlpPolicy",
        train_env,
        learning_rate=3e-4,
        buffer_size=500_000,  # Large buffer for off-policy
        batch_size=512,       # Larger batch for stability
        tau=0.005,
        gamma=0.99,
        train_freq=1,
        gradient_steps=1,
        action_noise=action_noise,
        ent_coef="auto",
        target_update_interval=1,
        target_entropy="auto",
        use_sde=True,         # State-dependent exploration
        sde_sample_freq=4,
        policy_kwargs=dict(
            net_arch=[512, 512, 256],
            activation_fn=torch.nn.ReLU,
        ),
        verbose=1,
        device="cuda" if torch.cuda.is_available() else "cpu",
        tensorboard_log="/home/mr_nags/aeroforge/logs/tensorboard/",
    )
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=100_000,
        save_path="/home/mr_nags/aeroforge/models/checkpoints/",
        name_prefix="sac_drone"
    )
    
    # Evaluation environment - must match training env wrapper structure
    # For SAC, eval env needs VecNormalize to match training env
    eval_env = create_vec_env(n_envs=2, curriculum_level=4, normalize=True, add_monitor=False)
    # Ensure eval_env is properly wrapped with VecNormalize (it already is from create_vec_env)
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="/home/mr_nags/aeroforge/models/best/",
        log_path="/home/mr_nags/aeroforge/logs/eval/",
        eval_freq=50_000,
        n_eval_episodes=20,
        deterministic=True,
        render=False,
    )
    
    curriculum_callback = CurriculumCallback(train_env, threshold=0.8, min_episodes=50)
    progress_callback = TrainingProgressCallback()
    
    print(f"Training on {n_envs} parallel environments")
    print(f"Curriculum: 5 levels (hover → waypoint → static → dynamic → complex)")
    print(f"Domain randomization: ENABLED")
    print(f"Checkpointing: Every 100K steps")
    print(f"Evaluation: Every 50K steps (20 episodes)")
    print(f"Action noise: NormalActionNoise (sigma=0.1)")
    print(f"SDE exploration: ENABLED")
    print()
    
    start_time = time.time()
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, eval_callback, curriculum_callback, progress_callback],
            progress_bar=False,
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
    finally:
        training_time = time.time() - start_time
        print(f"\nTraining time: {training_time/3600:.2f} hours")
        
        # Save final model
        final_path = "/home/mr_nags/aeroforge/models/sac_drone_final.zip"
        model.save(final_path)
        print(f"Final model saved to: {final_path}")
        
        # Save VecNormalize stats
        train_env.save("/home/mr_nags/aeroforge/models/vec_normalize.pkl")
        
        # Save training config
        with open("/home/mr_nags/aeroforge/models/training_config.json", "w") as f:
            json.dump({
                "algorithm": "SAC",
                "total_timesteps": total_timesteps,
                "training_time_hours": training_time / 3600,
                "n_envs": n_envs,
                "curriculum_levels": 5,
                "domain_randomization": True,
                "action_noise": "NormalActionNoise(sigma=0.1)",
                "sde": True,
                "policy_arch": [512, 512, 256],
                "buffer_size": 500000,
                "batch_size": 512,
            }, f, indent=2)
            
    return model


def train_ppo_optimized(total_timesteps: int = 3_000_000):
    """Train PPO as secondary algorithm."""
    
    print(f"\n{'='*60}")
    print(f"🚀 STARTING PPO TRAINING - {total_timesteps:,} timesteps")
    print(f"{'='*60}\n")
    
    n_envs = 8  # PPO can use more envs
    train_env = create_vec_env(n_envs=n_envs, curriculum_level=0, normalize=True)
    
    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=1024,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        clip_range_vf=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_sde=True,
        sde_sample_freq=4,
        policy_kwargs=dict(
            net_arch=[dict(pi=[512, 512], vf=[512, 512])],
            activation_fn=torch.nn.ReLU,
        ),
        verbose=1,
        device="cuda" if torch.cuda.is_available() else "cpu",
        tensorboard_log="/home/mr_nags/aeroforge/logs/tensorboard/",
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=100_000,
        save_path="/home/mr_nags/aeroforge/models/checkpoints/",
        name_prefix="ppo_drone"
    )
    
    eval_env = create_vec_env(n_envs=2, curriculum_level=4, normalize=True, add_monitor=False)
    # Ensure eval_env is properly wrapped with VecNormalize (it already is from create_vec_env)
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="/home/mr_nags/aeroforge/models/best/",
        log_path="/home/mr_nags/aeroforge/logs/eval/",
        eval_freq=50_000,
        n_eval_episodes=20,
        deterministic=True,
    )
    
    curriculum_callback = CurriculumCallback(train_env, threshold=0.8, min_episodes=50)
    progress_callback = TrainingProgressCallback()
    
    start_time = time.time()
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, eval_callback, curriculum_callback, progress_callback],
            progress_bar=False,
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
    finally:
        training_time = time.time() - start_time
        print(f"\nTraining time: {training_time/3600:.2f} hours")
        
        final_path = "/home/mr_nags/aeroforge/models/ppo_drone_final.zip"
        model.save(final_path)
        print(f"Final model saved to: {final_path}")
        
        train_env.save("/home/mr_nags/aeroforge/models/vec_normalize_ppo.pkl")
        
    return model


def evaluate_model(model_path: str, algorithm: str = "SAC", n_episodes: int = 50):
    """Evaluate a trained model comprehensively."""
    print(f"\n{'='*60}")
    print(f"📊 EVALUATING {algorithm.upper()} MODEL")
    print(f"{'='*60}\n")
    
    if algorithm.upper() == "SAC":
        model = SAC.load(model_path)
    else:
        model = PPO.load(model_path)
    
    # Load VecNormalize if exists
    normalize_path = model_path.replace(".zip", "_vec_normalize.pkl")
    if os.path.exists(normalize_path):
        eval_env = create_vec_env(n_envs=1, curriculum_level=4, normalize=False)
        eval_env = VecNormalize.load(normalize_path, eval_env)
        eval_env.training = False
        eval_env.norm_reward = False
    else:
        eval_env = create_vec_env(n_envs=1, curriculum_level=4, normalize=False)
    
    results = []
    for ep in range(n_episodes):
        obs, _ = eval_env.reset()
        done = False
        ep_reward = 0
        ep_len = 0
        ep_collisions = 0
        ep_min_clearance = float('inf')
        ep_goal_dist = float('inf')
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = eval_env.step(action)
            done = terminated or truncated
            ep_reward += reward
            ep_len += 1
            
            # Get info from underlying env
            if hasattr(eval_env, 'envs'):
                env = eval_env.envs[0]
                if hasattr(env, 'unwrapped'):
                    env = env.unwrapped
                if hasattr(env, 'collisions'):
                    ep_collisions = env.collisions
                if hasattr(env, 'min_clearance'):
                    ep_min_clearance = min(ep_min_clearance, env.min_clearance)
                if 'goal_distance' in info:
                    ep_goal_dist = min(ep_goal_dist, info['goal_distance'])
        
        success = ep_collisions == 0 and ep_goal_dist < 1.0
        results.append({
            'success': success,
            'reward': ep_reward,
            'length': ep_len,
            'collisions': ep_collisions,
            'min_clearance': ep_min_clearance,
            'final_goal_dist': ep_goal_dist,
        })
    
    # Aggregate statistics
    successes = sum(1 for r in results if r['success'])
    avg_reward = np.mean([r['reward'] for r in results])
    avg_len = np.mean([r['length'] for r in results])
    avg_collisions = np.mean([r['collisions'] for r in results])
    avg_clearance = np.mean([r['min_clearance'] for r in results])
    
    print(f"\n📊 EVALUATION RESULTS ({n_episodes} episodes):")
    print(f"  Success Rate: {successes/n_episodes:.0%} ({successes}/{n_episodes})")
    print(f"  Avg Reward: {avg_reward:.2f}")
    print(f"  Avg Episode Length: {avg_len:.1f}")
    print(f"  Avg Collisions: {avg_collisions:.2f}")
    print(f"  Avg Min Clearance: {avg_clearance:.2f}m")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="AeroForge Ultimate RL Training")
    parser.add_argument("--algorithm", choices=["sac", "ppo", "both"], default="sac")
    parser.add_argument("--timesteps", type=int, default=5_000_000)
    parser.add_argument("--eval-only", type=str, help="Path to model to evaluate")
    parser.add_argument("--eval-algo", choices=["sac", "ppo"], default="sac")
    parser.add_argument("--eval-episodes", type=int, default=50)
    parser.add_argument("--resume", type=str, help="Path to checkpoint to resume")
    args = parser.parse_args()
    
    if args.eval_only:
        evaluate_model(args.eval_only, args.eval_algo, args.eval_episodes)
        return
    
    if args.algorithm in ["sac", "both"]:
        train_sac_optimized(args.timesteps)
    
    if args.algorithm in ["ppo", "both"]:
        train_ppo_optimized(args.timesteps if args.algorithm == "ppo" else 3_000_000)
    
    # Final evaluation of best models
    print("\n" + "="*60)
    print("🏁 FINAL EVALUATION OF BEST MODELS")
    print("="*60)
    
    best_sac = "/home/mr_nags/aeroforge/models/best/best_model.zip"
    if os.path.exists(best_sac):
        evaluate_model(best_sac, "SAC", 50)
    
    best_ppo = "/home/mr_nags/aeroforge/models/best/best_model.zip"
    # Note: PPO and SAC share best_model path, would need separate dirs


if __name__ == "__main__":
    main()