# PEIS — Personal Engineering Intelligence System

PEIS is a personal engineering intelligence environment for helping an individual understand, plan, execute, evaluate, and continuously improve complex technical work without surrendering authority to an AI model.

It combines long-term operational continuity, grounded planning, deterministic validation, bounded execution, and evidence-based learning into a governed engineering workflow.

PEIS is not intended to be an autonomous agent that decides what should happen and then acts without oversight. AI systems may interpret, propose, repair, and assist. Deterministic software decides whether a proposal is structurally admissible, and the human retains authority over objectives, policy, approval, and consequential action.

> **Project status:** Advanced architecture and functional-core prototype. PEIS has a working vertical slice from objective through planning, validation, registered execution, and deterministic artifact persistence. The complete personal engineering environment is not yet finished.

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

## Authoritative Artifact Chain

PEIS preserves important state as structured, deterministic records rather than leaving it only in chat transcripts.

```text
Request
  → PlanningSessionSnapshot
  → model draft
  → validation and bounded adjudication
  → PlanRecord
  → ApprovalRecord, when required
  → ExecutionConfigRecord
  → registered execution
  → ExecutionResultRecord
  → StopArtifact, on HALT
```

Primary artifact types include:

| Artifact | Purpose |
|---|---|
| `PlanningSessionSnapshot` | Freezes the evidence, policies, capabilities, versions, and relevant context used for planning |
| `PlanRecord` | Represents an admissible, validated plan |
| `ApprovalRecord` | Records explicit human approval or rejection when policy requires it |
| `ExecutionConfigRecord` | Binds execution to an explicit configuration |
| `ExecutionResultRecord` | Records overall and per-step execution outcomes |
| `StopArtifact` | Records a terminal halt condition and prevents silent continuation |

Artifact identity is derived from canonicalized content and its authoritative bindings, including relevant evidence, policies, capabilities, schemas, validators, prompt packs, inputs, and determinism constraints. This makes decisions inspectable and helps expose silent context drift.

## Human Authority and Safety

PEIS treats validation, approval, and execution as separate events.

- A valid plan is not automatically an authorized plan.
- Approval must be explicit, recorded, and bound to the plan when required.
- Rejection is preserved as an authoritative outcome.
- Execution occurs through separately configured, registered capabilities.
- A `HALT` condition stops forward execution and emits a `StopArtifact`.
- Recovery from a halt requires a new evaluation context rather than silent in-place resumption.

Human beings remain responsible for objectives, legitimacy, policy, priorities, approval, and final authority.

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

The current prototype is implemented in Python using a `src/` project layout. Its working components include:

- Planning-session snapshot construction.
- Local-model draft generation through an Ollama adapter.
- Schema and contract validation.
- Bounded escalation, repair, and adjudication.
- Deterministic plan, failure, correction, and result artifacts.
- Persistent planning and execution artifact stores.
- A registered capability framework and plan-driven executor.
- A command-line execution surface.
- A FastAPI-compatible runtime gateway exposing `/health`, `/v1/models`, and `/v1/chat/completions`.

The demonstrated end-to-end vertical slice is:

```text
Objective
  → grounded planning context
  → AI-generated draft
  → deterministic validation or bounded repair
  → validated plan
  → registered execution
  → deterministic result artifact
  → persistence
```

A verified `run_pytest` execution successfully completed through this pipeline and produced a persisted execution record. At the strongest verified implementation checkpoint, the integrated core reported **149 of 149 automated tests passing**.

That test count describes a verified checkpoint, not a claim that every later design requirement is already implemented.

## Development Status

