# PEIS — Personal Engineering Intelligence System

PEIS is a personal engineering intelligence environment for helping an individual understand, plan, execute, evaluate, and continuously improve complex technical work without surrendering authority to an AI model.

It combines long-term operational continuity, grounded planning, deterministic validation, bounded execution, and evidence-based learning into a governed engineering workflow.

PEIS is not intended to be an autonomous agent that decides what should happen and then acts without oversight. AI systems may interpret, propose, repair, and assist. Deterministic software decides whether a proposal is structurally admissible, and the human retains authority over objectives, policy, approval, and consequential action.

> **Project status:** Advanced architecture with multiple substantial but partly separate implementations. The repository contains a deterministic record/control-plane path, a model-assisted planning subsystem, a PlanRecord-driven capability executor and CLI, and a FastAPI gateway with local Ollama and OpenAI provider adapters. These are **not yet connected into one verified request-to-plan-to-authorized-execution workflow**. The intended shared Open WebUI multi-model environment is also not established. PEIS is not a completed or production-ready platform.

## Why PEIS Exists

Complex projects rarely fail because ideas are unavailable. They fail because execution loses continuity:

- Objectives drift or become fragmented.
- Decisions become separated from their rationale.
- Project state is scattered across conversations, repositories, tools, and machines.
- Plans silently stop matching current evidence or available capabilities.
- AI output is treated as authoritative without adequate validation.
- Outcomes are recorded poorly and do not improve future work.

PEIS is designed to preserve the connection between intention, evidence, decisions, action, and results across the life of a project.

Its central question is:

> How can one person reliably coordinate increasingly complex engineering work across projects, systems, tools, and AI capabilities while preserving understanding, traceability, and human authority?

## System Model

The full PEIS vision follows this intelligence cycle:

```text
Human objective
      ↓
Memory and continuity
      ↓
Retrieval and grounding
      ↓
Reasoning and planning
      ↓
Deterministic validation
      ↓
Human authorization when required
      ↓
Bounded execution support
      ↓
Results, evaluation, and learning
```

Two related layers make up the project:

### The broader PEIS environment

The complete environment is intended to help the user:

- Preserve long-term engineering and project context.
- Retrieve relevant evidence at the right time.
- Reason through difficult, multi-domain problems.
- Turn informal objectives into explicit plans.
- Coordinate AI models, software tools, and human decisions.
- Evaluate actual outcomes against intended outcomes.
- Reuse prior decisions, failures, and results to improve future work.

### The governed operational core

The operational core is the authoritative control plane currently being implemented. It determines:

- Whether an AI-produced plan is structurally valid.
- Whether every proposed action maps to a registered capability.
- Whether the necessary evidence, policy, and configuration are bound to the plan.
- Whether human approval is required.
- What may execute and under which constraints.
- What happened during execution.
- Whether the system must halt instead of continuing unsafely.

The control plane is not the entirety of PEIS. It is the machinery that allows the broader intelligence environment to operate dependably.

## Operating Model

### Conversation and planning are separate authority domains

PEIS distinguishes ordinary assistance from authoritative planning:

| Mode | Purpose | Authority |
|---|---|---|
| `CONVERSATION` | Exploration, explanation, and advice | Advisory only; cannot authorize execution |
| `PLANNING` | Produce a schema-constrained and capability-bound plan | May produce a validated `PlanRecord` |

This boundary prevents conversational language from silently becoming executable instruction.

### Models propose; deterministic systems decide admissibility

The bounded planning flow is:

1. A local model produces a non-authoritative draft.
2. The draft is checked against schemas, policies, evidence, and the capability inventory.
3. ChatGPT may perform one bounded repair or adjudication step when appropriate.
4. The repaired result is validated again.
5. Material ambiguity is escalated to the human.
6. If no valid result can be produced, the request hard-fails.

Canonical planning outcomes include:

- `VALID`
- `REPAIRED_VALID`
- `ESCALATE_USER`
- `HARD_FAIL`

Models cannot validate their own output, invent executable capabilities, approve a plan, or create authority through repeated debate.

### Execution is capability-bound

PEIS does not treat arbitrary model-generated commands as executable. A plan may invoke only capabilities that are present in a registered capability inventory and permitted by current policy.

The prototype capability surface includes actions such as:

