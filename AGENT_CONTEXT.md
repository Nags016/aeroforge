# AeroForge — Agent Context for Coding Agents

> Status: ACTIVE HACKATHON BUILD
> Date: 2026-08-26
> Target: Google All Things Agentic Hackathon 2026
> Builder: Solo
> Phase: Day 1 - Baseline + Agent Skeleton

---

## MISSION

Build an agentic system that behaves like an **autonomous flight engineer**.

Input: Natural language drone mission
> "Fly from A to B using the camera to avoid obstacles, minimizing unnecessary motion."

Output: Validated, reproducible PX4 SITL flight with metrics.

---

## HACKATHON REQUIREMENTS (MUST HAVE)

- ✅ Gemini 3.5+ via API/Vertex AI
- ✅ Google ADK (Agent Development Kit)
- ✅ Google Cloud: Cloud Run, Firestore, Cloud Storage
- ✅ PX4 SITL + Gazebo Harmonic
- ✅ ROS 2 Jazzy

---

## CURRENT ENVIRONMENT (VERIFIED)

| Component | Version/Path | Status |
|-----------|--------------|--------|
| PX4-Autopilot | v1.17.0 (d6f12ad1c4) | `/home/mr_nags/PX4-Autopilot` ✅ |
| Gazebo Harmonic | 8.14.0 | distrobox `ubuntu24` ✅ |
| ROS 2 | Jazzy (built from source) | `/home/mr_nags/ros2_jazzy` ✅ |
| micro-ROS Agent | Built from source | `/tmp/micro-ros-agent` ✅ |
| Python | 3.12.3 | distrobox + host ✅ |
| PX4 SITL + Gazebo | Working | `HEADLESS=1 make px4_sitl gz_x500` ✅ |

---

## SIMULATION COMMANDS (TESTED WORKING)

```bash
# Terminal 1: micro-ROS Agent (ROS 2 bridge)
distrobox enter ubuntu24 -- bash -c "
  . /opt/ros/jazzy/setup.bash
  export LD_LIBRARY_PATH=/tmp/micro-ros-agent/install/micro_ros_agent/lib:\$LD_LIBRARY_PATH
  /tmp/micro-ros-agent/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent udp4 -p 8888 -v 4
"

# Terminal 2: PX4 SITL + Gazebo (headless)
distrobox enter ubuntu24 -- bash -c "
  pkill -9 -f 'px4\|gz sim' 2>/dev/null; sleep 2
  . /home/mr_nags/ros2_jazzy/install/setup.bash
  cd /home/mr_nags/PX4-Autopilot
  HEADLESS=1 make px4_sitl gz_x500
"

# Terminal 3: Verify ROS 2 topics
distrobox enter ubuntu24 -- bash -c "
  . /home/mr_nags/ros2_jazzy/install/setup.bash
  ros2 topic list | grep fmu
"
```

---

## AGENT ARCHITECTURE (4 Specialized Agents)

### 1. Mission Analyst
- Input: Natural language mission
- Output: `MissionSpec` JSON
- Tools: `get_environment_status()`

### 2. Autonomy Architect
- Input: `MissionSpec` + environment capabilities
- Output: `ExperimentSpec` (algorithm choice, reward, obs/action spaces)
- Decision: Classical planner vs RL vs Hybrid

### 3. Experiment Engineer
- Input: `ExperimentSpec`
- Runs: Simulation, training, evaluation
- Tools: `simulation.start()`, `run_episode()`, `training.start()`, `evaluation.compute_metrics()`

### 4. Verification Agent
- Input: Experiment results
- Output: PASS/ITERATE/FAIL with thresholds
- Separate from optimization agent

---

## TOOL BOUNDARY (LLM calls typed tools)

```python
# Simulation
simulation.start(config)
simulation.stop()
simulation.run_episode(policy_config)
simulation.capture_camera()

# PX4
px4.sitl_status()
px4.deploy_to_sitl(policy_path)

# Training
training.start(config)
training.status()
training.stop()

# Evaluation
evaluation.compute_metrics(telemetry)
```

---

## SAFETY RULES (ABSOLUTE)

1. SITL first - no real hardware
2. No arbitrary actuator/motor commands to LLM
3. No automatic firmware flashing
4. No bypassing PX4 failsafes
4. Candidate policies must pass sim eval before promotion
5. Keep generated code in sandboxed workspace
6. Never overwrite user's PX4 without explicit approval
7. Preserve all experiment logs
8. Fail closed or ask for clarification

---

## DAY 1 SUCCESS CONDITIONS

- [x] Environment documented
- [x] PX4 SITL + Gazebo baseline flight works
- [ ] Google ADK agent scaffold
- [ ] MissionSpec schema
- [ ] `get_environment_status()` tool
- [ ] `run_baseline_mission()` tool
- [ ] Natural language → MissionSpec → baseline flight → metrics → explanation

---

## FILES TO NEVER MODIFY

- `/home/mr_nags/PX4-Autopilot` - Upstream PX4 source
- `/home/mr_nags/ros2_jazzy` - ROS 2 build
- `/home/mr_nags/px4_venv` - PX4 Python venv

---

## NEXT IMMEDIATE TASKS

1. Create Python virtual environment for aeroforge
2. Install Google ADK dependencies
3. Define `schemas.py` with MissionSpec, ExperimentSpec, Metrics
4. Implement `agent/mission_agent.py` with `get_environment_status()`
5. Implement `tools/simulation.py` with distrobox command wrappers
6. Wire up first vertical slice