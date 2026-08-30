"""AeroForge - Enhanced Schemas with Math/Learning Capabilities"""

from typing import Literal, Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import numpy as np


class StrategyType(str, Enum):
    CLASSICAL_MPC = "classical_mpc"
    CLASSICAL_RRT = "classical_rrt"
    RL_PPO = "rl_ppo"
    RL_SAC = "rl_sac"
    HYBRID_MPC_RL = "hybrid_mpc_rl"
    HYBRID_RRT_RL = "hybrid_rrt_rl"


class ControlLevel(str, Enum):
    OFFBOARD_POSITION = "offboard_position"
    OFFBOARD_VELOCITY = "offboard_velocity"
    OFFBOARD_ACCELERATION = "offboard_acceleration"
    OFFBOARD_ATTITUDE = "offboard_attitude"


class SensorRequirement(str, Enum):
    CAMERA = "camera"
    DEPTH = "depth"
    LIDAR = "lidar"
    GPS = "gps"
    IMU = "imu"
    OPTICAL_FLOW = "optical_flow"


class ObstacleAvoidancePolicy(str, Enum):
    NONE = "none"
    REACTIVE_POTENTIAL_FIELD = "reactive_potential_field"
    REACTIVE_VELOCITY_OBSTACLE = "reactive_velocity_obstacle"
    PLANNER_RRT = "planner_rrt"
    PLANNER_RRT_STAR = "planner_rrt_star"
    LEARNED_POLICY = "learned_policy"


class LearningObjective(str, Enum):
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_ENERGY = "minimize_energy"
    MINIMIZE_PATH_LENGTH = "minimize_path_length"
    MAXIMIZE_SAFETY = "maximize_safety"
    BALANCED = "balanced"


class Vector3D(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, **kwargs):
        super().__init__(x=x, y=y, z=z, **kwargs)
    
    def to_numpy(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    def distance_to(self, other: "Vector3D") -> float:
        return float(np.linalg.norm(self.to_numpy() - other.to_numpy()))
    
    def __add__(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)
    
    def __sub__(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)
    
    def __mul__(self, scalar: float) -> "Vector3D":
        return Vector3D(x=self.x * scalar, y=self.y * scalar, z=self.z * scalar)


class Quaternion(BaseModel):
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Obstacle(BaseModel):
    position: Vector3D
    radius: float
    height: float = 5.0
    velocity: Optional[Vector3D] = None  # For dynamic obstacles
    obstacle_type: str = "static"  # static, dynamic, unknown


class MissionSpec(BaseModel):
    """Structured mission specification from natural language."""
    mission_id: str = Field(default_factory=lambda: f"mission_{int(np.random.randint(100000)):06d}")
    
    # Spatial
    start: Vector3D = Field(default_factory=lambda: Vector3D(0, 0, 2))
    goal: Vector3D = Field(default_factory=lambda: Vector3D(10, 10, 2))
    waypoints: List[Vector3D] = Field(default_factory=list)
    
    # Environment
    known_obstacles: List[Obstacle] = Field(default_factory=list)
    map_bounds: Dict[str, Vector3D] = Field(default_factory=lambda: {
        "min": Vector3D(-50, -50, 0),
        "max": Vector3D(50, 50, 20)
    })
    
    # Sensors & Perception
    sensor_requirements: List[SensorRequirement] = Field(default_factory=lambda: [
        SensorRequirement.GPS, SensorRequirement.IMU
    ])
    obstacle_avoidance: ObstacleAvoidancePolicy = ObstacleAvoidancePolicy.REACTIVE_POTENTIAL_FIELD
    minimum_clearance_m: float = Field(default=1.5, ge=0.5, le=10.0)
    
    # Objectives with weights (math-based optimization)
    objectives: Dict[LearningObjective, float] = Field(default_factory=lambda: {
        LearningObjective.BALANCED: 1.0
    })
    
    # Constraints (hard limits)
    constraints: Dict[str, Any] = Field(default_factory=lambda: {
        "max_velocity_mps": 10.0,
        "max_acceleration_mps2": 5.0,
        "max_flight_time_s": 120.0,
        "geofence_enabled": True,
        "no_fly_zones": [],
    })
    
    # Learning preferences
    strategy_preference: Optional[StrategyType] = None
    learning_enabled: bool = True
    max_learning_iterations: int = 20
    
    # Acceptance criteria (mathematical thresholds)
    acceptance_criteria: Dict[str, float] = Field(default_factory=lambda: {
        "max_collisions": 0.0,
        "max_goal_error_m": 0.5,
        "min_clearance_m": 1.5,
        "max_flight_time_s": 60.0,
        "min_success_rate": 0.9,
    })
    
    # Human-in-the-loop
    human_guidance: Optional[str] = None
    ask_for_clarification: bool = True
    
    @field_validator("objectives")
    @classmethod
    def normalize_objectives(cls, v: Dict[LearningObjective, float]) -> Dict[LearningObjective, float]:
        total = sum(v.values())
        if total > 0:
            return {k: v / total for k, v in v.items()}
        return v


class ExperimentSpec(BaseModel):
    """Experiment configuration for autonomy algorithm."""
    experiment_id: str = Field(default_factory=lambda: f"exp_{int(np.random.randint(100000)):06d}")
    mission_id: str
    
    # Strategy
    strategy: StrategyType
    control_level: ControlLevel = ControlLevel.OFFBOARD_VELOCITY
    
    # Observation/Action spaces (math-defined)
    observation_space: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "Box",
        "shape": [36],
        "low": float(-np.inf),
        "high": float(np.inf),
    })
    action_space: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "Box",
        "shape": [3],
        "low": -1.0,
        "high": 1.0,
    })
    
    # Algorithm config
    algorithm: str = "PPO"
    algorithm_config: Dict[str, Any] = Field(default_factory=lambda: {
        "learning_rate": 3e-4,
        "n_steps": 2048,
        "batch_size": 64,
        "n_epochs": 10,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "ent_coef": 0.01,
        "vf_coef": 0.5,
        "max_grad_norm": 0.5,
    })
    
    # Reward function (mathematical)
    reward_config: Dict[str, float] = Field(default_factory=lambda: {
        "goal_reward": 100.0,
        "goal_distance_weight": -1.0,
        "velocity_weight": -0.1,
        "acceleration_weight": -0.05,
        "collision_penalty": -50.0,
        "clearance_reward_weight": 2.0,
        "clearance_threshold": 2.0,
        "time_penalty": -0.1,
        "action_smoothness_weight": -0.01,
    })
    
    # Environment
    world_config: Dict[str, Any] = Field(default_factory=dict)
    obstacle_config: Dict[str, Any] = Field(default_factory=lambda: {
        "num_obstacles": 10,
        "obstacle_radius_range": [0.5, 3.0],
        "dynamic_obstacle_ratio": 0.2,
    })
    
    # Training/Eval
    n_episodes: int = 100
    max_steps_per_episode: int = 500
    eval_episodes: int = 10
    eval_frequency: int = 10
    
    # Learning state (for continual learning)
    policy_checkpoint: Optional[str] = None
    replay_buffer_path: Optional[str] = None
    training_history: List[Dict[str, float]] = Field(default_factory=list)
    
    # Acceptance thresholds
    success_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "collision_rate": 0.0,
        "goal_reach_rate": 0.9,
        "avg_clearance_m": 1.5,
        "avg_flight_time_s": 60.0,
    })