- `noop`
- `run_pytest`
- `identify_next_task`
- `summarize_current_blocker`
- `review_repo_state`
- `review_runtime_surface`
- `review_recent_artifacts`

These capabilities demonstrate the execution pattern. They do not yet represent the intended breadth of the finished system.

## Implemented Records and Separate Execution Paths

The repository contains several structured record models and persistence paths. They are related to the intended PEIS lifecycle, but they do not yet form one integrated end-to-end pipeline.

### Deterministic control-plane path

The typed runtime accepts a `PipelineRequest` that already contains its authority, evidence, determinism, and stop-decision inputs. It builds and validates the corresponding evaluation, decision, and plan records through the deterministic runtime orchestrator.

```text
PipelineRequest
  → input and cross-module contract validation
  → deterministic orchestration
  → EvaluationRecord / DecisionRecord / PlanRecord
```

### PlanRecord execution path

The execution CLI accepts an existing serialized `PlanRecord`, resolves the repository and Python interpreter, executes its steps through a registered capability allow-list, constructs an `ExecutionResultRecord`, and persists that result.

```text
Existing PlanRecord JSON
  → registered CapabilityRegistry
  → PlanExecutionResult
  → ExecutionResultRecord
  → persisted result
```

This is a PlanRecord-driven execution path. It does not, by itself, prove that the model-assisted planning subsystem generated that PlanRecord or that the entire lifecycle is connected.

### Model-assisted planning path

A separate planning subsystem contains code for:

- Building a `PlanningSessionSnapshot`.
- Retrieving prior planning artifacts as grounding context.
- Building a versioned prompt pack.
- Asking a local model to draft a plan.
- Applying structural and capability validation.
- Making one bounded ChatGPT adjudication attempt when the initial draft is invalid.
- Persisting validated-plan, failure, and correction artifacts.

**Current limitation:** the capability-contract lookup in `src/peis/planning/contracts.py` calls `_register_default_capabilities(registry)`, but the function in `src/peis/execution/cli.py` requires a `repo_root` keyword argument. As currently committed, this mismatch prevents the planning validation path from being treated as operational. The planning package also has no direct test module in the current test tree.

### Record types present in the repository

| Record or artifact | Current role |
|---|---|
| `PlanningSessionSnapshot` | Captures planning-session context and version bindings |
| `EvaluationRecord` | Represents a structured evaluation |
| `DecisionRecord` | Represents a governed decision |
| `PlanRecord` | Represents a validated, capability-bound execution plan |
| `ExecutionResultRecord` | Represents and persists execution outcomes |
| Planning failure/correction artifacts | Preserve invalid drafts and adjudication/correction history |

`StopDecision` and the shared `StopState` algebra are implemented. A separate persisted `StopArtifact` is not present. Separate `ApprovalRecord` and `ExecutionConfigRecord` types are also not present in the current source tree; those remain architectural requirements rather than implemented artifact classes.

The full target artifact lifecycle remains a design objective. Diagrams and target requirements should not be read as proof that every named artifact or transition is implemented.

## Human Authority and Safety

PEIS separates structural validity, human authorization, and execution.

- A valid plan is not automatically authorized.
- `PlanRecord` binds authority, evidence, determinism, and its basis decision/stop state.
- `PlanRecord` enforces the shared stop-state rules and the human gate for states that require intervention.
- Registered capabilities can independently declare that human authorization is required; the executor checks the plan's `human_authorized` value before invoking such a capability.
- Execution is restricted to capabilities registered in an explicit allow-list. Arbitrary model-generated shell commands are not an execution capability.
- HALT stop states are defined and prevent normal plan progression. A separate persisted `StopArtifact` lifecycle is not implemented.
- The current implementation carries authorization as a boolean on the plan; it does not yet provide a separate persisted `ApprovalRecord` lifecycle.
- A complete persisted execution-configuration artifact and lifecycle are not implemented.

The design keeps objectives, legitimacy, policy, priorities, approval, and final authority with the human. The code implements parts of these boundaries; the complete approval and execution-governance lifecycle remains unfinished.

## Learning Without Uncontrolled Self-Modification

PEIS improves through evidence, not autonomous self-rewriting. Its feedback sources include:

- Validated plans.
- Validation failures.
- Model correction and adjudication cases.
- Human decisions.
- Execution results.
- Project artifacts and observed outcomes.

