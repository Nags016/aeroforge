# AeroForge — The Agentic Flight Engineer

> Turns natural-language drone missions into simulated, tested, and optimized autonomous flight solutions by letting a multi-agent system choose the right autonomy strategy, run experiments, diagnose failures, and deploy the validated policy to PX4 SITL.

## 🎯 Drone Automation Project
**Category:** Taskmaster (multi-step engineering workflow automation)  
**Stack:** Python 3.10+ • Rich/Textual CLI • Stable-Baselines3 (PPO/SAC) • PX4 SITL • Gazebo Harmonic • ROS 2 Jazzy

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AEROFORGE AGENT PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Natural Language Mission                                                    │
│           │                                                                   │
│           ▼                                                                   │
│  ┌─────────────────────┐                                                     │
│  │   Mission Analyst   │  → MissionSpec (start, goal, sensors, constraints)  │
│  │  (NL Understanding) │     + Clarifying Questions                          │
│  └──────────┬──────────┘                                                     │
│             │ MissionSpec                                                    │
│             ▼                                                                 │
│  ┌─────────────────────┐                                                     │
│  │  Autonomy Architect │  → Strategy Selection (6 strategies)                │
│  │  (Strategy Scoring) │     + ExperimentSpec (reward, algorithm, env)       │
│  └──────────┬──────────┘                                                     │
│             │ ExperimentSpec                                                 │
│             ▼                                                                 │
│  ┌─────────────────────┐     ┌─────────────────────┐                         │
│  │  Experiment Engineer│────▶│  Training / Sim     │                         │
│  │  (Iterative Cycle)  │     │  PPO/SAC/Classical  │                         │
│  └──────────┬──────────┘     └──────────┬──────────┘                         │
│             │ Metrics                     │                                   │
│             ▼                             ▼                                   │
│  ┌─────────────────────┐     ┌─────────────────────┐                         │
│  │ Verification Agent  │◀────│  Crash Analyzer     │                         │
│  │ (Safety Validation) │     │ (.ulg → log-analyser)│                        │
│  └──────────┬──────────┘     └─────────────────────┘                         │
│             │                                                                   │
│             ▼                                                                   │
│       PASS / ITERATE / FAIL                                                    │
│             │                                                                   │
│             ▼                                                                   │
│  ┌─────────────────────┐                                                     │
│  │   Final Execution   │  → Deploy to PX4 SITL                              │
│  │   (Validated Policy)│     + Full Experiment Record                       │
│  └─────────────────────┘                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5 Specialized Agents

| Agent | Role | Key Capability |
|-------|------|----------------|
| **Mission Analyst** | NL → MissionSpec | Parses natural language, asks clarifying questions |
| **Autonomy Architect** | MissionSpec → ExperimentSpec | Scores 6 strategies, picks optimal approach |
| **Experiment Engineer** | ExperimentSpec → Metrics | Iterative training/eval with bounded parameter mutation |
| **Verifier Agent** | Metrics → PASS/FAIL | Independent safety/performance validation |
| **Crash Analyzer** | .ulg → Fix → Re-run | Auto crash recovery via log-analyser.app |

---

## 🚀 Quickstart

### Prerequisites
- **Python 3.10+** (conda env `aeroforge`)
- **PX4 SITL** (optional for full simulation)
- **Gazebo Harmonic** (optional for visual sim)
- **NVIDIA GPU** (GTX 1650 4GB works for training)
- **ROS 2 Jazzy** (optional)

### 1. Install & Run CLI
```bash
# Already set up! Just run:
aeroforge "Fly from (0,0,2) to (10,10,2) avoiding obstacles"
```

### 2. Interactive Mode
```bash
aeroforge --interactive
```

### 3. Train RL Policy (runs on GPU)
```bash
# Train PPO for 1M steps (~2-3 hours on GTX 1650)
python train_rl.py --algorithm ppo --timesteps 1000000

# Train SAC for 500K steps
python train_rl.py --algorithm sac --timesteps 500000
```

### 4. Run Terminal Visualization Demo
```bash
python terminal_sim.py
```

---