class Metrics(BaseModel):
    """Standardized experiment metrics with statistical rigor."""
    success: bool
    collision_count: int = 0
    goal_error_m: float = 0.0
    minimum_clearance_m: float = 0.0
    mean_clearance_m: float = 0.0
    path_length_m: float = 0.0
    flight_time_s: float = 0.0
    smoothness_score: float = 0.0  # jerk integral
    energy_consumption: float = 0.0  # proxy: sum of |a|^2
    experiment_id: str
    
    # Statistical
    n_episodes: int = 1
    success_rate: float = 0.0
    std_goal_error_m: float = 0.0
    std_clearance_m: float = 0.0
    
    # Optional
    inference_latency_ms: Optional[float] = None
    training_time_s: Optional[float] = None
    
    def compute_composite_score(self, weights: Dict[str, float]) -> float:
        """Compute weighted composite score for optimization."""
        normalized = {
            "success_rate": self.success_rate,
            "goal_accuracy": 1.0 / (1.0 + self.goal_error_m),
            "safety": min(1.0, self.mean_clearance_m / 3.0),
            "efficiency": 1.0 / (1.0 + self.flight_time_s / 60.0),
            "smoothness": self.smoothness_score,
        }
        return sum(weights.get(k, 0) * v for k, v in normalized.items())


class BaselineMissionResult(BaseModel):
    """Result from running baseline mission."""
    success: bool
    metrics: Metrics
    duration_s: float
    error: Optional[str] = None
    telemetry_path: Optional[str] = None
    log_path: Optional[str] = None


class EnvironmentStatus(BaseModel):
    """Current simulation environment status."""
    px4_sitl_available: bool
    gazebo_available: bool
    ros2_available: bool
    camera_available: bool
    depth_camera_available: bool
    micro_ros_agent_running: bool
    px4_version: Optional[str] = None
    gazebo_version: Optional[str] = None
    ros2_distro: Optional[str] = None
    available_strategies: List[StrategyType] = Field(default_factory=list)
    compute_available: Dict[str, bool] = Field(default_factory=lambda: {
        "cpu": True,
        "cuda": False,
        "mps": False,
    })


class LearningState(BaseModel):
    """Persistent learning state for continual improvement."""
    mission_id: str
    best_policy_path: Optional[str] = None
    best_metrics: Optional[Metrics] = None
    training_history: List[Dict[str, Any]] = Field(default_factory=list)
    hyperparameter_history: List[Dict[str, Any]] = Field(default_factory=list)
    human_feedback_history: List[Dict[str, Any]] = Field(default_factory=list)
    total_experiments: int = 0
    total_training_time_s: float = 0.0
    last_updated: str = ""
    
    def update_from_experiment(self, exp_spec: ExperimentSpec, metrics: Metrics):
        self.total_experiments += 1
        self.training_history.append({
            "experiment_id": exp_spec.experiment_id,
            "strategy": exp_spec.strategy.value,
            "metrics": metrics.model_dump(),
            "algorithm_config": exp_spec.algorithm_config,
            "reward_config": exp_spec.reward_config,
        })
        self.hyperparameter_history.append({
            "experiment_id": exp_spec.experiment_id,
            "algorithm_config": exp_spec.algorithm_config,
            "reward_config": exp_spec.reward_config,
        })
        if self.best_metrics is None or metrics.compute_composite_score({
            "success_rate": 0.3, "goal_accuracy": 0.2, "safety": 0.2,
            "efficiency": 0.15, "smoothness": 0.15
        }) > self.best_metrics.compute_composite_score({
            "success_rate": 0.3, "goal_accuracy": 0.2, "safety": 0.2,
            "efficiency": 0.15, "smoothness": 0.15
        }):
            self.best_metrics = metrics
            self.best_policy_path = exp_spec.policy_checkpoint