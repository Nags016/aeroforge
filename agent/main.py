"""AeroForge Main Entry Point - Full Agent Pipeline with Crash Recovery"""

import json
import sys
import time
import asyncio
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, '/home/mr_nags/aeroforge')

from agent.mission_agent import MissionAnalyst, get_environment_status, run_baseline_mission
from agent.architect_agent import AutonomyArchitect
from agent.experiment_agent import ExperimentEngineer
from agent.verifier_agent import VerifierAgent
from agent.crash_analyzer import AutoCrashRecovery, run_with_crash_recovery
from agent.schemas import (
    MissionSpec, EnvironmentStatus, ExperimentSpec, Metrics, 
    LearningState, StrategyType
)


def main():
    """Run the full agent pipeline: NL → MissionSpec → Strategy → Experiment → Verify → Execute"""
    
    if len(sys.argv) < 2:
        print("Usage: python -m agent.main \"<natural language mission>\"")
        print('Example: python -m agent.main "Fly from A to B using camera to avoid obstacles"')
        return 1
    
    natural_language = " ".join(sys.argv[1:])
    print(f"🎯 Mission: {natural_language}\n")
    
    # Initialize agents
    analyst = MissionAnalyst()
    architect = AutonomyArchitect()
    engineer = ExperimentEngineer()
    verifier = VerifierAgent()
    crash_recovery = AutoCrashRecovery()
    
    # ============================================
    # STEP 1: Mission Analyst - NL → MissionSpec
    # ============================================
    print("📋 Step 1: Mission Analyst parsing natural language...")
    mission = analyst.parse_mission(natural_language)
    print(f"   Mission ID: {mission.mission_id}")
    print(f"   Start: ({mission.start.x:.1f}, {mission.start.y:.1f}, {mission.start.z:.1f})")
    print(f"   Goal: ({mission.goal.x:.1f}, {mission.goal.y:.1f}, {mission.goal.z:.1f})")
    print(f"   Sensors: {[s.value for s in mission.sensor_requirements]}")
    print(f"   Obstacle avoidance: {mission.obstacle_avoidance.value}")
    print(f"   Min clearance: {mission.minimum_clearance_m}m")
    print(f"   Objectives: {[f'{k.value}:{v:.1f}' for k,v in mission.objectives.items()]}")
    
    # Check for clarifying questions
    questions = analyst.ask_clarifying_questions(mission)
    if questions:
        print("\n❓ Clarifying questions:")
        for q in questions:
            print(f"   - {q}")
        print("   (Proceeding with defaults for autonomous execution)")
    
    # ============================================
    # STEP 2: Environment Status
    # ============================================
    print("\n🔍 Step 2: Checking environment status...")
    env = get_environment_status()
    print(f"   PX4 SITL: {'✅' if env.px4_sitl_available else '❌'} ({env.px4_version or 'unknown'})")
    print(f"   Gazebo: {'✅' if env.gazebo_available else '❌'} ({env.gazebo_version or 'unknown'})")
    print(f"   ROS 2: {'✅' if env.ros2_available else '❌'} ({env.ros2_distro or 'unknown'})")
    print(f"   Camera: {'✅' if env.camera_available else '❌'}")
    print(f"   Depth Camera: {'✅' if env.depth_camera_available else '❌'}")
    print(f"   micro-ROS Agent: {'✅' if env.micro_ros_agent_running else '❌'}")
    print(f"   Compute: CPU={'✅' if env.compute_available.get('cpu') else '❌'} "
          f"CUDA={'✅' if env.compute_available.get('cuda') else '❌'} "
          f"MPS={'✅' if env.compute_available.get('mps') else '❌'}")
    
    if not env.px4_sitl_available:
        print("\n❌ PX4 SITL not available - cannot proceed")
        return 1
    
    # ============================================
    # STEP 3: Autonomy Architect - Strategy Selection
    # ============================================
    print("\n🧠 Step 3: Autonomy Architect selecting strategy...")
    experiment_spec = architect.select_strategy(mission, env)
    print(f"   Selected Strategy: {experiment_spec.strategy.value}")
    print(f"   Control Level: {experiment_spec.control_level.value}")
    print(f"   Algorithm: {experiment_spec.algorithm}")
    print(f"   Episodes: {experiment_spec.n_episodes}")
    print(f"   Max Steps/Episode: {experiment_spec.max_steps_per_episode}")
    
    # Show strategy scoring rationale
    print(f"   Reward Weights: goal={experiment_spec.reward_config['goal_reward']:.0f}, "
          f"collision={experiment_spec.reward_config['collision_penalty']:.0f}, "
          f"clearance={experiment_spec.reward_config['clearance_reward_weight']:.1f}, "
          f"time={experiment_spec.reward_config['time_penalty']:.2f}")
    
    # ============================================
    # STEP 4: Experiment Engineer - Run Experiment Cycle with Crash Recovery
    # ============================================
    print("\n🔬 Step 4: Experiment Engineer running experiment cycle with crash recovery...")
    print(f"   Max iterations: 10")
    
    # Initialize learning state
    learning_state = LearningState(mission_id=mission.mission_id)
    
    # Run experiment cycle with crash recovery
    start_time = time.time()
    
    # Run with crash recovery
    crash_results = asyncio.run(run_with_crash_recovery(
        mission, experiment_spec, env, api_key=None
    ))
    
    cycle_time = time.time() - start_time
    
    print(f"\n⏱️  Experiment cycle completed in {cycle_time:.1f}s")
    
    if crash_results["recovered"]:
        print(f"✅ Crash recovery successful!")
        print(f"   Attempts: {len(crash_results['attempts'])}")
        final_metrics = crash_results["final_metrics"]
    else:
        print(f"❌ Crash recovery failed after {len(crash_results['attempts'])} attempts")
        # Fallback to regular experiment cycle
        learning_state = LearningState(mission_id=mission.mission_id)
        start_time = time.time()
        final_learning_state = engineer.run_experiment_cycle(
            mission, experiment_spec, env, learning_state
        )
        cycle_time = time.time() - start_time
        final_metrics = final_learning_state.best_metrics
    
    print(f"\n⏱️  Experiment cycle completed in {cycle_time:.1f}s")
    
    if final_metrics:
        print(f"\n🏆 Best Result:")
        print(f"   Success: {'✅' if final_metrics.success else '❌'}")
        print(f"   Collisions: {final_metrics.collision_count}")
        print(f"   Goal Error: {final_metrics.goal_error_m:.2f}m")
        print(f"   Min Clearance: {final_metrics.minimum_clearance_m:.2f}m")
        print(f"   Mean Clearance: {final_metrics.mean_clearance_m:.2f}m")
        print(f"   Path Length: {final_metrics.path_length_m:.2f}m")
        print(f"   Flight Time: {final_metrics.flight_time_s:.1f}s")
        print(f"   Smoothness: {final_metrics.smoothness_score:.2f}")
        print(f"   Energy: {final_metrics.energy_consumption:.1f}")
    
    # ============================================
    # STEP 5: Verifier Agent - Independent Validation
    # ============================================
    print("\n🔍 Step 5: Verifier Agent validating results...")
    verification = None
    if final_metrics:
        verification = verifier.verify(
            mission, 
            experiment_spec, 
            final_metrics
        )
        print(f"   Passed: {'✅' if verification.passed else '❌'}")
        print(f"   Confidence: {verification.confidence:.0%}")
        print(f"   Score: {verification.score:.2f}")
        
        if verification.issues:
            print("   Issues:")
            for issue in verification.issues:
                print(f"   ⚠️  {issue}")
        
        if verification.recommendations:
            print("   Recommendations:")
            for rec in verification.recommendations:
                print(f"   💡 {rec}")
    
    # ============================================
    # STEP 6: Execute Final Validated Mission
    # ============================================
    print("\n🚀 Step 6: Executing final validated mission...")
    final_metrics = run_baseline_mission()
    
    print(f"\n📊 Final Mission Results:")
    print(f"   Success: {'✅' if final_metrics['success'] else '❌'}")
    print(f"   Collisions: {final_metrics['collision_count']}")
    print(f"   Goal Error: {final_metrics['goal_error_m']}m")
    print(f"   Min Clearance: {final_metrics['minimum_clearance_m']}m")
    print(f"   Mean Clearance: {final_metrics['mean_clearance_m']}m")
    print(f"   Path Length: {final_metrics['path_length_m']}m")
    print(f"   Flight Time: {final_metrics['flight_time_s']:.1f}s")
    print(f"   Smoothness: {final_metrics['smoothness_score']}")
    print(f"   Energy: {final_metrics['energy_consumption']}")
    
    # ============================================
    # STEP 6: Save Complete Record
    # ============================================
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "natural_language": natural_language,
        "mission_spec": mission.model_dump(),
        "environment": env.model_dump(),
        "experiment_spec": experiment_spec.model_dump(),
        "verification": verification.__dict__ if verification else None,
        "final_metrics": final_metrics,
        "total_time_s": time.time() - start_time,
    }
    
    output_dir = Path("experiments/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = Path("experiments/results") / f"mission_{mission.mission_id}_full.json"
    
    with open(output_file, "w") as f:
        json.dump(record, f, indent=2, default=str)
    
    print(f"\n💾 Complete mission record saved to {output_file}")
    
    return 0 if final_metrics.get('success', False) else 1


if __name__ == "__main__":
    start_time = time.time()
    sys.exit(main())