# AeroForge - Agent Orchestration Rules

## Agent Roles & Responsibilities

### 1. Mission Analyst Agent
**Purpose**: Interpret natural language → structured MissionSpec
- Asks only essential clarifying questions
- Defines: start, goal, obstacles, sensors, safety margins, objectives
- Output: `MissionSpec` JSON

### 2. Autonomy Architect Agent  
**Purpose**: Choose strategy based on MissionSpec + environment
- Inspects available sensors/simulation capabilities
- Selects: Classical / RL / Hybrid approach
- Defines: observation/action spaces, reward function, metrics
- Output: `ExperimentSpec` JSON

### 3. Experiment Engineer Agent
**Purpose**: Execute experiments, iterate on parameters
- Generates/modifies experiment configs
- Launches simulation/training tools
- Inspects results, makes bounded changes
- Repeats until convergence
- Modifies: reward weights, hyperparameters, planner params, obstacle distribution
- **NEW**: Loads & evaluates trained RL policies (PPO/SAC)
- MUST NOT: modify PX4 safety-critical source, generate unrestricted actuator commands

### 4. Verification Agent
**Purpose**: Independent validation of results
- Compares metrics to acceptance thresholds
- Detects failures, rejects unsafe policies
- Produces validation report
- Structurally separate from optimization agent

### 5. Crash Analyzer Agent
**Purpose**: Automatic crash recovery pipeline
- Detects .ulg crash logs from PX4
- Uploads to log-analyser.app for root cause analysis
- Applies fix templates based on crash type
- Triggers re-execution with corrected parameters

---

## Communication Protocol

```
User Mission (NL)
       │
       ▼
Mission Analyst ──▶ MissionSpec
       │
       ▼
Autonomy Architect ──▶ ExperimentSpec
       │
       ▼
Experiment Engineer ──▶ Experiment Results (metrics, logs, artifacts)
       │
       ▼
Verification Agent ──▶ PASS / ITERATE / FAIL
       │
       ▼
Crash Analyzer ──▶ (if crash) Auto-fix → Re-run
       │
       ▼
Final Validated Policy ──▶ PX4 SITL Execution
```

---

## Tool Calling Rules

1. **All tools are typed** - Pydantic input/output validation
2. **Tools log invocations** - timestamp, args, result, duration
3. **Tools have timeouts** - configurable per tool
4. **Tools fail safely** - no shell injection, no arbitrary fs access
5. **Tools return structured data** - JSON-serializable

---

## State Management

- **Firestore**: Experiment metadata, agent state, history
- **Cloud Storage**: ULog logs, policy artifacts, configs
- **Local**: Experiment JSONL log, CHANGELOG.md, trained models

---

## Iteration Loop

```
Experiment N: FAIL
    │
    ▼
Diagnosis (from metrics + logs)
    │
    ▼
Bounded Parameter Change (1-3 params)
    │
    ▼
Experiment N+1
    │
    ▼
... until PASS or max iterations
```

Max iterations per mission: 10 (configurable)

---

## Error Handling

- Tool failures → logged, agent retries with backoff (max 3)
- Simulation crashes → captured, reported, next experiment adjusted
- Policy unsafe → Verification Agent rejects, Experiment Agent modifies
- Ambiguous mission → Mission Analyst asks clarifying question

---

## Google Cloud Integration

- **Cloud Run**: Agent backend API
- **Firestore**: Experiment state, mission history
- **Cloud Storage**: Logs, policies, world files
- **Pub/Sub**: Async simulation job queue (future)

---

## Safety Boundary Enforcement

Code review checklist for every tool:
- [ ] Validates all inputs with Pydantic
- [ ] No `shell=True` or `eval()`
- [ ] No absolute paths outside workspace
- [ ] Timeouts configured
- [ ] Returns structured result or raises typed exception
- [ ] Logs to experiment_log.jsonl

---

## RL Integration Rules

- Training runs on GPU (CUDA) when available
- Checkpoints saved every 50K steps
- Best model selected by evaluation reward
- Policy loaded for eval with `deterministic=True`
- Evaluation runs 10+ episodes for statistical significance
- Trained policies only deployed after Verifier Agent PASS

---

## CLI Interface Standards

- **Rich/Textual** for beautiful terminal UX
- **Panel/Table/Progress** for structured output
- **Color-coded status**: ✅ PASS, ⚠️ WARNING, ❌ FAIL
- **Interactive mode** for iterative mission planning
- **Global `aeroforge` command** installed in `~/.local/bin`
- **Visualization demo** with ASCII/ANSI flight sim

---

## 6 Autonomy Strategies (Implemented)

| Strategy | Type | Algorithm | Best For |
|----------|------|-----------|----------|
| `classical_mpc` | Classical | MPC | Precision waypoint, known env |
| `classical_rrt` | Classical | RRT* | Exploration, unknown env |
| `rl_ppo` | RL | PPO | Learning from experience |
| `rl_sac` | RL | SAC | Continuous control |
| `hybrid_mpc_rl` | Hybrid | MPC + PPO | Known + unknown mix |
| `hybrid_rrt_rl` | Hybrid | RRT* + SAC | Complex dynamic env |

---

## Experiment Output Schema

Every mission produces complete JSON record:
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
Saved to: `experiments/results/mission_<id>_full.json`