These records can become grounded inputs to later planning, allowing the system to improve while preserving provenance and reviewability.

## System Boundaries

PEIS deliberately does not attempt to own every adjacent AI or knowledge function.

PEIS does not own:

- Raw conversation transcript storage.
- Conversation archival or long-term memory storage.
- Corpus ingestion and retrieval indexing infrastructure.
- Embedding generation or vector databases.
- Arbitrary host mutation or hardware optimization.
- A chat interface as an authority boundary.
- Hidden retrieval, implicit planning-mode changes, or implicit execution.

Other systems may provide continuity, memory, or retrieval to PEIS through explicit interfaces. Retrieved information remains non-authoritative until it is deliberately bound into a planning session.

## Current Implementation

The repository is a Python project using a `src/` layout and requiring Python 3.12 or later. The source tree contains the following distinct implementation areas.

### Deterministic records and control-plane primitives

Implemented code includes:

- Authority classes and evidence-role bindings.
- Evidence and determinism envelopes, including mismatch detection.
- A shared stop-state model and cross-module enforcement functions.
- Structured `EvaluationRecord`, `DecisionRecord`, and `PlanRecord` models and builders.
- A typed deterministic runtime request/orchestration path.
- JSON artifact storage and loading.

### Capability execution

Implemented code includes:

- An explicit `CapabilityRegistry` allow-list with no dynamic imports or fallback execution.
- A `PlanRecord` executor that checks capability registration and human-authorization requirements.
- An execution CLI that accepts a serialized `PlanRecord`, resolves the repository root and repo-local Python interpreter, runs registered handlers, and persists an `ExecutionResultRecord`.
- Seven CLI-registered capabilities: `noop`, `run_pytest`, `identify_next_task`, `summarize_current_blocker`, `review_repo_state`, `review_runtime_surface`, and `review_recent_artifacts`.

The CLI's execution path begins with an already-created `PlanRecord`. It is not currently wired directly to the model-assisted planning runtime.

### Model-assisted planning

The repository contains a separate planning package with snapshot construction, Ollama invocation, retrieval, prompt-pack construction, draft generation, schema/capability validation, bounded adjudication, and planning-artifact persistence.

This package is **present in source but not currently verified as runnable at the repository's current HEAD**. In particular, the capability-registry call-signature mismatch described above blocks the validation path. There are no dedicated tests for the planning package in the current test tree.

### Runtime gateway and model providers

A FastAPI gateway is present with:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

Its `GatewayOrchestrator` calls the configured local Ollama provider first and the OpenAI provider second. The current gateway prompt/validator accepts a strict JSON action-plan shape and allows only the `run_pytest` action. Default turn budgets are up to two local-model turns and two OpenAI turns, with a four-turn total limit.

This gateway is a separate model-orchestration surface. The API returns the gateway's JSON response; it does not currently invoke the PEIS `PlanningRuntime`, convert the result into the canonical `PlanRecord`, or execute it through the governed CLI. The gateway configuration also defaults `enable_pipeline_execution` to false. No gateway-specific test module is present.

The gateway's existence does not establish a completed Open WebUI integration. The project conversations record attempts to use Open WebUI as the shared user-facing environment, but the intended multi-model conversation and human hand-back behavior remain unverified. The gateway's internal turn budget is not the same thing as a demonstrated interactive hand-back to the user.

### Test evidence and operational limits

The current repository contains 21 test modules covering core contracts, record construction, storage, execution, and the typed runtime pipeline. The project history records a strongest verified checkpoint of **149/149 automated tests passing**. That is a historical result: tests were not executed as part of this README audit, and the current test tree does not directly exercise the planning package or runtime gateway.

The repository's packaging and launch configuration are also incomplete:

- `pyproject.toml` declares Python 3.12+ and build tooling, but does not declare the runtime dependencies imported by the application.
- The server launch script checks for FastAPI and Uvicorn, while the gateway provider modules also import `requests` and `openai`.
- The current launch scripts contain machine-specific assumptions: `start_peis.sh` and `run_peis_server.sh` use `/home/kimberly/peis`, and `run_peis.sh` expects an SSH host alias named `xps`.

PEIS is therefore best described as an **advanced architecture with a substantial but partially integrated implementation**. It is not yet a stable daily-use environment or a production-ready platform.

## Development Status

