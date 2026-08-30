"""AeroForge RL Environment - Gymnasium wrapper for PX4+Gazebo RL training"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time
import logging
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

from agent.schemas import MissionSpec, ExperimentSpec, Vector3D, Obstacle, StrategyType

logger = logging.getLogger(__name__)


@dataclass
class DroneState:
    """Current drone state from PX4"""
    position: np.ndarray      # [x, y, z] in NED frame
    velocity: np.ndarray      # [vx, vy, vz] in body frame
    quaternion: np.ndarray    # [w, x, y, z]
    angular_velocity: np.ndarray  # [wx, wy, wz]
    battery_voltage: float
    battery_current: float
    gps_fix_type: int
    ekf_healthy: bool
    timestamp: float


class AeroForgeEnv(gym.Env):
    """
    Gymnasium environment for PX4 drone RL training.
    
    Observation Space (29 dims):
    - Position (3): x, y, z in NED
    - Velocity (3): vx, vy, vz in body frame
    - Quaternion (4): w, x, y, z
    - Goal relative position (3): goal - current_pos
    - Depth rays (16): 16-ray depth sensor (simulated)
    
    Action Space (3 dims):
    - Velocity command: [vx, vy, vz] normalized [-1, 1]
    - Maps to max_velocity_mps * action
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}
    
    def __init__(
        self,
        mission_spec: MissionSpec,
        experiment_spec: ExperimentSpec,
        render_mode: Optional[str] = None,
        max_velocity_mps: float = 10.0,
        max_episode_steps: int = 500,
        use_gazebo: bool = True,
        headless: bool = True,
    ):
        super().__init__()
        
        self.mission_spec = mission_spec
        self.experiment_spec = experiment_spec
        self.render_mode = render_mode
        self.max_velocity_mps = max_velocity_mps
        self.max_episode_steps = max_episode_steps
        self.use_gazebo = use_gazebo
        self.headless = headless
        
        # Observation: 29 dims
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(29,), dtype=np.float32
        )
        
        # Action: 3 dims (velocity command)
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(3,), dtype=np.float32
        )
        
        # Episode state
        self.current_step = 0
        self.episode_reward = 0.0
        self.total_collisions = 0
        self.min_clearance = float('inf')
        self.path_length = 0.0
        self.prev_position = None
        
        # Goal
        self.goal = np.array([mission_spec.goal.x, mission_spec.goal.y, mission_spec.goal.z])
        self.start = np.array([mission_spec.start.x, mission_spec.start.y, mission_spec.start.z])
        
        # Obstacles
        self.obstacles = [
            np.array([obs.position.x, obs.position.y, obs.position.z]) 
            for obs in mission_spec.known_obstacles
        ]
        self.obstacle_radii = [obs.radius for obs in mission_spec.known_obstacles]
        
        # Reward weights from experiment spec
        self.reward_config = experiment_spec.reward_config
        
        # PX4 connection (mock for now, replace with MAVLink/ROS2)
        self.px4_connected = False
        self.current_state = DroneState(
            position=self.start.copy(),
            velocity=np.zeros(3),
            quaternion=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.zeros(3),
            battery_voltage=16.8,
            battery_current=0.0,
            gps_fix_type=3,
            ekf_healthy=True,
            timestamp=time.time(),
        )
        
        # For rendering
        self.render_window = None
        
        logger.info(f"AeroForgeEnv initialized: goal={self.goal}, max_steps={max_episode_steps}")
    
    def _get_observation(self) -> np.ndarray:
        """Construct observation vector (29 dims)."""
        pos = self.current_state.position
        vel = self.current_state.velocity
        quat = self.current_state.quaternion
        
        # Goal relative position
        goal_rel = self.goal - pos
        
        # Simulated depth rays (16 directions)
        depth_rays = self._simulate_depth_rays(pos)
        
        obs = np.concatenate([
            pos,                    # 3
            vel,                    # 3
            quat,                   # 4
            goal_rel,               # 3
            depth_rays,             # 16
        ]).astype(np.float32)
        
        return obs
    
    def _simulate_depth_rays(self, position: np.ndarray) -> np.ndarray:
        """Simulate 16-ray depth sensor."""
        rays = np.full(16, 50.0)  # Max range 50m
        
        # 16 directions: 8 horizontal + 4 up/down + 4 diagonal
        directions = np.array([
            [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0],  # Cardinal
            [0.707, 0.707, 0], [-0.707, 0.707, 0], [0.707, -0.707, 0], [-0.707, -0.707, 0],  # Diagonal
            [0, 0, 1], [0, 0, -1],  # Up/Down
            [0.577, 0.577, 0.577], [-0.577, 0.577, 0.577], [0.577, -0.577, 0.577], [-0.577, -0.577, 0.577],  # 3D diagonal
        ])
        
        for i, dir_vec in enumerate(directions):
            min_dist = 50.0
            for obs_pos, radius in zip(self.obstacles, self.obstacle_radii):
                # Ray-sphere intersection
                oc = position - obs_pos
                a = np.dot(dir_vec, dir_vec)
                b = 2.0 * np.dot(oc, dir_vec)
                c = np.dot(oc, oc) - radius**2
                disc = b**2 - 4*a*c
                if disc >= 0:
                    t = (-b - np.sqrt(disc)) / (2*a)
                    if t > 0 and t < min_dist:
                        min_dist = t
            rays[i] = min_dist
        
        return rays.astype(np.float32)
    
    def _compute_reward(self, action: np.ndarray) -> Tuple[float, Dict[str, float]]:
        """Compute dense reward with shaping."""
        pos = self.current_state.position
        vel = self.current_state.velocity
        
        # Distance to goal
        dist_to_goal = np.linalg.norm(self.goal - pos)
        
        # Minimum clearance to obstacles
        min_clearance = float('inf')
        for obs_pos, radius in zip(self.obstacles, self.obstacle_radii):
            clearance = np.linalg.norm(pos - obs_pos) - radius
            min_clearance = min(min_clearance, clearance)
        
        self.min_clearance = min(self.min_clearance, min_clearance)
        
        # Collision check
        collision = min_clearance <= 0.0
        if collision:
            self.total_collisions += 1
        
        # Path length
        if self.prev_position is not None:
            self.path_length += np.linalg.norm(pos - self.prev_position)
        self.prev_position = pos.copy()
        
        # Reward components
        reward_components = {}
        
        # Goal reward (dense + sparse)
        reward_components["goal_distance"] = -dist_to_goal * self.reward_config.get("goal_distance_weight", 1.0)
        if dist_to_goal < 0.5:
            reward_components["goal_reached"] = self.reward_config.get("goal_reward", 100.0)
        
        # Collision penalty
        if collision:
            reward_components["collision"] = self.reward_config.get("collision_penalty", -50.0)
        
        # Clearance reward
        reward_components["clearance"] = min(3.0, max(0.0, min_clearance)) * self.reward_config.get("clearance_reward_weight", 2.0)
        
        # Time penalty
        reward_components["time"] = self.reward_config.get("time_penalty", -0.1)
        
        # Action smoothness
        action_mag = np.linalg.norm(action)
        reward_components["action_smooth"] = -action_mag * self.reward_config.get("action_smoothness_weight", 0.01)
        
        # Velocity penalty (energy)
        vel_mag = np.linalg.norm(vel)
        reward_components["velocity"] = -vel_mag * self.reward_config.get("velocity_weight", 0.1)
        
        # Total reward
        total_reward = sum(reward_components.values())
        
        return total_reward, reward_components
    
    def _check_terminated(self) -> bool:
        """Check if episode should terminate."""
        pos = self.current_state.position
        
        # Goal reached
        if np.linalg.norm(self.goal - pos) < 0.5:
            return True
        
        # Collision
        if self.total_collisions > 0:
            return True
        
        # Out of bounds
        bounds = self.mission_spec.map_bounds
        if (pos[0] < bounds["min"].x or pos[0] > bounds["max"].x or
            pos[1] < bounds["min"].y or pos[1] > bounds["max"].y or
            pos[2] < bounds["min"].z or pos[2] > bounds["max"].z):
            return True
        
        return False
    
    def _check_truncated(self) -> bool:
        """Check if episode should truncate (max steps)."""
        return self.current_step >= self.max_episode_steps
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one environment step."""
        self.current_step += 1
        
        # Apply action: velocity command
        # action is [-1, 1]^3, scale to max_velocity
        velocity_cmd = action * self.max_velocity_mps
        
        # Simulate physics (simple integration for now)
        dt = 0.1  # 10 Hz control
        self.current_state.velocity = velocity_cmd
        self.current_state.position += velocity_cmd * dt
        self.current_state.timestamp = time.time()
        
        # Compute reward
        reward, reward_info = self._compute_reward(action)
        self.episode_reward += reward
        
        # Check termination
        terminated = self._check_terminated()
        truncated = self._check_truncated()
        
        # Observation
        obs = self._get_observation()
        
        # Info dict
        info = {
            "step": self.current_step,
            "episode_reward": self.episode_reward,
            "dist_to_goal": np.linalg.norm(self.goal - self.current_state.position),
            "min_clearance": self.min_clearance,
            "total_collisions": self.total_collisions,
            "path_length": self.path_length,
            "reward_components": reward_info,
            "success": np.linalg.norm(self.goal - self.current_state.position) < 0.5 and self.total_collisions == 0,
        }
        
        return obs, reward, terminated, truncated, info
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state."""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.episode_reward = 0.0
        self.total_collisions = 0
        self.min_clearance = float('inf')
        self.path_length = 0.0
        self.prev_position = None
        
        # Reset drone state
        self.current_state = DroneState(
            position=self.start.copy(),
            velocity=np.zeros(3),
            quaternion=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.zeros(3),
            battery_voltage=16.8,
            battery_current=0.0,
            gps_fix_type=3,
            ekf_healthy=True,
            timestamp=time.time(),
        )
        
        obs = self._get_observation()
        info = {
            "mission_id": self.mission_spec.mission_id,
            "experiment_id": self.experiment_spec.experiment_id,
        }
        
        return obs, info
    
    def render(self) -> Optional[np.ndarray]:
        """Render environment (optional)."""
        if self.render_mode == "rgb_array":
            # Return RGB array for video recording
            return np.zeros((480, 640, 3), dtype=np.uint8)
        return None
    
    def close(self):
        """Clean up resources."""
        if self.render_window:
            self.render_window.close()
        logger.info("AeroForgeEnv closed")