## 🎮 CLI Features (Beautiful Terminal UI)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  █████╗ ██████╗ ██████╗ ██████╗ ██╗  ██╗██╗███╗   ██╗██████╗  ██████╗ ██████╗ ║
║  ...                                                                    ║
║        Agentic Flight Engineer  •  Autonomous Drone Missions  •  v1.0.0     ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━ Step 1: Mission Analyst - Parsing Natural Language ━━━
  ℹ️  Mission ID: mission_001
  ℹ️  Start: (0.0, 0.0, 2.0)
  ℹ️  Goal: (10.0, 10.0, 2.0)
  ℹ️  Sensors: ['gps', 'imu']
  ℹ️  Obstacle Avoidance: reactive_potential_field
  ℹ️  Min Clearance: 2.0m

━━━ Step 2: Environment Status Check ━━━
           🔍 Environment Status            
╭─────────────────┬──────────────┬─────────╮
│ Component       │ Status       │ Details │
├─────────────────┼──────────────┼─────────┤
│ PX4 SITL        │ ✅ Available │ unknown │
│ Gazebo          │ ✅ Available │ unknown │
│ ROS 2           │ ✅ Available │ jazzy   │
│ Camera          │ ✅ Available │         │
│ Depth Camera    │ ✅ Available │         │
│ micro-ROS Agent │ ✅ Running   │         │
│ Compute - CPU   │ ✅           │         │
│ Compute - CUDA  │ ✅           │         │
│ Compute - MPS   │ ❌           │         │
╰─────────────────┴──────────────┴─────────╯

━━━ Step 3: Autonomy Architect - Strategy Selection ━━━
          🧠 Strategy Selection          
╭───────────────────┬───────────────────╮
│ Property          │ Value             │
├───────────────────┼───────────────────┤
│ Selected Strategy │ classical_mpc     │
│ Control Level     │ offboard_velocity │
│ Algorithm         │ MPC               │
│ Episodes          │ 1                 │
╰───────────────────┴───────────────────╯

━━━ Step 4: Experiment Engineer - Running Experiment Cycle ━━━
🔄 Iteration 1/20
   Metrics: success=True, collisions=0, goal_error=0.21m, clearance=1.96m
   Result: ✅ PASS - All thresholds met
✅ Experiment PASSED on iteration 1!

━━━ Step 5: Verifier Agent - Independent Validation ━━━
╭─────────────────────────── 🔍 Verification Result ───────────────────────────╮
│ Passed: ✅ PASSED                                                            │
│ Confidence: 100%                                                             │
│ Score: 0.97                                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯

━━━ Step 6: Final Mission Execution ━━━
      📊 Final Mission Results       
╭────────────────┬────────┬─────────╮
│ Metric         │ Value  │ Status  │
├────────────────┼────────┼─────────┤
│ Success        │ ✅     │ ✅ PASS │
│ Collisions     │ 0      │ ✅      │
│ Goal Error     │ 0.32m  │ ✅      │
│ Min Clearance  │ 2.85m  │ ✅      │
│ Path Length    │ 22.56m │         │
│ Flight Time    │ 10.4s  │         │
│ Energy         │ 64.6   │         │
╰────────────────┴────────┴─────────╯
```

---

## 🧠 6 Autonomy Strategies

| Strategy | Type | Best For | Key Features |
|----------|------|----------|--------------|
| `classical_mpc` | Classical | Precision waypoint, known env | MPC control, fast, deterministic |
| `classical_rrt` | Classical | Exploration, unknown env | RRT* planning, global path |
| `rl_ppo` | RL | Learning from experience | PPO, on-policy, stable |
| `rl_sac` | RL | Continuous control | SAC, off-policy, sample efficient |
| `hybrid_mpc_rl` | Hybrid | Known + unknown mix | MPC planning + RL adaptation |
| `hybrid_rrt_rl` | Hybrid | Complex dynamic env | RRT* global + RL local |

---

## 📊 Experiment Output

Every mission produces a complete JSON record:
```json
{
  "timestamp": "2026-08-29 23:45:12",
  "natural_language": "Fly from (0,0,2) to (10,10,2) avoiding obstacles",
  "mission_spec": {...},
  "environment": {...},
  "experiment_spec": {...},
  "verification": {...},
  "final_metrics": {
    "success": true,
    "collision_count": 0,
    "goal_error_m": 0.32,
    "minimum_clearance_m": 2.85,
    "path_length_m": 22.56,
    "flight_time_s": 10.4,
    "smoothness_score": 0.87,
    "energy_consumption": 64.6
  },
  "total_time_s": 4.2
}
```
Saved to: `experiments/results/mission_mission_001_full.json`

---

## 🤖 RL Training Details

### Environment (36-dim obs, 3-dim action)
```
Observation:
├── Position (3)
├── Velocity (3)  
├── Quaternion (4)
├── Goal Relative (3)
├── 16-Ray Depth (16) - simulated lidar
├── Previous Action (3)
├── Time Left (1)
└── Obstacle Info (4)

