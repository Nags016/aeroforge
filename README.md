# AeroForge — The Agentic Flight Engineer

> Turns natural-language drone missions into simulated, tested, and optimized autonomous flight solutions by letting a Gemini-powered agent choose the right autonomy strategy, run experiments, diagnose failures, and deploy the validated policy to PX4 SITL.

## 🎯 Hackathon Project
**Google All Things Agentic Hackathon 2026**  
**Category:** Taskmaster (multi-step engineering workflow automation)  
**Stack:** Gemini 3.5+ • Google ADK • Google Cloud (Cloud Run, Firestore, Cloud Storage) • PX4 SITL • Gazebo Harmonic • ROS 2 Jazzy

---

## 🏗️ Architecture

```
Natural Language Mission
         │
         ▼
    ┌─────────────┐
    │    Gemini   │  (Mission Analyst Agent)
    │   + ADK     │
    └──────┬──────┘
           │ MissionSpec JSON
           ▼
    ┌─────────────┐
    │  Autonomy   │  (Architect Agent)
    │  Architect  │  → ExperimentSpec
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐     ┌──────────────┐
    │  Experiment │────▶│  PX4 SITL +  │
    │   Agent     │     │  Gazebo      │
    └──────┬──────┘     └──────┬───────┘
           │                   │
           ▼                   ▼
    ┌─────────────┐     ┌──────────────┐
    │ Verification│◀────│  Telemetry / │
    │   Agent     │     │   ULog Logs  │
    └──────┬──────┘     └──────────────┘
           │
           ▼
      PASS / ITERATE / FAIL
```

---

## 🚀 Quickstart

### Prerequisites (verified working)
- **PX4-Autopilot v1.17.0** at `/home/mr_nags/PX4-Autopilot`
- **Gazebo Harmonic 8.14.0** in distrobox `ubuntu24`
- **ROS 2 Jazzy** built from source at `/home/mr_nags/ros2_jazzy`
- **micro-ROS agent** built at `/tmp/micro-ros-agent`
- **Python 3.12+** with virtual environment

### 1. Start the Simulation Stack

**Terminal 1 - micro-ROS Agent (ROS 2 bridge):**
```bash
distrobox enter ubuntu24 -- bash -c "
  . /opt/ros/jazzy/setup.bash
  export LD_LIBRARY_PATH=/tmp/micro-ros-agent/install/micro_ros_agent/lib:\$LD_LIBRARY_PATH
  /tmp/micro-ros-agent/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent udp4 -p 8888 -v 4
"
```

**Terminal 2 - PX4 SITL + Gazebo (headless):**
```bash
distrobox enter ubuntu24 -- bash -c "
  pkill -9 -f 'px4\|gz sim' 2>/dev/null; sleep 2
  . /home/mr_nags/ros2_jazzy/install/setup.bash
  cd /home/mr_nags/PX4-Autopilot
  HEADLESS=1 make px4_sitl gz_x500
"
```

**Terminal 3 - Verify ROS 2 topics:**
```bash
distrobox enter ubuntu24 -- bash -c "
  . /home/mr_nags/ros2_jazzy/install/setup.bash
  ros2 topic list | grep fmu
  # Should show: /fmu/out/vehicle_local_position, /fmu/out/vehicle_attitude, etc.
"
```

### 2. Run AeroForge Agent (after setup)
```bash
cd /home/mr_nags/aeroforge
source .venv/bin/activate
python -m agent.main "Fly from A to B using camera to avoid obstacles"
```

---

## 📁 Project Structure

```
aeroforge/
├── README.md                 # This file
├── AGENT_CONTEXT.md          # Master context for coding agents
├── AGENTS.md                 # Agent orchestration rules
├── .env.example              # Environment variables template
├── .gitignore
├── pyproject.toml            # Python package config
├── docs/
│   ├── architecture.md       # System architecture diagram
│   ├── safety.md             # Safety boundaries
│   ├── experiments.md        # Experiment tracking
│   ├── hackathon.md          # Hackathon submission details
│   ├── environment_baseline.md
│   ├── baseline_flight.md
│   ├── camera_baseline.md
│   └── DAY1_REPORT.md
├── agent/
│   ├── __init__.py
│   ├── mission_agent.py      # Mission Analyst - NL → MissionSpec
│   ├── architect_agent.py    # Autonomy Architect - MissionSpec → ExperimentSpec
│   ├── experiment_agent.py   # Experiment Engineer - runs sim, trains, evaluates
│   ├── verifier_agent.py     # Verification Agent - validates results
│   └── schemas.py            # Pydantic models (MissionSpec, ExperimentSpec, Metrics)
├── tools/
│   ├── __init__.py
│   ├── simulation.py         # start(), stop(), run_episode(), capture_camera()
│   ├── px4.py                # sitl_status(), deploy_to_sitl()
│   ├── gazebo.py             # create_scenario(), world management
│   ├── telemetry.py          # get_telemetry(), parse_ulog()
│   ├── camera.py             # get_camera_frame(), depth_from_camera()
│   ├── training.py           # start_training(), get_training_status()
│   └── evaluation.py         # compute_metrics(), compare_policies()
├── simulation/
│   ├── worlds/               # Gazebo world files
│   ├── configs/              # Simulation configs
│   └── scenarios/            # Mission scenarios (obstacles, start/goal)
├── experiments/
│   ├── configs/              # Experiment configurations
│   ├── results/              # Metrics JSONL
│   └── artifacts/            # Policies, logs, models
├── tests/
│   ├── unit/
│   └── integration/
└── infra/
    └── cloud-run/            # Cloud Run deployment configs
```

---

## 🤖 Agent Workflow (Day 1 Target)

### Phase 1-3: Baseline (DONE ✅)
- [x] Environment inspection documented
- [x] PX4 SITL + Gazebo verified working
- [x] Camera simulation - Gazebo camera topics available

### Phase 4-5: Project + Agent Skeleton (IN PROGRESS)
- [x] Repository structure created
- [ ] Google ADK agent scaffold
- [ ] MissionSpec schema defined
- [ ] First tools: `get_environment_status()`, `run_baseline_mission()`

### Phase 6-7: Vertical Slice (NEXT)
- [ ] Natural language → MissionSpec → Baseline flight → Metrics → Explanation

### Phase 8-10: Logging, Testing, Report
- [ ] Experiment logging (JSONL)
- [ ] Schema/tool tests
- [ ] DAY1_REPORT.md

---

## 🛡️ Safety Rules (Non-Negotiable)

1. **SITL only** - No real hardware for MVP
2. **No arbitrary actuator commands** exposed to LLM
3. **PX4 safety boundaries preserved** - Offboard mode requires continuous heartbeat
4. **Fail closed** - Agent asks for clarification when uncertain
5. **Separate optimization from verification** - Two different agents
6. **No PX4 source modifications** without explicit human approval

---

## 📊 Metrics Schema

Every experiment outputs:
```json
{
  "success": true,
  "collision_count": 0,
  "goal_error_m": 0.31,
  "minimum_clearance_m": 1.72,
  "path_length_m": 28.4,
  "flight_time_s": 18.2,
  "smoothness_score": 0.87,
  "experiment_id": "exp_003"
}
```

---

## 🔧 Development Commands

```bash
# Run tests
pytest tests/ -v

# Type check
mypy agent/ tools/

# Format
ruff format agent/ tools/

# Lint
ruff check agent/ tools/
```

---

## 📝 License
MIT License - See LICENSE file

## 🤝 Contributing
Solo hackathon project - issues/PRs welcome for discussion

---

*Built for Google All Things Agentic Hackathon 2026*