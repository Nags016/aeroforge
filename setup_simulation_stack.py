#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
Simulation Stack Setup - Automated PX4/ROS2/Gazebo setup
"""

import subprocess
import time
import sys
from pathlib import Path

def run_cmd(cmd, description, timeout=120):
    """Run a command with description."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"$ {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout.strip():
                print(result.stdout[-500:])
        else:
            print(f"❌ FAILED (exit code: {result.returncode})")
            if result.stderr.strip():
                print(f"STDERR: {result.stderr[-500:]}")
            if result.stdout.strip():
                print(f"STDOUT: {result.stdout[-500:]}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("⏱️ TIMEOUT")
        return False, "", "Timeout"
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False, "", str(e)

def setup_distrobox_ubuntu24():
    """Set up distrobox with Ubuntu 24.04."""
    print("\n📦 Setting up Distrobox Ubuntu 24.04...")
    
    # Check if distrobox exists
    success, _, _ = run_cmd("which distrobox", "Checking distrobox")
    if not success:
        run_cmd("sudo pacman -S --noconfirm distrobox", "Installing distrobox")
    
    # Create ubuntu24 container
    success, _, _ = run_cmd("distrobox list | grep ubuntu24", "Checking ubuntu24 container")
    if not success:
        run_cmd("distrobox create --name ubuntu24 --image ubuntu:24.04 --yes", "Creating ubuntu24 container")
    
    return True

def install_ros2_jazzy():
    """Install ROS 2 Jazzy in distrobox."""
    print("\n🤖 Installing ROS 2 Jazzy...")
    
    # Install dependencies
    cmds = [
        "sudo apt update && sudo apt install -y curl gnupg lsb-release",
        "sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg",
        'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null',
        "sudo apt update",
        "sudo apt install -y ros-jazzy-desktop python3-colcon-common-extensions",
        'echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc',
    ]
    
    for cmd in cmds:
        full_cmd = f"distrobox enter ubuntu24 -- bash -c '{cmd}'"
        success, _, _ = run_cmd(full_cmd, f"ROS 2: {cmd[:50]}...")
        if not success:
            return False
    
    return True

def install_gazebo_harmonic():
    """Install Gazebo Harmonic in distrobox."""
    print("\n🎮 Installing Gazebo Harmonic...")
    
    cmds = [
        "sudo apt update && sudo apt install -y wget lsb-release gnupg",
        "sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg",
        'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null',
        "sudo apt update",
        "sudo apt install -y gz-harmonic",
    ]
    
    for cmd in cmds:
        full_cmd = f"distrobox enter ubuntu24 -- bash -c '{cmd}'"
        success, _, _ = run_cmd(full_cmd, f"Gazebo: {cmd[:50]}...")
        if not success:
            return False
    
    return True

def install_px4_autopilot():
    """Install PX4 Autopilot in distrobox."""
    print("\n✈️ Installing PX4 Autopilot...")
    
    cmds = [
        "cd /home/mr_nags && git clone --recursive https://github.com/PX4/PX4-Autopilot.git -b v1.17.0",
        "cd /home/mr_nags/PX4-Autopilot && bash ./Tools/setup/ubuntu.sh --no-nuttx --no-sim-tools",
    ]
    
    for cmd in cmds:
        full_cmd = f"distrobox enter ubuntu24 -- bash -c '{cmd}'"
        success, _, _ = run_cmd(full_cmd, f"PX4: {cmd[:50]}...", timeout=300)
        if not success:
            return False
    
    return True

def install_micro_ros_agent():
    """Install micro-ROS agent in distrobox."""
    print("\n🔗 Installing micro-ROS Agent...")
    
    cmds = [
        "mkdir -p /tmp/micro-ros-agent && cd /tmp/micro-ros-agent",
        "git clone -b jazzy https://github.com/micro-ROS/micro_ros_agent.git src/micro_ros_agent",
        "cd /tmp/micro-ros-agent && /opt/ros/jazzy/setup.bash && colcon build --symlink-install",
    ]
    
    for cmd in cmds:
        full_cmd = f"distrobox enter ubuntu24 -- bash -c '{cmd}'"
        success, _, _ = run_cmd(full_cmd, f"micro-ROS: {cmd[:50]}...", timeout=300)
        if not success:
            return False
    
    return True

def install_mavlink_router():
    """Install mavlink-router."""
    print("\n📡 Installing MAVLink Router...")
    
    cmds = [
        "sudo apt update && sudo apt install -y git meson ninja-build pkg-config systemd libsystemd-dev",
        "cd /tmp && git clone https://github.com/mavlink-router/mavlink-router.git",
        "cd /tmp/mavlink-router && meson setup build && ninja -C build && sudo ninja -C build install",
    ]
    
    for cmd in cmds:
        full_cmd = f"distrobox enter ubuntu24 -- bash -c '{cmd}'"
        success, _, _ = run_cmd(full_cmd, f"MAVLink Router: {cmd[:50]}...", timeout=300)
        if not success:
            return False
    
    return True

def verify_installation():
    """Verify all components are installed."""
    print("\n✅ Verifying Installation...")
    
    checks = [
        ("distrobox enter ubuntu24 -- bash -c 'source /opt/ros/jazzy/setup.bash && ros2 --version'", "ROS 2 version"),
        ("distrobox enter ubuntu24 -- bash -c 'gz sim --version'", "Gazebo version"),
        ("distrobox enter ubuntu24 -- bash -c 'cd /home/mr_nags/PX4-Autopilot && HEADLESS=1 timeout 30 make px4_sitl none 2>&1 | head -20'", "PX4 build test"),
        ("distrobox enter ubuntu24 -- bash -c 'ls /tmp/micro-ros-agent/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent'", "micro-ROS agent binary"),
    ]
    
    all_passed = True
    for cmd, desc in checks:
        success, stdout, _ = run_cmd(cmd, f"Verify: {desc}", timeout=60)
        if not success:
            all_passed = False
    
    return all_passed

def main():
    """Main setup function."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AeroForge Simulation Stack Setup                                   ║
║     PX4 SITL + Gazebo Harmonic + ROS 2 Jazzy + micro-ROS                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    steps = [
        (setup_distrobox_ubuntu24, "Distrobox Ubuntu 24.04"),
        (install_ros2_jazzy, "ROS 2 Jazzy"),
        (install_gazebo_harmonic, "Gazebo Harmonic"),
        (install_px4_autopilot, "PX4 Autopilot v1.17.0"),
        (install_micro_ros_agent, "micro-ROS Agent"),
        (install_mavlink_router, "MAVLink Router"),
        (verify_installation, "Verification"),
    ]
    
    for func, name in steps:
        print(f"\n{'='*60}")
        print(f"STEP: {name}")
        print(f"{'='*60}")
        
        try:
            success = func()
            if not success:
                print(f"⚠️  {name} had issues, continuing...")
        except Exception as e:
            print(f"❌ {name} failed: {e}")
    
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    print("""
Next steps:
1. Start micro-ROS agent:
   distrobox enter ubuntu24 -- bash -c "
     . /opt/ros/jazzy/setup.bash
     /tmp/micro-ros-agent/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent udp4 -p 8888 -v 4
   "

2. Start PX4 SITL + Gazebo:
   distrobox enter ubuntu24 -- bash -c "
     . /home/mr_nags/ros2_jazzy/install/setup.bash
     cd /home/mr_nags/PX4-Autopilot
     HEADLESS=1 make px4_sitl gz_x500
   "

3. Verify topics:
   distrobox enter ubuntu24 -- bash -c "
     . /home/mr_nags/ros2_jazzy/install/setup.bash
     ros2 topic list | grep fmu
   "
    """)

if __name__ == "__main__":
    main()