| Area | Status |
|---|---|
| Mission, scope, and governing principles | Established |
| Boundary between PEIS and external memory/retrieval systems | Established |
| Canonical governed control-plane design | Substantially established |
| Core authority, evidence, determinism, and stop-state primitives | Implemented |
| Evaluation, decision, and plan record models | Implemented |
| Typed deterministic runtime orchestration | Implemented and covered by tests |
| PlanRecord-based capability executor | Implemented |
| Execution CLI and persisted execution results | Implemented; begins from an existing PlanRecord |
| Default CLI capability inventory | Seven capabilities registered |
| Model-assisted planning subsystem | Source present; current capability-registry call mismatch blocks validation |
| Planning artifact retrieval and persistence | Implemented in source; current runtime path not verified |
| FastAPI gateway and provider adapters | Implemented in source; gateway behavior lacks direct test coverage |
| Gateway-to-PEIS planning/execution integration | Not implemented |
| Open WebUI shared multi-model interaction | Not established |
| Separate ApprovalRecord lifecycle | Not implemented |
| Separate ExecutionConfigRecord lifecycle | Not implemented |
| Persisted StopArtifact lifecycle | Not implemented; StopDecision/StopState primitives exist |
| Human-authorization gate | Partially implemented through PlanRecord and capability checks |
| Automated test checkpoint | 149/149 passing at a historical verified checkpoint; not rerun in this audit |
| Direct tests for planning and gateway packages | Absent from current test tree |
| Memory, continuity, and retrieval integration | Boundaries defined; broader integration incomplete |
| Feedback and learning loop | Partially supported by planning artifacts; not complete |
| Portable setup and stable daily-use operator experience | Incomplete |
| Complete PEIS environment | Not yet implemented |

## Current Priorities

The next stage is to make the existing components work together and verify their behavior against the repository's actual contracts. The immediate implementation priorities are:

- Correct the capability-registry call in `src/peis/planning/contracts.py` so planning validation can resolve the registered action inventory.
- Add direct tests for planning snapshots, retrieval, draft generation, validation, adjudication, and artifact persistence.
- Define and test the conversion from a validated planning result into the canonical `PlanRecord` without bypassing authority, evidence, determinism, or stop-state requirements.
- Connect the planning and execution paths only through that explicit, validated contract.
- Decide whether the gateway is to become an entry point to the governed planning/execution pipeline or remain a separate model-orchestration surface; do not present it as execution until that integration exists.
- Add direct tests for gateway configuration, provider adapters, turn-budget behavior, output validation, and API behavior.
- Establish and verify the intended Open WebUI interaction, including the required human oversight and hand-back behavior.
- Implement distinct approval, execution-configuration, and persisted stop artifacts if they remain part of the canonical architecture.
- Declare application runtime dependencies and replace machine-specific launcher paths/SSH aliases with an explicit, portable configuration.
- Complete the evidence-backed feedback loop and validate PEIS against real engineering work rather than only controlled test objectives.

The intended operator experience remains a natural-language entry point for real engineering work, backed by structured planning and governed execution. That experience should not be described as complete until the separate components above are connected and verified.

## Relationship to the blAIne Ecosystem

PEIS is the operational intelligence layer within the broader blAIne ecosystem.

```text
blAIne
├── The Human Capability Project (THCP)
│   └── Human capability, agency, and governance
├── Knowledge Governance Infrastructure (KGI)
│   └── Knowledge preservation, governance, and continuity
├── Personal Engineering Intelligence System (PEIS)
│   └── Reasoning, planning, validation, execution, and operational learning
└── Future infrastructure initiatives
```

PEIS consumes governed knowledge and continuity, converts human objectives into bounded engineering action, records the resulting evidence, and uses those outcomes to improve future work.

## Long-Term Vision

The long-term goal is not simply better task management or more AI automation.

It is a durable personal engineering environment that helps one person:

- Maintain coherent understanding across many complex projects.
- Use multiple AI systems without confusing assistance with authority.
- Turn objectives into explicit, reviewable, executable plans.
- Coordinate tools and workflows through bounded capabilities.
- Preserve why decisions were made and what actually happened.
- Convert completed work, mistakes, and discoveries into future capability.

PEIS exists to make increasingly ambitious engineering work more understandable, traceable, governable, and executable while keeping the human in control.

---

