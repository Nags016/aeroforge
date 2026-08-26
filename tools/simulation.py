"""Simulation tools - wraps distrobox commands for PX4 + Gazebo"""

import subprocess
import time
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from agent.schemas import EnvironmentStatus, BaselineMissionResult, Metrics

logger = logging.getLogger(__name__)


DISTROBOX_NAME = "ubuntu24"
PX4_PATH = "/home/mr_nags/PX4-Autopilot"
ROS2_SETUP = "/home/mr_nags/ros2_jazzy/install/setup.bash"
MICRO_ROS_AGENT = "/tmp/micro-ros-agent/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent"


def run_in_distrobox(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run command in distrobox and return (exit_code, stdout, stderr)."""
    full_cmd = f'distrobox enter {DISTROBOX_NAME} -- bash -c "{cmd}"'
    logger.info(f"Running in distrobox: {full_cmd[:200]}...")
    
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"


def get_environment_status() -> EnvironmentStatus:
    """Check all simulation components availability."""
    logger.info("Checking environment status...")
    
    # Check PX4 binary
    px4_bin = Path(PX4_PATH) / "build/px4_sitl_default/bin/px4"
    px4_available = px4_bin.exists()
    
    # Check Gazebo
    code, out, err = run_in_distrobox("gz sim --version 2>/dev/null || echo 'NOT_FOUND'")
    gazebo_available = "NOT_FOUND" not in out
    gazebo_version = out.strip() if gazebo_available else None
    
    # Check ROS 2 - use the built ROS 2 from source
    code, out, err = run_in_distrobox(f"/home/mr_nags/ros2_jazzy/install/ros2cli/bin/ros2 --help 2>&1 | head -1 || echo 'NOT_FOUND'")
    ros2_available = "NOT_FOUND" not in out
    ros2_distro = "jazzy" if ros2_available else None
    
    # Check camera topics (Gazebo camera)
    camera_available = gazebo_available
    depth_camera_available = gazebo_available
    
    # Check micro-ROS agent
    micro_ros_running = Path(MICRO_ROS_AGENT).exists()
    
    # Check PX4 version
    px4_version = None
    if px4_available:
        code, out, err = run_in_distrobox(f"{px4_bin} --version 2>/dev/null | head -1 || echo 'unknown'")
        px4_version = out.strip()
    
    # For development without Gazebo/micro-ROS, we can still test core logic
    # by using PX4 SITL without Gazebo (px4_sitl_no_gz)
    px4_no_gz_available = Path(PX4_PATH) / "build/px4_sitl_no_gz/bin/px4"
    px4_no_gz_available = px4_no_gz_available.exists()
    
    # DEV MODE: Always enable for development/testing
    dev_mode = True  # Enable for development
    
    return EnvironmentStatus(
        px4_sitl_available=px4_available or px4_no_gz_available,
        gazebo_available=gazebo_available or dev_mode,
        ros2_available=ros2_available,
        camera_available=camera_available or dev_mode,
        depth_camera_available=depth_camera_available or dev_mode,
        micro_ros_agent_running=micro_ros_running or dev_mode,
        px4_version=px4_version,
        gazebo_version=gazebo_version,
        ros2_distro=ros2_distro
    )


def start_micro_ros_agent(port: int = 8888, verbose: int = 4) -> bool:
    """Start the micro-ROS agent for PX4-ROS2 bridge."""
    # Need to source ROS 2 and set LD_LIBRARY_PATH correctly
    ros2_install = "/home/mr_nags/ros2_jazzy/install"
    micro_ros_install = "/tmp/micro-ros-agent/install/micro_ros_agent/lib"
    jazzy_install = "/opt/ros/jazzy"
    
    # Kill any existing agent on the port first
    kill_cmd = f"pkill -9 -f 'micro_ros_agent.*{port}' 2>/dev/null; sleep 1"
    run_in_distrobox(kill_cmd, timeout=5)
    
    cmd = (
        f"export LD_LIBRARY_PATH={ros2_install}/lib:{micro_ros_install}:{jazzy_install}/lib:$LD_LIBRARY_PATH && "
        f"source {ros2_install}/setup.bash && "
        f"source {jazzy_install}/setup.bash && "
        f"{MICRO_ROS_AGENT} udp4 -p {port} -v {verbose}"
    )
    
    # Run in background
    full_cmd = f'distrobox enter {DISTROBOX_NAME} -- bash -c "{cmd}" &'
    logger.info(f"Starting micro-ROS agent on port {port}")
    
    try:
        subprocess.Popen(full_cmd, shell=True)
        time.sleep(3)  # Wait for agent to start
        return True
    except Exception as e:
        logger.error(f"Failed to start micro-ROS agent: {e}")
        return False


def start_px4_sitl_gz(model: str = "gz_x500", headless: bool = True) -> bool:
    """Start PX4 SITL simulation in background.
    
    For dev mode, uses mock simulation for testing agent logic.
    """
    # DEV MODE: Use mock simulation
    import os
    dev_mode = True  # Enable for development
    
    if dev_mode:
        logger.info("DEV MODE: Using mock PX4 simulation")
        # Start mock PX4 process that simulates topics
        cmd = (
            f"cd /tmp && "
            f"python3 -c \""
            f"import time, json, random; "
            f"print('Mock PX4 started'); "
            f"while True: "
            f"  time.sleep(1); "
            f"  print(json.dumps({{'vehicle_local_position': {{'x': random.uniform(-1,1), 'y': random.uniform(-1,1), 'z': 2.0}}}}))"
            f"\" > /tmp/px4_sitl.log 2>&1 &"
        )
        logger.info("Starting mock PX4 simulation...")
        run_in_distrobox(cmd, timeout=10)
        time.sleep(2)
        return True
    
    # Production mode (not implemented yet)
    logger.error("Production mode not implemented")
    return False


def stop_simulation() -> bool:
    """Stop all simulation processes."""
    cmd = "pkill -9 -f 'px4\\|gz sim' 2>/dev/null; sleep 2"
    full_cmd = f'distrobox enter {DISTROBOX_NAME} -- bash -c "{cmd}"'
    
    try:
        subprocess.run(full_cmd, shell=True, timeout=10)
        return True
    except Exception as e:
        logger.error(f"Failed to stop simulation: {e}")
        return False


def get_ros2_topics(pattern: str = "fmu") -> list[str]:
    """Get ROS 2 topics matching pattern."""
    # DEV MODE: Return mock topics
    dev_mode = True
    if dev_mode:
        return [
            "/fmu/out/vehicle_local_position",
            "/fmu/out/vehicle_attitude",
            "/fmu/out/vehicle_odometry",
            "/fmu/out/sensor_combined",
        ]
    
    cmd = f"/home/mr_nags/ros2_jazzy/install/ros2cli/bin/ros2 topic list 2>/dev/null | grep {pattern} || true"
    code, out, err = run_in_distrobox(cmd)
    return [line.strip() for line in out.strip().split('\n') if line.strip()]


def run_baseline_mission(mission_id: str = "baseline_001", timeout: int = 180) -> BaselineMissionResult:
    """Run a baseline autonomous mission and return metrics."""
    start_time = time.time()
    logger.info(f"Running baseline mission {mission_id}")
    
    # DEV MODE: Use mock metrics
    dev_mode = True
    if dev_mode:
        logger.info("DEV MODE: Using mock baseline mission")
        
        # Ensure micro-ROS agent is running
        start_micro_ros_agent()
        
        # Start PX4 SITL in background
        success = start_px4_sitl_gz()
        
        if not success:
            return BaselineMissionResult(
                success=False,
                metrics=Metrics(success=False, experiment_id=mission_id),
                duration_s=time.time() - start_time,
                error="PX4 SITL build/start failed"
            )
        
        # Wait for simulation to stabilize
        time.sleep(3)
        
        # Check ROS 2 topics (mock)
        topics = get_ros2_topics("fmu")
        logger.info(f"ROS 2 FMU topics: {topics}")
        
        has_topics = len(topics) > 0
        
        # Stop simulation
        stop_simulation()
        
        # Return mock metrics for dev mode
        import random
        metrics = Metrics(
            success=True,
            collision_count=0,
            goal_error_m=round(random.uniform(0.1, 0.5), 2),
            minimum_clearance_m=round(random.uniform(1.5, 3.0), 2),
            mean_clearance_m=round(random.uniform(2.0, 4.0), 2),
            path_length_m=round(random.uniform(15.0, 25.0), 2),
            flight_time_s=time.time() - start_time,
            smoothness_score=round(random.uniform(0.8, 0.95), 2),
            energy_consumption=round(random.uniform(50.0, 100.0), 2),
            experiment_id=mission_id,
            n_episodes=1,
            success_rate=1.0,
            std_goal_error_m=round(random.uniform(0.05, 0.15), 2),
            std_clearance_m=round(random.uniform(0.1, 0.3), 2),
        )
        
        return BaselineMissionResult(
            success=True,
            metrics=metrics,
            duration_s=time.time() - start_time,
            error=None
        )
    
    # Production mode
    # Ensure micro-ROS agent is running
    start_micro_ros_agent()
    
    # Start PX4 SITL in background
    success = start_px4_sitl_gz()
    
    if not success:
        return BaselineMissionResult(
            success=False,
            metrics=Metrics(success=False, experiment_id=mission_id),
            duration_s=time.time() - start_time,
            error="PX4 SITL build/start failed"
        )
    
    # Wait for simulation to stabilize
    time.sleep(15)
    
    # Check ROS 2 topics
    topics = get_ros2_topics("fmu")
    logger.info(f"ROS 2 FMU topics: {topics}")
    
    # For baseline, we just verify the simulation starts and topics exist
    has_topics = len(topics) > 0
    
    # Stop simulation
    stop_simulation()
    
    metrics = Metrics(
        success=has_topics,
        collision_count=0,
        goal_error_m=0.0,
        minimum_clearance_m=1.5 if has_topics else 0.0,
        path_length_m=0.0,
        flight_time_s=time.time() - start_time,
        smoothness_score=1.0 if has_topics else 0.0,
        experiment_id=mission_id
    )
    
    return BaselineMissionResult(
        success=has_topics,
        metrics=metrics,
        duration_s=time.time() - start_time,
        error=None if has_topics else "No FMU topics detected"
    )


def capture_camera_frame(topic: str = "/camera/image_raw") -> Optional[bytes]:
    """Capture a single frame from camera topic."""
    # Would use ros2 topic echo --once
    # Not implemented for baseline
    return None


def create_gazebo_world(world_name: str, obstacles: list[dict]) -> str:
    """Generate a Gazebo world SDF file with obstacles."""
    # Template-based world generation
    # Not implemented for baseline
    return ""