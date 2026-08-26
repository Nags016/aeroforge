"""AeroForge Main Entry Point - Day 1 Vertical Slice"""

import json
import sys
from agent.mission_agent import MissionAnalyst, get_environment_status, run_baseline_mission
from agent.schemas import MissionSpec, EnvironmentStatus


def main():
    """Run the Day 1 vertical slice: NL → MissionSpec → Baseline Flight → Metrics → Explanation"""
    
    if len(sys.argv) < 2:
        print("Usage: python -m agent.main \"<natural language mission>\"")
        print('Example: python -m agent.main "Fly from A to B using camera to avoid obstacles"')
        return 1
    
    natural_language = " ".join(sys.argv[1:])
    print(f"🎯 Mission: {natural_language}\n")
    
    # Step 1: Mission Analyst - NL to MissionSpec
    print("📋 Step 1: Mission Analyst parsing natural language...")
    analyst = MissionAnalyst()
    mission = analyst.parse_mission(natural_language)
    print(f"   Mission ID: {mission.mission_id}")
    print(f"   Start: {mission.start}")
    print(f"   Goal: {mission.goal}")
    print(f"   Sensors: {[s.value for s in mission.sensor_requirements]}")
    print(f"   Obstacle avoidance: {mission.obstacle_avoidance.value}")
    print(f"   Min clearance: {mission.minimum_clearance_m}m")
    print(f"   Objectives: {mission.objectives}")
    
    # Check for clarifying questions
    questions = analyst.ask_clarifying_questions(mission)
    if questions:
        print("\n❓ Clarifying questions:")
        for q in questions:
            print(f"   - {q}")
        print("   (Proceeding with defaults for Day 1)")
    
    # Step 2: Environment Status
    print("\n🔍 Step 2: Checking environment status...")
    env = get_environment_status()
    print(f"   PX4 SITL: {'✅' if env.px4_sitl_available else '❌'} ({env.px4_version or 'unknown'})")
    print(f"   Gazebo: {'✅' if env.gazebo_available else '❌'} ({env.gazebo_version or 'unknown'})")
    print(f"   ROS 2: {'✅' if env.ros2_available else '❌'} ({env.ros2_distro or 'unknown'})")
    print(f"   Camera: {'✅' if env.camera_available else '❌'}")
    print(f"   micro-ROS Agent: {'✅' if env.micro_ros_agent_running else '❌'}")
    
    if not all([env.px4_sitl_available, env.gazebo_available, env.ros2_available]):
        print("\n❌ Environment not ready - missing components")
        return 1
    
    # Step 3: Run Baseline Mission
    print("\n🚀 Step 3: Running baseline mission...")
    print("   (This starts PX4 SITL + Gazebo headless, may take 30-60s)")
    metrics = run_baseline_mission()
    
    # Step 4: Results
    print("\n📊 Step 4: Mission Results")
    print(f"   Success: {'✅' if metrics['success'] else '❌'}")
    print(f"   Collisions: {metrics['collision_count']}")
    print(f"   Goal Error: {metrics['goal_error_m']}m")
    print(f"   Min Clearance: {metrics['minimum_clearance_m']}m")
    print(f"   Path Length: {metrics['path_length_m']}m")
    print(f"   Flight Time: {metrics['flight_time_s']:.1f}s")
    print(f"   Smoothness: {metrics['smoothness_score']}")
    
    # Step 5: Explanation
    print("\n💡 Step 5: Analysis")
    if metrics['success']:
        print("   The baseline SITL environment is working correctly.")
        print("   PX4 + Gazebo + ROS 2 bridge established.")
        print("   Next: Implement Autonomy Architect for strategy selection.")
    else:
        print("   Baseline mission failed - environment issues detected.")
        print("   Check: micro-ROS agent running, PX4 SITL started, ROS 2 topics visible.")
    
    # Save mission for record
    record = {
        "natural_language": natural_language,
        "mission_spec": mission.model_dump(),
        "environment": env.model_dump(),
        "metrics": metrics
    }
    
    with open("experiments/results/day1_vertical_slice.json", "w") as f:
        json.dump(record, f, indent=2)
    
    print(f"\n💾 Saved experiment record to experiments/results/day1_vertical_slice.json")
    return 0 if metrics['success'] else 1


if __name__ == "__main__":
    sys.exit(main())