| Area | Status |
|---|---|
| Mission, scope, and governing principles | Established |
| Boundary between PEIS and memory/retrieval systems | Established |
| Canonical governed control-plane design | Substantially complete |
| Canonical architecture gap resolution | Complete for the recorded 18-gap synthesis |
| Planning pipeline | Implemented and demonstrated |
| Validation and bounded model adjudication | Implemented in first-pass form |
| Deterministic artifact persistence | Implemented |
| Registered execution framework | Implemented, with a narrow capability surface |
| Runtime gateway | Implemented |
| Automated test checkpoint | 149/149 passing at the strongest verified checkpoint |
| Human-approval lifecycle | Specified; complete runtime coverage not yet established |
| Execution configuration lifecycle | Specified; complete runtime coverage not yet established |
| HALT and `StopArtifact` lifecycle | Specified; complete end-to-end coverage not yet established |
| Memory, continuity, and retrieval integration | Boundaries defined; broader integration incomplete |
| Feedback and learning loop | Partially supported through artifacts; not complete |
| Stable daily-use operator experience | Incomplete |
| Complete PEIS environment | Not yet implemented |

PEIS is therefore best described as an **advanced architecture with a functional core prototype**, not a production-ready completed platform.

## Current Priorities

The next stage is to bring the working implementation into full alignment with the canonical architecture and make the system reliable for ordinary engineering use. Major priorities include:

- Reconcile remaining contract drift around planning snapshots and determinism bindings.
- Correct misleading normalized metadata after adjudication.
- Improve artifact-driven task selection and reject generic or meta-level recommendations.
- Expand the registered capability inventory.
- Complete approval, execution-configuration, and HALT behavior across the runtime.
- Integrate explicit continuity and retrieval bindings without collapsing neighboring systems into PEIS.
- Turn stored outcomes into a reliable, evidence-backed feedback loop.
- Improve planning reliability under host resource contention.
- Provide a stable daily operator experience, such as:

```bash
peis plan "my actual engineering problem today"
```

- Validate the system across real projects rather than only controlled objectives.

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

## Development history and the intended collaboration environment

The broader Open WebUI environment—not PEIS alone—was intended to let Blaine work with a local model and retrieval as memory/evidence support and ChatGPT as a reasoning resource, with Blaine retaining authority to direct, correct, interrupt, and approve. Blaine clarified that Open WebUI was the shared interface and PEIS was a system component within that environment; he reported that both models could be present in the room but could not communicate with each other. He required a durable, rigorous system rather than a temporary demo and explicitly confirmed bounded multi-model interaction as an intended behavior. [Conversation: `raw_chats/source_exports/PEIS - Project Index_69c96513-b4d8-83e8-9f09-58676374c3e6.raw.json`, active-branch message 42; `raw_chats/source_exports/Orchestrator for Multi-Agent Interaction_69cecc12-d290-83e8-b2fb-c33bdd7e739f.raw.json`, messages 40 and 44; `raw_chats/source_exports/PEIS Conversation Layer_69ceb26c-5fdc-83e8-b08a-9496fef66981.raw.json`, messages 12, 33, and 58].

The conversations also record important implementation divergence: Blaine rejected a gateway that returned structured JSON as satisfying the intended shared interaction experience. The implemented planning, validation, execution, storage, and gateway components are real software in this repository, but they should not be presented as proof that the full local-memory/cloud-reasoning environment is complete. This gap is part of the project’s current state.

Blaine set the objectives, authority boundaries, operational constraints, implementation priorities, and acceptance judgments, and corrected wrong paths, missing scaffolding, technical errors, and claims of completion that did not match the behavior. AI tools generated and revised substantial code, schemas, technical instructions, tests, and documentation. This is extensive AI-assisted development under human direction, not evidence that every implementation detail or line was independently authored by Blaine.

The 149/149 test result elsewhere in this README is supported by a historical terminal capture in `raw_chats/source_exports/PEIS - IMP cont a_69c9a38e-4114-83e8-87f4-5f888dce02a6.raw.json`, active-branch messages 272 and 312. It was not rerun during this review and does not establish the unimplemented full environment or production readiness. See `src/peis/tests/` for test code and the cited raw conversation exports for implementation context and unresolved interaction design.
