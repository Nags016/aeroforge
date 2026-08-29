#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
AeroForge RL Training Script - PPO/SAC for Drone Autonomy
Trains on GTX 1650 (4GB) with optimized settings
"""

import os
import sys
import time
import numpy as np
import torch
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.logger import configure
import json

# Add project path
sys.path.insert(0, '/home/mr_nags/aeroforge')

from agent.schemas import Vector3D, Obstacle


class DroneEnv(gym.Env):
    """Custom Gym environment for drone navigation."""
    
    def __init__(self, config: dict = None):
        super().__init__()
        
        self.config = config or {}
        self.max_steps = self.config.get('max_steps', 500)
        self.world_size = self.config.get('world_size', 50.0)
        self.num_obstacles = self.config.get('num_obstacles', 10)
        self.goal_threshold = self.config.get('goal_threshold', 1.0)
        self.collision_penalty = self.config.get('collision_penalty', -50.0)
        self.goal_reward = self.config.get('goal_reward', 100.0)
        self.time_penalty = self.config.get('time_penalty', -0.1)
        self.clearance_reward = self.config.get('clearance_reward', 2.0)
        self.clearance_threshold = self.config.get('clearance_threshold', 2.0)
        self.action_smoothness_weight = self.config.get('action_smoothness_weight', -0.01)
        
        # Observation space: 36 dims
        # [pos(3), vel(3), quat(4), goal_rel(3), 16-ray depth(16), prev_action(3), time_left(1), obstacles_info(4)]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(36,), dtype=np.float32
        )
        
        # Action space: 3D velocity command (normalized -1 to 1)
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(3,), dtype=np.float32
        )
        
        self.max_velocity = 10.0  # m/s
        self.max_acceleration = 5.0  # m/s^2
        self.dt = 0.1  # 10Hz
        
        self.reset()
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Random start and goal positions
        self.start_pos = np.array([
            np.random.uniform(-self.world_size/4, self.world_size/4),
            np.random.uniform(-self.world_size/4, self.world_size/4),
            np.random.uniform(1.0, 5.0)
        ], dtype=np.float32)
        
        self.goal_pos = np.array([
            np.random.uniform(-self.world_size/2, self.world_size/2),
            np.random.uniform(-self.world_size/2, self.world_size/2),
            np.random.uniform(1.0, 10.0)
        ], dtype=np.float32)
        
        # Ensure minimum distance
        while np.linalg.norm(self.goal_pos - self.start_pos) < 5.0:
            self.goal_pos = np.array([
                np.random.uniform(-self.world_size/2, self.world_size/2),
                np.random.uniform(-self.world_size/2, self.world_size/2),
                np.random.uniform(1.0, 10.0)
            ], dtype=np.float32)
        
        # Generate obstacles
        self.obstacles = []
        for _ in range(self.num_obstacles):
            obs = Obstacle(
                position=Vector3D(
                    x=np.random.uniform(-self.world_size/2, self.world_size/2),
                    y=np.random.uniform(-self.world_size/2, self.world_size/2),
                    z=np.random.uniform(0.5, 10.0)
                ),
                radius=np.random.uniform(0.5, 3.0),
                height=5.0
            )
            # Make sure obstacles don't spawn on start/goal
            if np.linalg.norm([obs.position.x - self.start_pos[0], obs.position.y - self.start_pos[1]]) > 3.0:
                if np.linalg.norm([obs.position.x - self.goal_pos[0], obs.position.y - self.goal_pos[1]]) > 3.0:
                    self.obstacles.append(obs)
                    
        self.position = self.start_pos.copy()
        self.velocity = np.zeros(3, dtype=np.float32)
        self.prev_action = np.zeros(3, dtype=np.float32)
        self.step_count = 0
        self.total_reward = 0.0
        self.collisions = 0
        self.min_clearance = float('inf')
        self.path_length = 0.0
        
        return self._get_obs(), {}
        
    def _get_obs(self):
        """Get 36-dimensional observation."""
        # Position (3)
        pos = self.position
        
        # Velocity (3)
        vel = self.velocity
        
        # Quaternion (simplified - identity for now) (4)
        quat = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        
        # Goal relative position (3)
        goal_rel = self.goal_pos - self.position
        
        # 16-ray depth sensor (16) - simulate lidar/depth rays
        depth_rays = self._simulate_depth_rays()
        
        # Previous action (3)
        prev_act = self.prev_action
        
        # Time left normalized (1)
        time_left = 1.0 - (self.step_count / self.max_steps)
        
        # Obstacle info: nearest obstacle distance, angle, count, dynamic_ratio (4)
        nearest_dist, nearest_angle = self._get_nearest_obstacle_info()
        obstacle_info = np.array([
            nearest_dist / self.world_size,
            nearest_angle / np.pi,
            len(self.obstacles) / 20.0,
            0.0  # dynamic ratio placeholder
        ], dtype=np.float32)
        
        obs = np.concatenate([
            pos, vel, quat, goal_rel, depth_rays, prev_act, 
            obstacle_info
        ]).astype(np.float32)
        
        return obs
        
    def _simulate_depth_rays(self, num_rays: int = 16) -> np.ndarray:
        """Simulate 16-ray depth sensor."""
        rays = np.ones(num_rays, dtype=np.float32) * 50.0  # max range 50m
        
        for i in range(num_rays):
            angle = 2 * np.pi * i / num_rays
            ray_dir = np.array([np.cos(angle), np.sin(angle), 0.0])
            
            for obs in self.obstacles:
                # Ray-cylinder intersection (simplified)
                oc = np.array([self.position[0] - obs.position.x, 
                              self.position[1] - obs.position.y])
                ray_2d = ray_dir[:2]
                
                a = np.dot(ray_2d, ray_2d)
                b = 2 * np.dot(oc, ray_2d)
                c = np.dot(oc, oc) - obs.radius**2
                
                disc = b*b - 4*a*c
                if disc >= 0:
                    t = (-b - np.sqrt(disc)) / (2*a)
                    if t > 0 and t < rays[i]:
                        rays[i] = t
                        
        return rays / 50.0  # Normalize
        
    def _get_nearest_obstacle_info(self):
        """Get nearest obstacle distance and angle."""
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
        """Check if drone collides with any obstacle."""
        for obs in self.obstacles:
            dx = self.position[0] - obs.position.x
            dy = self.position[1] - obs.position.y
            dz = self.position[2] - obs.position.z
            dist_xy = np.hypot(dx, dy)
            if dist_xy < obs.radius and abs(dz) < obs.height / 2:
                return True
        return False
        
    def _get_clearance(self) -> float:
        """Get minimum clearance from obstacles."""
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
        target_vel = action * self.max_velocity
        
        # Simple acceleration limiting
        accel = (target_vel - self.velocity) / self.dt
        accel_norm = np.linalg.norm(accel)
        if accel_norm > self.max_acceleration:
            accel = accel / accel_norm * self.max_acceleration
            
        self.velocity = self.velocity + accel * self.dt
        
        # Update position
        prev_pos = self.position.copy()
        self.position = self.position + self.velocity * self.dt
        
        # Geofence
        self.position = np.clip(self.position, 
                               [-self.world_size/2, -self.world_size/2, 0.1],
                               [self.world_size/2, self.world_size/2, 20.0])
        
        self.path_length += np.linalg.norm(self.position - prev_pos)
        self.step_count += 1
        self.prev_action = action.copy()
        
        # Compute reward
        reward = 0.0
        
        # Time penalty
        reward += self.time_penalty
        
        # Goal distance reward
        goal_dist = np.linalg.norm(self.goal_pos - self.position)
        reward += -goal_dist * 0.1  # distance weight
        
        # Clearance reward
        clearance = self._get_clearance()
        self.min_clearance = min(self.min_clearance, clearance)
        if clearance > self.clearance_threshold:
            reward += self.clearance_reward * (clearance - self.clearance_threshold)
        else:
            reward += -10.0 * (self.clearance_threshold - clearance)
            
        # Action smoothness
        action_diff = np.linalg.norm(action - self.prev_action)
        reward += self.action_smoothness_weight * action_diff
        
        # Check collision
        collided = self._check_collision()
        if collided:
            reward += self.collision_penalty
            self.collisions += 1
            
        # Check goal reached
        terminated = False
        if goal_dist < self.goal_threshold:
            reward += self.goal_reward
            terminated = True
            
        # Check max steps
        truncated = self.step_count >= self.max_steps
        
        self.total_reward += reward
        
        return self._get_obs(), reward, terminated, truncated, {
            'goal_distance': goal_dist,
            'clearance': clearance,
            'collisions': self.collisions,
            'step': self.step_count,
        }
        
    def render(self):
        pass


def make_env(config: dict = None):
    """Create environment factory."""
    def _init():
        env = DroneEnv(config)
        env = Monitor(env)
        return env
    return _init


class TrainingProgressCallback(BaseCallback):
    """Custom callback for detailed training progress."""
    
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.best_reward = -np.inf
        
    def _on_step(self) -> bool:
        if len(self.model.ep_info_buffer) > 0:
            ep_info = self.model.ep_info_buffer[-1]
            if 'r' in ep_info:
                self.episode_rewards.append(ep_info['r'])
                if ep_info['r'] > self.best_reward:
                    self.best_reward = ep_info['r']
                    print(f"\n[NEW BEST] Episode reward: {ep_info['r']:.2f}")
                    
        if self.n_calls % 10000 == 0:
            if len(self.episode_rewards) > 10:
                recent = self.episode_rewards[-10:]
                print(f"\n[Progress] Steps: {self.n_calls:,} | "
                      f"Recent avg reward: {np.mean(recent):.2f} | "
                      f"Best: {self.best_reward:.2f} | "
                      f"Episodes: {len(self.episode_rewards)}")
                      
        return True


def train_ppo(config: dict = None, total_timesteps: int = 1_000_000):
    """Train PPO policy."""
    
    # Default config
    default_config = {
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
    if config:
        default_config.update(config)
        
    # Create environments
    n_envs = 4  # Number of parallel envs
    env_fns = [make_env(default_config) for _ in range(n_envs)]
    vec_env = DummyVecEnv(env_fns)
    vec_env = VecMonitor(vec_env)
    
    # Policy network architecture
    policy_kwargs = dict(
        net_arch=[dict(pi=[256, 256], vf=[256, 256])],
        activation_fn=torch.nn.ReLU,
    )
    
    # Create PPO model
    model = PPO(
        "MlpPolicy",
        vec_env,
        policy_kwargs=policy_kwargs,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        device="cuda" if torch.cuda.is_available() else "cpu",
        tensorboard_log="/home/mr_nags/aeroforge/logs/tensorboard/",
    )
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path="/home/mr_nags/aeroforge/models/checkpoints/",
        name_prefix="ppo_drone"
    )
    
    eval_env = DummyVecEnv([make_env(default_config)])
    eval_env = VecMonitor(eval_env)
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="/home/mr_nags/aeroforge/models/best/",
        log_path="/home/mr_nags/aeroforge/logs/eval/",
        eval_freq=25000,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
    )
    
    progress_callback = TrainingProgressCallback()
    
    print(f"\n{'='*60}")
    print(f"Starting PPO Training")
    print(f"Total timesteps: {total_timesteps:,}")
    print(f"Device: {model.device}")
    print(f"Parallel envs: {n_envs}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, eval_callback, progress_callback],
            progress_bar=True,
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
    finally:
        training_time = time.time() - start_time
        print(f"\nTraining time: {training_time/3600:.2f} hours")
        
        # Save final model
        final_path = "/home/mr_nags/aeroforge/models/ppo_drone_final.zip"
        model.save(final_path)
        print(f"Final model saved to: {final_path}")
        
        # Save training config
        with open("/home/mr_nags/aeroforge/models/training_config.json", "w") as f:
            json.dump({
                "total_timesteps": total_timesteps,
                "training_time_hours": training_time / 3600,
                "config": default_config,
                "best_reward": progress_callback.best_reward,
                "total_episodes": len(progress_callback.episode_rewards),
            }, f, indent=2)
            
    return model


def train_sac(config: dict = None, total_timesteps: int = 500_000):
    """Train SAC policy (off-policy, better for continuous control)."""
    
    default_config = {
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
    if config:
        default_config.update(config)
        
    # SAC needs more memory, use fewer parallel envs
    n_envs = 2
    env_fns = [make_env(default_config) for _ in range(n_envs)]
    vec_env = DummyVecEnv(env_fns)
    vec_env = VecMonitor(vec_env)
    
    model = SAC(
        "MlpPolicy",
        vec_env,
        learning_rate=3e-4,
        buffer_size=100000,
        batch_size=256,
        tau=0.005,
        gamma=0.99,
        train_freq=1,
        gradient_steps=1,
        ent_coef="auto",
        verbose=1,
        device="cuda" if torch.cuda.is_available() else "cpu",
        tensorboard_log="/home/mr_nags/aeroforge/logs/tensorboard/",
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=25000,
        save_path="/home/mr_nags/aeroforge/models/checkpoints/",
        name_prefix="sac_drone"
    )
    
    eval_env = DummyVecEnv([make_env(default_config)])
    eval_env = VecMonitor(eval_env)
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="/home/mr_nags/aeroforge/models/best/",
        log_path="/home/mr_nags/aeroforge/logs/eval/",
        eval_freq=12500,
        n_eval_episodes=10,
        deterministic=True,
    )
    
    progress_callback = TrainingProgressCallback()
    
    print(f"\n{'='*60}")
    print(f"Starting SAC Training")
    print(f"Total timesteps: {total_timesteps:,}")
    print(f"Device: {model.device}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, eval_callback, progress_callback],
            progress_bar=True,
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
    finally:
        training_time = time.time() - start_time
        print(f"\nTraining time: {training_time/3600:.2f} hours")
        
        final_path = "/home/mr_nags/aeroforge/models/sac_drone_final.zip"
        model.save(final_path)
        print(f"Final model saved to: {final_path}")
        
    return model


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train RL policy for AeroForge")
    parser.add_argument("--algorithm", choices=["ppo", "sac"], default="ppo")
    parser.add_argument("--timesteps", type=int, default=1_000_000)
    parser.add_argument("--config", type=str, help="JSON config file")
    args = parser.parse_args()
    
    # Create directories
    os.makedirs("/home/mr_nags/aeroforge/models/checkpoints", exist_ok=True)
    os.makedirs("/home/mr_nags/aeroforge/models/best", exist_ok=True)
    os.makedirs("/home/mr_nags/aeroforge/logs/tensorboard", exist_ok=True)
    os.makedirs("/home/mr_nags/aeroforge/logs/eval", exist_ok=True)
    
    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
            
    if args.algorithm == "ppo":
        train_ppo(config, args.timesteps)
    else:
        train_sac(config, args.timesteps)