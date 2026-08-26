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
- MUST NOT: modify PX4 safety-critical source, generate unrestricted actuator commands

### 4. Verification Agent
**Purpose**: Independent validation of results
- Compares metrics to acceptance thresholds
- Detects failures, rejects unsafe policies
- Produces validation report
- Structurally separate from optimization agent

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
- **Local**: Experiment JSONL log, CHANGELOG.md

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