# Factory function for Ray/SB3
def make_aeroforge_env(mission_spec: MissionSpec, experiment_spec: ExperimentSpec, **kwargs):
    """Factory function for creating AeroForgeEnv."""
    return AeroForgeEnv(mission_spec, experiment_spec, **kwargs)


# Curriculum environments
class CurriculumEnv:
    """Manages curriculum learning progression."""
    
    LEVELS = [
        {"name": "hover", "goal": [0, 0, 2], "obstacles": [], "max_steps": 200},
        {"name": "waypoint", "goal": [5, 0, 2], "obstacles": [], "max_steps": 300},
        {"name": "multi_waypoint", "goal": [10, 5, 2], "obstacles": [], "max_steps": 400},
        {"name": "static_obstacles", "goal": [15, 10, 2], "obstacles": [[5, 2, 2, 1.5], [10, 8, 2, 2.0]], "max_steps": 500},
        {"name": "dynamic_obstacles", "goal": [20, 15, 3], "obstacles": [[8, 5, 2, 1.5], [15, 12, 2, 2.0]], "max_steps": 500},
    ]
    
    def __init__(self, base_mission: MissionSpec, base_experiment: ExperimentSpec):
        self.base_mission = base_mission
        self.base_experiment = base_experiment
        self.current_level = 0
    
    def get_env(self, level: Optional[int] = None) -> AeroForgeEnv:
        """Get environment for specific curriculum level."""
        if level is None:
            level = self.current_level
        
        level_config = self.LEVELS[min(level, len(self.LEVELS) - 1)]
        
        # Create modified mission spec
        from agent.schemas import MissionSpec, Vector3D, Obstacle
        mission = MissionSpec(
            mission_id=f"{self.base_mission.mission_id}_level{level}",
            start=self.base_mission.start,
            goal=Vector3D(*level_config["goal"]),
            map_bounds=self.base_mission.map_bounds,
            known_obstacles=[
                Obstacle(position=Vector3D(*obs[:3]), radius=obs[3]) 
                for obs in level_config["obstacles"]
            ],
        )
        
        experiment = ExperimentSpec(
            experiment_id=f"{self.base_experiment.experiment_id}_level{level}",
            mission_id=mission.mission_id,
            strategy=self.base_experiment.strategy,
            max_steps_per_episode=level_config["max_steps"],
        )
        
        return AeroForgeEnv(mission, experiment)
    
    def advance(self) -> bool:
        """Advance to next curriculum level."""
        if self.current_level < len(self.LEVELS) - 1:
            self.current_level += 1
            return True
        return False


if __name__ == "__main__":
    # Quick test
    from agent.schemas import MissionSpec, ExperimentSpec, Vector3D, StrategyType
    
    mission = MissionSpec(
        mission_id="test_001",
        start=Vector3D(0, 0, 2),
        goal=Vector3D(10, 10, 2),
    )
    
    exp_spec = ExperimentSpec(
        experiment_id="test_exp",
        mission_id=mission.mission_id,
        strategy=StrategyType.RL_PPO,
    )
    
    env = AeroForgeEnv(mission, exp_spec)
    obs, info = env.reset()
    print(f"Observation shape: {obs.shape}")
    print(f"Action space: {env.action_space}")
    
    for _ in range(5):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Reward: {reward:.3f}, Dist: {info['dist_to_goal']:.2f}, Terminated: {terminated}")
    
    env.close()
    print("✅ Test passed!")