## Development history, intended interaction environment, and evidence

### PEIS is a component, not the entire AI environment

The project conversations make an important system-boundary distinction:

- **Open WebUI** is the shared user-facing environment in which Blaine wanted to interact with ChatGPT and the local AI.
- **The local model and its retrieval/memory sources** are intended to contribute relevant project context and first-pass responses.
- **ChatGPT** is intended to contribute higher-level reasoning, correction, and synthesis using the local model's contribution.
- **PEIS** is a governed engineering-intelligence component within that environment. It is responsible for structured planning, validation, bounded execution, and evidence-backed operational learning. It is not the chat interface and is not, by itself, what makes the two models communicate.

The intended interaction is not a system that converts every user message into a JSON plan. Ordinary questions and discussion should remain ordinary conversation. Structured plan output is appropriate when the user is actually asking PEIS to plan or execute an engineering task.

### Intended multi-model interaction

The extracted project conversations describe the following target behavior:

1. The user submits a request in the shared environment.
2. The local AI contributes first, using relevant local knowledge, retrieval, and project context.
3. ChatGPT reasons over the user's request and the local AI's contribution, correcting, challenging, or synthesizing as appropriate.
4. The user can observe the exchange, direct it, interrupt it, correct either model, and retain authority over decisions and consequential actions.
5. The interaction is bounded rather than an uncontrolled agent loop; the design discussions specify a maximum of two messages per AI before returning control to the user.

This interaction design is related to PEIS but is not equivalent to the governed planning/execution pipeline. The README therefore distinguishes the working PEIS core from the still-unresolved shared conversation integration.

### What the conversations actually verify

The project history supports these separate conclusions:

- Open WebUI was running and accessible, and Blaine was able to place both ChatGPT and the local model in the same room. The unresolved issue was that the two models were not communicating with one another as intended.
- Ollama and the local `qwen2.5:3b` model were callable on the XPS.
- ChatGPT was callable through the API in a separate test.
- A sequential local-model-to-ChatGPT script was exercised outside Open WebUI. That experiment did not establish the intended integrated experience: outputs were sometimes echoed or malformed, and attempts to post messages into existing Open WebUI chats failed (including a `405 Method Not Allowed` response).
- A PEIS FastAPI gateway and planning/execution pipeline were implemented. Their existence and the successful PEIS vertical slice do not prove that the shared Open WebUI conversation flow was completed.
- The extracted hand-off records explicitly identify the interactive environment integration and meaningful local-model/ChatGPT collaboration as unfinished. The current project should not be described as having a completed multi-agent conversation environment.

Attempts to inject or replay messages into existing Open WebUI conversations through undocumented endpoints were abandoned. That approach is not an accepted integration mechanism and should not be presented as a completed feature.

### Development ownership and AI assistance

The conversations record Blaine setting the project objectives, intended system behavior, authority boundaries, constraints, implementation priorities, and acceptance criteria. They also record his corrections when implementation work drifted from those requirements, including corrections to the distinction between Open WebUI and PEIS.

AI tools generated and revised substantial code, schemas, technical instructions, tests, and documentation under Blaine's direction. This is AI-assisted development guided by the user's concepts and decisions; it is not evidence that every implementation detail or line of code was independently authored by Blaine.

### Test evidence and limits

The **149/149 automated test** result is a historical verified checkpoint recorded in the PEIS implementation conversations. It was not rerun as part of this README update and does not establish that all later changes pass, that the complete PEIS environment is implemented, or that the Open WebUI multi-model integration works.

### Conversation archive

The project conversation archive is retained under `extracted_chats/`. It contains readable Markdown exports and corresponding raw JSON exports. These files are provenance and development-history evidence, not runtime dependencies or an authoritative substitute for the current source code and tests.

The principal PEIS design and implementation records include:

- `PEIS - Project Index`
- `PEIS Project Overview`
- `PEIS Environment Design`
- `PEIS Implementation Query`
- `PEIS Implementation Questions`
- `PEIS Planning Review`
- `PEIS Conversation Layer`
- `Orchestrator for Multi-Agent Interaction`
- `PEIS hand-off details`
- `Iteration drift explanation`

`Browser Copy Workaround` records the separate Chat Archive Extractor effort. That extractor is a neighboring project, not a PEIS subsystem; its conversation is retained here only as part of the historical archive.

