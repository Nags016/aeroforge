"""Mission Analyst Agent - interprets natural language to MissionSpec"""

import json
import uuid
from typing import Optional
from agent.schemas import MissionSpec, EnvironmentStatus, SensorRequirement, ObstacleAvoidancePolicy, StrategyType, LearningObjective, Vector3D


class MissionAnalyst:
    """Converts natural language missions to structured MissionSpec."""
    
    def __init__(self):
        self.mission_counter = 0
    
    def parse_mission(self, natural_language: str, env_status: Optional[EnvironmentStatus] = None) -> MissionSpec:
        """Parse natural language into MissionSpec.
        
        In production, this would use Gemini/ADK. For Day 1, we use rule-based parsing.
        """
        self.mission_counter += 1
        mission_id = f"mission_{self.mission_counter:03d}"
        
        # Simple keyword extraction for Day 1
        nl_lower = natural_language.lower()
        
        # Extract positions (simplified - in reality would use NLP)
        start = Vector3D(x=0.0, y=0.0, z=2.0)  # default
        goal = Vector3D(x=10.0, y=10.0, z=2.0)  # default
        
        # Determine sensor requirements
        sensors = [SensorRequirement.GPS, SensorRequirement.IMU]
        if "camera" in nl_lower:
            sensors.append(SensorRequirement.CAMERA)
        if "depth" in nl_lower:
            sensors.append(SensorRequirement.DEPTH)
        if "lidar" in nl_lower:
            sensors.append(SensorRequirement.LIDAR)
        
        # Determine obstacle avoidance
        if "avoid" in nl_lower or "obstacle" in nl_lower:
            avoidance = ObstacleAvoidancePolicy.REACTIVE_POTENTIAL_FIELD
        else:
            avoidance = ObstacleAvoidancePolicy.NONE
        
        # Minimum clearance
        clearance = 1.5
        if "1.5" in nl_lower or "1.5m" in nl_lower:
            clearance = 1.5
        elif "2" in nl_lower or "2m" in nl_lower:
            clearance = 2.0
        elif "3" in nl_lower or "3m" in nl_lower:
            clearance = 3.0
        
        # Objectives with weights
        objectives = {LearningObjective.BALANCED: 1.0}
        
        # Constraints
        constraints = {}
        if "time" in nl_lower:
            constraints["max_flight_time_s"] = 60.0
        
        return MissionSpec(
            mission_id=mission_id,
            start=start,
            goal=goal,
            sensor_requirements=sensors,
            obstacle_avoidance=avoidance,
            minimum_clearance_m=clearance,
            objectives={LearningObjective.BALANCED: 1.0},
            constraints=constraints,
            acceptance_criteria={
                "max_collisions": 0,
                "max_goal_error_m": 1.0,
                "min_clearance_m": clearance,
                "max_flight_time_s": constraints.get("max_flight_time_s", 60.0)
            }
        )
    
    def ask_clarifying_questions(self, mission: MissionSpec) -> list[str]:
        """Generate clarifying questions if mission is ambiguous."""
        questions = []
        
        if not mission.sensor_requirements:
            questions.append("What sensors should be used? (camera, depth, lidar, GPS)")
        
        if mission.obstacle_avoidance == ObstacleAvoidancePolicy.NONE:
            questions.append("Should the drone avoid obstacles?")
        
        if mission.minimum_clearance_m == 1.5:
            questions.append("Is 1.5m minimum clearance acceptable?")
        
        return questions


def get_environment_status() -> EnvironmentStatus:
    """Tool: Get current simulation environment status."""
    from tools.simulation import get_environment_status as _get_status
    return _get_status()


def run_baseline_mission() -> dict:
    """Tool: Run the validated baseline mission and return metrics."""
    from tools.simulation import run_baseline_mission as _run_baseline
    result = _run_baseline()
    return result.metrics.model_dump()


if __name__ == "__main__":
    # Quick test
    analyst = MissionAnalyst()
    
    # Test mission
    nl = "Fly from A to B using the camera to avoid obstacles with 1.5m clearance"
    mission = analyst.parse_mission(nl)
    
    print("MissionSpec:")
    print(json.dumps(mission.model_dump(), indent=2))
    
    questions = analyst.ask_clarifying_questions(mission)
    if questions:
        print("\nClarifying questions:")
        for q in questions:
            print(f"  - {q}")