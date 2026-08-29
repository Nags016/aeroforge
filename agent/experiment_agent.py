"""Experiment Engineer Agent - executes experiments, trains, evaluates, iterates"""

import time
import random
import json
import os
import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path

from agent.schemas import (
    ExperimentSpec, Metrics, MissionSpec, LearningState,
    StrategyType, ObstacleAvoidancePolicy
)
from tools.simulation import run_baseline_mission, get_environment_status
from agent.schemas import EnvironmentStatus

try:
    from stable_baselines3 import PPO, SAC
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


class ExperimentEngineer:
    """Executes experiments, trains policies, evaluates results, iterates on parameters."""

    def __init__(self, workspace: str = "/home/mr_nags/aeroforge/experiments"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.learning_state = LearningState(mission_id="")
        self.max_iterations = 20

    def run_experiment_cycle(self, mission: MissionSpec, experiment_spec: ExperimentSpec,
                              env: EnvironmentStatus, learning_state: Optional[LearningState] = None) -> LearningState:
        """Run full experiment cycle: generate → train → evaluate → iterate."""

        if learning_state:
            self.learning_state = learning_state
        self.learning_state.mission_id = experiment_spec.mission_id

        print(f"🔬 Starting experiment cycle for mission {experiment_spec.mission_id}")
        print(f"   Strategy: {experiment_spec.strategy.value}")
        print(f"   Algorithm: {experiment_spec.algorithm}")

        for iteration in range(self.max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}/{self.max_iterations}")

            # 1. Run experiment (simulation or training)
            metrics = self._run_experiment(experiment_spec, iteration)

            # 2. Evaluate metrics
            passed, feedback = self._evaluate(metrics, experiment_spec)

            # 3. Update learning state
            self.learning_state.update_from_experiment(
                self._create_experiment_spec_with_iteration(experiment_spec, iteration),
                metrics
            )

            print(f"   Metrics: success={metrics.success}, collisions={metrics.collision_count}, "
                  f"goal_error={metrics.goal_error_m:.2f}m, clearance={metrics.minimum_clearance_m:.2f}m")
            print(f"   Result: {'✅ PASS' if passed else '❌ FAIL'} - {feedback}")

            if passed:
                print(f"✅ Experiment PASSED on iteration {iteration + 1}!")
                self.learning_state.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
                return self.learning_state

            # 4. Diagnose and mutate parameters
            if iteration < self.max_iterations - 1:
                experiment_spec = self._mutate_parameters(experiment_spec, metrics, feedback)
                print(f"   🔧 Mutated parameters for next iteration")

        print(f"❌ Experiment FAILED after {self.max_iterations} iterations")
        self.learning_state.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        return self.learning_state

    def _run_experiment(self, experiment_spec: ExperimentSpec, iteration: int) -> "Metrics":
        """Run a single experiment iteration."""

        # For dev mode, use mock simulation with strategy-specific behavior
        import random

        # Base metrics with strategy-specific variations
        if "RL" in experiment_spec.strategy.value:
            # RL strategies improve over iterations
            improvement = min(0.3, iteration * 0.05)
            base_success = 0.5 + improvement
            base_clearance = 1.5 + iteration * 0.1
            base_error = max(0.1, 0.5 - iteration * 0.03)
        elif "HYBRID" in experiment_spec.strategy.value:
            # Hybrid improves faster
            improvement = min(0.4, iteration * 0.08)
            base_success = 0.6 + improvement
            base_clearance = 1.8 + iteration * 0.15
            base_error = max(0.05, 0.3 - iteration * 0.04)
        else:
            # Classical methods - consistent but limited
            base_success = 0.9
            base_clearance = 2.0
            base_error = 0.2

        # Add noise
        success = random.random() < base_success
        collision_count = 0 if success else random.randint(1, 3)
        goal_error = max(0.05, base_error + random.uniform(-0.05, 0.05))
        clearance = max(0.5, base_clearance + random.uniform(-0.2, 0.3))

        from agent.schemas import Metrics
        return Metrics(
            success=success,
            collision_count=collision_count,
            goal_error_m=round(goal_error, 2),
            minimum_clearance_m=round(max(0.1, clearance - random.uniform(0, 0.5)), 2),
            mean_clearance_m=round(base_clearance + random.uniform(0, 0.5), 2),
            path_length_m=round(random.uniform(15, 30), 2),
            flight_time_s=round(random.uniform(10, 40), 2),
            smoothness_score=round(random.uniform(0.7, 0.95), 2),
            energy_consumption=round(random.uniform(50, 150), 2),
            experiment_id=f"{experiment_spec.experiment_id}_iter{iteration}",
            n_episodes=1,
            success_rate=1.0 if success else 0.0,
            std_goal_error_m=round(random.uniform(0.05, 0.15), 2),
            std_clearance_m=round(random.uniform(0.1, 0.3), 2),
        )

    def _evaluate(self, metrics: "Metrics", experiment_spec: "ExperimentSpec") -> tuple[bool, str]:
        """Evaluate metrics against acceptance thresholds."""
        thresholds = experiment_spec.success_thresholds

        checks = []

        # Collision rate
        collision_rate = 0.0 if metrics.collision_count == 0 else 1.0
        if collision_rate <= thresholds.get("collision_rate", 0.0):
            checks.append(("collision_rate", True, f"collision_rate={collision_rate}"))
        else:
            checks.append(("collision_rate", False, f"collision_rate={collision_rate} > {thresholds.get('collision_rate', 0)}"))

        # Goal reach rate
        goal_reach = 1.0 if metrics.success else 0.0
        if goal_reach >= thresholds.get("goal_reach_rate", 0.8):
            checks.append(("goal_reach_rate", True, f"goal_reach_rate={goal_reach}"))
        else:
            checks.append(("goal_reach_rate", False, f"goal_reach_rate={goal_reach} < {thresholds.get('goal_reach_rate', 0.8)}"))

        # Clearance
        if metrics.mean_clearance_m >= thresholds.get("avg_clearance_m", 1.5):
            checks.append(("clearance", True, f"clearance={metrics.mean_clearance_m:.2f}m"))
        else:
            checks.append(("clearance", False, f"clearance={metrics.mean_clearance_m:.2f}m < {thresholds.get('avg_clearance_m', 1.5)}"))

        # Flight time
        if metrics.flight_time_s <= thresholds.get("avg_flight_time_s", 60):
            checks.append(("flight_time", True, f"flight_time={metrics.flight_time_s:.1f}s"))
        else:
            checks.append(("flight_time", False, f"flight_time={metrics.flight_time_s:.1f}s > {thresholds.get('avg_flight_time_s', 60)}"))

        all_passed = all(passed for _, passed, _ in checks)
        feedback = "; ".join([msg for _, passed, msg in checks if not passed]) or "All thresholds met"

        return all_passed, feedback

    def _mutate_parameters(self, experiment_spec: "ExperimentSpec", metrics: "Metrics", feedback: str) -> "ExperimentSpec":
        """Mutate experiment parameters based on failure analysis."""
        import copy
        import random

        new_spec = copy.deepcopy(experiment_spec)

        # Analyze failure and mutate accordingly
        if metrics.collision_count > 0:
            # Increase collision penalty, decrease max velocity
            new_spec.reward_config["collision_penalty"] *= 1.5
            new_spec.algorithm_config["max_velocity"] = max(2.0,
                new_spec.algorithm_config.get("max_velocity", 10.0) * 0.9)
            print(f"   🔧 Increased collision penalty, reduced max velocity")

        if metrics.goal_error_m > 1.0:
            # Increase goal reward, increase goal distance weight
            new_spec.reward_config["goal_reward"] *= 1.3
            new_spec.reward_config["goal_distance_weight"] *= 1.2
            print(f"   🔧 Increased goal reward weight")

        if metrics.minimum_clearance_m < 1.5:
            # Increase clearance reward, increase threshold
            new_spec.reward_config["clearance_reward_weight"] *= 1.5
            new_spec.reward_config["clearance_threshold"] = min(3.0,
                new_spec.reward_config.get("clearance_threshold", 1.5) * 1.2)
            print(f"   🔧 Increased clearance reward weight")

        if metrics.flight_time_s > 60:
            # Increase time penalty
            new_spec.reward_config["time_penalty"] *= 1.3
            print(f"   🔧 Increased time penalty")

        # Add small random perturbations to escape local minima
        for key in ["learning_rate", "ent_coef", "clip_range"]:
            if key in new_spec.algorithm_config:
                new_spec.algorithm_config[key] *= random.uniform(0.9, 1.1)

        return new_spec

    def _create_experiment_spec_with_iteration(self, experiment_spec: "ExperimentSpec", iteration: int):
        """Create a copy of experiment spec with iteration info."""
        import copy
        new_spec = copy.deepcopy(experiment_spec)
        new_spec.experiment_id = f"{experiment_spec.experiment_id}_iter{iteration}"
        return new_spec

    def load_trained_policy(self, policy_path: str, algorithm: str = "PPO"):
        """Load a trained RL policy for evaluation."""
        if not SB3_AVAILABLE:
            raise ImportError("stable-baselines3 not installed")

        if algorithm.upper() == "PPO":
            model = PPO.load(policy_path)
        elif algorithm.upper() == "SAC":
            model = SAC.load(policy_path)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        print(f"✅ Loaded trained {algorithm} policy from {policy_path}")
        return model

    def evaluate_policy(self, model, experiment_spec: ExperimentSpec, n_episodes: int = 10) -> Metrics:
        """Evaluate a trained policy in the environment."""
        from train_rl import make_env

        # Create eval env
        config = {
            'max_steps': experiment_spec.max_steps_per_episode,
            'world_size': 50.0,
            'num_obstacles': experiment_spec.obstacle_config.get('num_obstacles', 10),
            'goal_threshold': 1.0,
            'collision_penalty': experiment_spec.reward_config.get('collision_penalty', -50.0),
            'goal_reward': experiment_spec.reward_config.get('goal_reward', 100.0),
            'time_penalty': experiment_spec.reward_config.get('time_penalty', -0.1),
            'clearance_reward': experiment_spec.reward_config.get('clearance_reward_weight', 2.0),
            'clearance_threshold': experiment_spec.reward_config.get('clearance_threshold', 2.0),
            'action_smoothness_weight': experiment_spec.reward_config.get('action_smoothness_weight', -0.01),
        }

        eval_env = make_env(config)()

        # Run evaluation episodes
        episode_rewards = []
        episode_lengths = []
        successes = 0
        collisions = 0
        goal_errors = []
        clearances = []
        path_lengths = []
        flight_times = []
        smoothness = []
        energy = []

        for ep in range(n_episodes):
            obs, _ = eval_env.reset()
            done = False
            ep_reward = 0
            ep_len = 0
            ep_collisions = 0
            ep_min_clearance = float('inf')
            ep_path_length = 0.0

            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = eval_env.step(action)
                done = terminated or truncated
                ep_reward += reward
                ep_len += 1

                if hasattr(eval_env, 'collisions'):
                    ep_collisions = eval_env.collisions
                if hasattr(eval_env, 'min_clearance'):
                    ep_min_clearance = min(ep_min_clearance, eval_env.min_clearance)
                if hasattr(eval_env, 'path_length'):
                    ep_path_length = eval_env.path_length

            episode_rewards.append(ep_reward)
            episode_lengths.append(ep_len)
            if ep_collisions == 0 and info.get('goal_distance', 100) < 1.0:
                successes += 1
            collisions += ep_collisions
            goal_errors.append(info.get('goal_distance', 0))
            clearances.append(ep_min_clearance if ep_min_clearance != float('inf') else 0)
            path_lengths.append(ep_path_length)
            flight_times.append(ep_len * 0.1)  # dt = 0.1
            smoothness.append(0.8)  # placeholder
            energy.append(100.0)  # placeholder

        # Aggregate metrics
        return Metrics(
            success=successes / n_episodes >= 0.8,
            collision_count=collisions // n_episodes,
            goal_error_m=sum(goal_errors) / len(goal_errors),
            minimum_clearance_m=min(clearances) if clearances else 0,
            mean_clearance_m=sum(clearances) / len(clearances) if clearances else 0,
            path_length_m=sum(path_lengths) / len(path_lengths),
            flight_time_s=sum(flight_times) / len(flight_times),
            smoothness_score=sum(smoothness) / len(smoothness),
            energy_consumption=sum(energy) / len(energy),
            experiment_id=experiment_spec.experiment_id + "_eval",
            n_episodes=n_episodes,
            success_rate=successes / n_episodes,
            std_goal_error_m=float(np.std(goal_errors)) if len(goal_errors) > 1 else 0,
            std_clearance_m=float(np.std(clearances)) if len(clearances) > 1 else 0,
        )


# For importing
def run_experiment_cycle(mission, experiment_spec, env, learning_state=None):
    """Convenience function to run experiment cycle."""
    engineer = ExperimentEngineer()
    return engineer.run_experiment_cycle(mission, experiment_spec, env, learning_state)