Action: [vx, vy, vz] normalized [-1, 1] → scaled to max 10 m/s
```

### Reward Function
```python
reward = (
    goal_reward * reached_goal
    + goal_distance_weight * distance_to_goal
    + clearance_reward_weight * max(0, clearance - threshold)
    + collision_penalty * collision
    + time_penalty * dt
    + action_smoothness_weight * |action - prev_action|
)
```

### Training Config (PPO)
- **Steps:** 1,000,000
- **Parallel envs:** 4
- **LR:** 3e-4
- **Batch:** 256
- **Epochs:** 10
- **Device:** CUDA (GTX 1650)
- **Checkpoints:** Every 50K steps
- **Eval:** Every 25K steps (10 episodes)

---

## 📁 Project Structure

```
aeroforge/
├── aeroforge_cli.py          # Beautiful Rich-based CLI
├── terminal_sim.py           # ASCII/ANSI flight visualization
├── train_rl.py               # PPO/SAC training script
├── AGENTS.md                 # Agent orchestration rules
├── AGENT_CONTEXT.md          # Master context for agents
├── README.md                 # This file
├── pyproject.toml
├── agent/
│   ├── main.py               # Original pipeline entry
│   ├── mission_agent.py      # Mission Analyst
│   ├── architect_agent.py    # Autonomy Architect
│   ├── experiment_agent.py   # Experiment Engineer (with RL eval)
│   ├── verifier_agent.py     # Verification Agent
│   ├── crash_analyzer.py     # Crash recovery
│   ├── schemas.py            # Pydantic models
│   └── __init__.py
├── tools/
│   ├── simulation.py
│   ├── px4.py
│   ├── gazebo.py
│   └── ...
├── simulation/
│   ├── worlds/
│   └── scenarios/
├── experiments/
│   ├── results/              # JSON records
│   └── configs/
├── models/
│   ├── checkpoints/          # Training checkpoints
│   └── best/                 # Best eval models
├── logs/
│   ├── tensorboard/
│   └── eval/
└── tests/
    └── test_schemas.py
```

---

## 🛡️ Safety Rules (Non-Negotiable)

1. **SITL only** - No real hardware for MVP
2. **No arbitrary actuator commands** exposed to agents
3. **PX4 safety boundaries preserved** - Offboard requires continuous heartbeat
4. **Fail closed** - Agent asks for clarification when uncertain
5. **Separate optimization from verification** - Two different agents
6. **No PX4 source modifications** without explicit human approval

---

## 🔧 Development Commands

```bash
# Run tests
cd /home/mr_nags/aeroforge && /home/mr_nags/miniconda3/envs/aeroforge/bin/python -m pytest tests/ -v

# Run CLI demo
aeroforge "Fly from (0,0,2) to (10,10,2) avoiding obstacles"

# Interactive mode
aeroforge --interactive

# Train RL
python train_rl.py --algorithm ppo --timesteps 1000000

# Visualization demo
python terminal_sim.py

# Check training logs
tensorboard --logdir logs/tensorboard
```

---

## 📝 License
MIT License

---

## 🤝 What's Ready

1. **True Agentic System** - 5 specialized agents with clear roles, not a chatbot
2. **Real Engineering Problem** - Drone autonomy requires control theory, perception, safety
3. **Production-Ready CLI** - Beautiful terminal UX like Hermes/Kiro/Codex
4. **RL + Classical Hybrid** - Best of both worlds for autonomy
5. **Crash Recovery Pipeline** - Novel .ulg → log-analyser → auto-fix → re-run
6. **Human-in-the-Loop** - Clarifying questions for ambiguous missions
7. **Complete Experiment Tracking** - Every run logged, replayable, auditable
8. **Works Offline** - Mock simulation for demo, scales to real Gazebo/PX4
9. **Google Stack Ready** - ADK, Firestore, Cloud Storage integration scaffolded

---

*Contact: nagarajsbhat12@gmail.com*
