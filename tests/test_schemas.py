"""Unit tests for AeroForge schemas and agents"""

import pytest
from agent.schemas import (
    MissionSpec, ExperimentSpec, Metrics, EnvironmentStatus,
    SensorRequirement, ObstacleAvoidancePolicy, StrategyType, ControlLevel,
    LearningObjective, Vector3D
)
from agent.mission_agent import MissionAnalyst


class TestSchemas:
    """Test Pydantic schema validation."""
    
    def test_mission_spec_defaults(self):
        mission = MissionSpec(
            mission_id="test_001",
            start=Vector3D(0, 0, 2),
            goal=Vector3D(10, 10, 2)
        )
        assert mission.mission_id == "test_001"
        assert mission.minimum_clearance_m == 1.5
        assert mission.obstacle_avoidance == ObstacleAvoidancePolicy.REACTIVE_POTENTIAL_FIELD
        assert LearningObjective.BALANCED in mission.objectives
    
    def test_mission_spec_custom(self):
        mission = MissionSpec(
            mission_id="test_002",
            start=Vector3D(0, 0, 1),
            goal=Vector3D(5, 5, 3),
            sensor_requirements=[SensorRequirement.CAMERA, SensorRequirement.DEPTH],
            obstacle_avoidance=ObstacleAvoidancePolicy.LEARNED_POLICY,
            minimum_clearance_m=2.0,
            objectives={LearningObjective.BALANCED: 1.0},
            strategy_preference=StrategyType.RL_PPO
        )
        assert len(mission.sensor_requirements) == 2
        assert mission.obstacle_avoidance == ObstacleAvoidancePolicy.LEARNED_POLICY
        assert mission.strategy_preference == StrategyType.RL_PPO
    
    def test_metrics(self):
        metrics = Metrics(
            success=True,
            collision_count=0,
            goal_error_m=0.3,
            minimum_clearance_m=1.8,
            path_length_m=25.0,
            flight_time_s=15.5,
            smoothness_score=0.9,
            experiment_id="exp_001"
        )
        assert metrics.success is True
        assert metrics.collision_count == 0
    
    def test_environment_status(self):
        env = EnvironmentStatus(
            px4_sitl_available=True,
            gazebo_available=True,
            ros2_available=True,
            camera_available=True,
            depth_camera_available=True,
            micro_ros_agent_running=True,
            px4_version="v1.17.0",
            gazebo_version="8.14.0",
            ros2_distro="jazzy"
        )
        assert env.px4_sitl_available is True
        assert env.gazebo_version == "8.14.0"
        assert env.depth_camera_available is True


class TestMissionAnalyst:
    """Test MissionAnalyst parsing."""
    
    def test_parse_simple_mission(self):
        analyst = MissionAnalyst()
        mission = analyst.parse_mission("Fly from A to B")
        
        assert mission.mission_id == "mission_001"
        assert mission.start.x == 0.0 and mission.start.y == 0.0 and mission.start.z == 2.0
        assert mission.goal.x == 10.0 and mission.goal.y == 10.0 and mission.goal.z == 2.0
    
    def test_parse_camera_mission(self):
        analyst = MissionAnalyst()
        mission = analyst.parse_mission("Fly using camera to avoid obstacles")
        
        assert SensorRequirement.CAMERA in mission.sensor_requirements
        assert mission.obstacle_avoidance == ObstacleAvoidancePolicy.REACTIVE_POTENTIAL_FIELD
    
    def test_parse_clearance(self):
        analyst = MissionAnalyst()
        mission = analyst.parse_mission("Fly with 2m clearance from obstacles")
        
        assert mission.minimum_clearance_m == 2.0
    
    def test_mission_counter_increments(self):
        analyst = MissionAnalyst()
        m1 = analyst.parse_mission("Mission 1")
        m2 = analyst.parse_mission("Mission 2")
        
        assert m1.mission_id == "mission_001"
        assert m2.mission_id == "mission_002"


class TestExperimentSpec:
    """Test ExperimentSpec validation."""
    
    def test_experiment_spec_defaults(self):
        exp = ExperimentSpec(
            experiment_id="exp_001",
            mission_id="mission_001",
            strategy=StrategyType.CLASSICAL_MPC
        )
        assert exp.strategy == StrategyType.CLASSICAL_MPC
        assert exp.control_level == ControlLevel.OFFBOARD_VELOCITY
        assert exp.algorithm == "PPO"
        assert exp.n_episodes == 100


class TestVector3D:
    """Test Vector3D math operations."""
    
    def test_vector_operations(self):
        v1 = Vector3D(1, 2, 3)
        v2 = Vector3D(4, 5, 6)
        
        # Addition
        v3 = v1 + v2
        assert v3.x == 5 and v3.y == 7 and v3.z == 9
        
        # Subtraction
        v4 = v2 - v1
        assert v4.x == 3 and v4.y == 3 and v4.z == 3
        
        # Scalar multiplication
        v5 = v1 * 2.0
        assert v5.x == 2 and v5.y == 4 and v5.z == 6
        
        # Distance
        dist = v1.distance_to(v2)
        assert abs(dist - 5.196) < 0.01  # sqrt(27)
    
    def test_to_numpy(self):
        v = Vector3D(1, 2, 3)
        arr = v.to_numpy()
        assert list(arr) == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])