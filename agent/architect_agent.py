"""Autonomy Architect Agent - selects optimal strategy based on mission and environment"""

from typing import Optional
from agent.schemas import (
    MissionSpec, ExperimentSpec, EnvironmentStatus, 
    StrategyType, ControlLevel, SensorRequirement, ObstacleAvoidancePolicy,
    LearningObjective, Vector3D
)
import numpy as np


class AutonomyArchitect:
    """Selects optimal autonomy strategy based on mission requirements and environment capabilities."""
    
    def __init__(self):
        self.strategy_scores = {}
    
    def select_strategy(self, mission: MissionSpec, env: EnvironmentStatus) -> ExperimentSpec:
        """Select optimal strategy based on mission requirements and environment."""
        
        # Score each available strategy
        scores = self._score_strategies(mission, env)
        best_strategy = max(scores, key=scores.get)
        
        # Create experiment spec based on selected strategy
        experiment = self._create_experiment_spec(mission, best_strategy, env, scores)
        
        return experiment
    
    def _score_strategies(self, mission: MissionSpec, env: EnvironmentStatus) -> Dict[StrategyType, float]:
        """Score each strategy based on mission requirements and environment."""
        scores = {}
        
        # Get available strategies based on environment
        available = self._get_available_strategies(env)
        
        for strategy in available:
            score = 0.0
            
            # Base scores per strategy
            if strategy == StrategyType.CLASSICAL_MPC:
                score = self._score_classical_mpc(mission, env)
            elif strategy == StrategyType.CLASSICAL_RRT:
                score = self._score_classical_rrt(mission, env)
            elif strategy == StrategyType.RL_PPO:
                score = self._score_rl_ppo(mission, env)
            elif strategy == StrategyType.RL_SAC:
                score = self._score_rl_sac(mission, env)
            elif strategy == StrategyType.HYBRID_MPC_RL:
                score = self._score_hybrid_mpc_rl(mission, env)
            elif strategy == StrategyType.HYBRID_RRT_RL:
                score = self._score_hybrid_rrt_rl(mission, env)
            
            scores[strategy] = score
        
        return scores
    
    def _get_available_strategies(self, env: EnvironmentStatus) -> List[StrategyType]:
        """Determine which strategies are available based on environment."""
        available = [StrategyType.CLASSICAL_MPC, StrategyType.CLASSICAL_RRT]
        
        # RL strategies need compute
        if env.compute_available.get("cuda", False) or env.compute_available.get("mps", False):
            available.extend([StrategyType.RL_PPO, StrategyType.RL_SAC])
            available.extend([StrategyType.HYBRID_MPC_RL, StrategyType.HYBRID_RRT_RL])
        elif env.compute_available.get("cpu", False):
            # CPU-only RL is slow but possible for simple tasks
            available.extend([StrategyType.RL_PPO])
        
        # Camera/depth enables visual strategies
        if env.camera_available or env.depth_camera_available:
            pass  # Already covered
        
        return available
    
    def _score_classical_mpc(self, mission: MissionSpec, env: EnvironmentStatus) -> float:
        """Score Classical MPC strategy."""
        score = 0.7  # Base score
        
        # Good for: known environments, precise control, real-time guarantees
        if mission.obstacle_avoidance in [ObstacleAvoidancePolicy.NONE, ObstacleAvoidancePolicy.REACTIVE_POTENTIAL_FIELD]:
            score += 0.2
        
        # Penalize if many dynamic obstacles
        if len(mission.known_obstacles) > 10:
            score -= 0.1
        
        # Good for tight clearance requirements
        if mission.minimum_clearance_m < 2.0:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _score_classical_rrt(self, mission: MissionSpec, env: EnvironmentStatus) -> float:
        """Score Classical RRT strategy."""
        score = 0.6  # Base score
        
        # Good for: unknown environments, global planning
        if mission.obstacle_avoidance in [ObstacleAvoidancePolicy.PLANNER_RRT, ObstacleAvoidancePolicy.PLANNER_RRT_STAR]:
            score += 0.3
        
        # Good for complex environments
        if len(mission.known_obstacles) > 5:
            score += 0.2
        
        # Slower, not ideal for real-time
        if mission.constraints.get("max_flight_time_s", 60) < 30:
            score -= 0.1
        
        return min(1.0, max(0.0, score))
    
    def _score_rl_ppo(self, mission: MissionSpec, env: EnvironmentStatus) -> float:
        """Score RL PPO strategy."""
        score = 0.5  # Base score
        
        # Good for: learning complex behaviors, adapting to dynamics
        if mission.learning_enabled:
            score += 0.3
        
        # Good for: complex obstacle fields, dynamic obstacles
        if mission.obstacle_avoidance == ObstacleAvoidancePolicy.LEARNED_POLICY:
            score += 0.2
        
        # Needs GPU for reasonable training time
        if env.compute_available.get("cuda", False):
            score += 0.2
        elif env.compute_available.get("mps", False):
            score += 0.1
        else:
            score -= 0.2  # CPU training is slow
        
        # Camera/depth helps RL
        if env.camera_available or env.depth_camera_available:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _score_rl_sac(self, mission: MissionSpec, env: EnvironmentStatus) -> float:
        """Score RL SAC strategy."""
        score = self._score_rl_ppo(mission, env)
        
        # SAC better for continuous control
        if mission.obstacle_avoidance == ObstacleAvoidancePolicy.LEARNED_POLICY:
            score += 0.1
        
        # SAC handles continuous actions better
        return min(1.0, max(0.0, score))
    
    def _score_hybrid_mpc_rl(self, mission: MissionSpec, env: EnvironmentStatus) -> float:
        """Score Hybrid MPC+RL strategy."""
        score = 0.6  # Base score
        
        # Best of both worlds: MPC for safety, RL for adaptation
        if mission.learning_enabled and mission.minimum_clearance_m < 2.0:
            score += 0.2
        
        # Good for dynamic environments with safety constraints
        if mission.obstacle_avoidance == ObstacleAvoidancePolicy.LEARNED_POLICY:
            score += 0.2
        
        # Needs compute for both
        if env.compute_available.get("cuda", False):
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _score_hybrid_rrt_rl(self, mission: MissionSpec, env: EnvironmentStatus) -> float:
        """Score Hybrid RRT+RL strategy."""
        score = 0.5  # Base score
        
        # Good for unknown environments with learning
        if mission.obstacle_avoidance == ObstacleAvoidancePolicy.LEARNED_POLICY:
            score += 0.2
        
        if len(mission.known_obstacles) < 5:  # Unknown environment
            score += 0.2
        
        return min(1.0, max(0.0, score))
    
    def _create_experiment_spec(self, mission: MissionSpec, strategy: StrategyType, 
                                 env: EnvironmentStatus, scores: Dict[StrategyType, float]) -> ExperimentSpec:
        """Create experiment specification from selected strategy."""
        
        experiment_id = f"exp_{mission.mission_id.split('_')[-1]}"
        
        # Configure based on strategy
        if strategy in [StrategyType.CLASSICAL_MPC]:
            config = self._get_mpc_config(mission)
        elif strategy in [StrategyType.CLASSICAL_RRT, StrategyType.CLASSICAL_RRT]:
            config = self._get_rrt_config(mission)
        elif strategy in [StrategyType.RL_PPO]:
            config = self._get_ppo_config(mission)
        elif strategy in [StrategyType.RL_SAC]:
            config = self._get_sac_config(mission)
        elif strategy in [StrategyType.HYBRID_MPC_RL]:
            config = self._get_hybrid_mpc_rl_config(mission)
        else:
            config = self._get_hybrid_rrt_rl_config(mission)
        
        # Build reward config from mission objectives
        reward_config = self._build_reward_config(mission)
        
        experiment = ExperimentSpec(
            experiment_id=f"exp_{mission.mission_id}",
            mission_id=mission.mission_id,
            strategy=strategy,
            control_level=ControlLevel.OFFBOARD_VELOCITY,
            algorithm=config["algorithm"],
            algorithm_config=config["algorithm_config"],
            reward_config=reward_config,
            world_config={
                "bounds": {
                    "min": mission.map_bounds["min"].model_dump(),
                    "max": mission.map_bounds["max"].model_dump(),
                },
                "obstacles": [obs.model_dump() for obs in mission.known_obstacles],
            },
            obstacle_config={
                "num_obstacles": max(5, len(mission.known_obstacles)),
                "obstacle_radius_range": [0.5, 3.0],
                "dynamic_obstacle_ratio": 0.2,
            },
            n_episodes=config["n_episodes"],
            max_steps_per_episode=config["max_steps"],
            eval_episodes=10,
            success_thresholds={
                "collision_rate": mission.acceptance_criteria.get("max_collisions", 0.0),
                "goal_reach_rate": 1.0 - mission.acceptance_criteria.get("max_goal_error_m", 0.5) / 10.0,
                "avg_clearance_m": mission.minimum_clearance_m,
                "avg_flight_time_s": mission.constraints.get("max_flight_time_s", 60.0),
            }
        )
        
        return experiment
    
    def _get_mpc_config(self, mission: MissionSpec) -> Dict:
        return {
            "algorithm": "MPC",
            "algorithm_config": {
                "horizon": 20,
                "dt": 0.1,
                "Q": [10, 10, 10, 1, 1, 1, 0.1, 0.1, 0.1],  # state weights
                "R": [1, 1, 1],  # control weights
                "max_velocity": mission.constraints.get("max_velocity_mps", 10.0),
                "max_acceleration": mission.constraints.get("max_acceleration_mps2", 5.0),
            },
            "n_episodes": 1,
            "max_steps": 500,
        }
    
    def _get_rrt_config(self, mission: MissionSpec) -> Dict:
        return {
            "algorithm": "RRT*",
            "algorithm_config": {
                "max_iterations": 5000,
                "step_size": 1.0,
                "goal_threshold": 0.5,
                "rewire_radius": 5.0,
            },
            "n_episodes": 1,
            "max_steps": 1000,
        }
    
    def _get_ppo_config(self, mission: MissionSpec) -> Dict:
        return {
            "algorithm": "PPO",
            "algorithm_config": {
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
            },
            "n_episodes": 100,
            "max_steps": 500,
        }
    
    def _get_sac_config(self, mission: MissionSpec) -> Dict:
        return {
            "algorithm": "SAC",
            "algorithm_config": {
                "learning_rate": 3e-4,
                "buffer_size": 100000,
                "batch_size": 256,
                "tau": 0.005,
                "gamma": 0.99,
                "ent_coef": "auto",
            },
            "n_episodes": 100,
            "max_steps": 500,
        }
    
    def _get_hybrid_mpc_rl_config(self, mission: MissionSpec) -> Dict:
        return {
            "algorithm": "Hybrid_MPC_RL",
            "algorithm_config": {
                "mpc_horizon": 15,
                "rl_weight": 0.3,
                "safety_layer": True,
            },
            "n_episodes": 50,
            "max_steps": 500,
        }
    
    def _get_hybrid_rrt_rl_config(self, mission: MissionSpec) -> Dict:
        return {
            "algorithm": "Hybrid_RRT_RL",
            "algorithm_config": {
                "rrt_iterations": 2000,
                "rl_refinement": True,
            },
            "n_episodes": 50,
            "max_steps": 500,
        }
    
    def _build_reward_config(self, mission: MissionSpec) -> Dict[str, float]:
        """Build reward weights from mission objectives."""
        weights = {
            "goal_reward": 100.0,
            "goal_distance_weight": -1.0,
            "velocity_weight": -0.1,
            "acceleration_weight": -0.05,
            "collision_penalty": -50.0,
            "clearance_reward_weight": 2.0,
            "clearance_threshold": mission.minimum_clearance_m,
            "time_penalty": -0.1,
            "action_smoothness_weight": -0.01,
        }
        
        # Adjust weights based on objectives
        for obj, weight in mission.objectives.items():
            if obj == LearningObjective.MINIMIZE_TIME:
                weights["time_penalty"] *= (1 + weight)
            elif obj == LearningObjective.MINIMIZE_ENERGY:
                weights["velocity_weight"] *= (1 + weight)
                weights["acceleration_weight"] *= (1 + weight)
            elif obj == LearningObjective.MINIMIZE_PATH_LENGTH:
                weights["goal_distance_weight"] *= (1 + weight)
            elif obj == LearningObjective.MAXIMIZE_SAFETY:
                weights["collision_penalty"] *= (1 + weight)
                weights["clearance_reward_weight"] *= (1 + weight)
        
        return weights


from typing import List, Dict