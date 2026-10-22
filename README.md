# dispute-escrow
dispute-escrow
# DisputeEscrow — A Reusable Adjudication Primitive for GenLayer

`DisputeEscrow` is a standalone GenLayer Intelligent Contract that enables trustless milestone payments where fund release depends on AI-verified deliverable quality. It is designed as a **reusable primitive**, not a one-off demo: any builder can deploy a new instance with their own rubric hash without touching the consensus logic.

## Why This Matters

The agentic economy needs a way to settle **subjective deliverables** — code quality, research output, API uptime evidence — where a simple "AI says yes/no" is not enough. `DisputeEscrow` solves this with a two-stage consensus design:

1. **Deterministic gate** — deadline and deliverable hash checks. No LLM involved.
2. **Non-deterministic judgment** — rubric-based LLM evaluation with a **custom validator** that enforces verdict consistency, tolerates minor score variance, and rejects empty reasoning.

This contract fills a gap that existing GenLayer examples (e.g., debate tournaments) do not address: escrow with real funds and a parameterized, reusable rubric.

## How Consensus Is Used

### Stage 1 — Deterministic Gate (Authoritative)

- `submit_deliverable` reverts if called after `deadline`.
- Only the designated `payee` can submit.
- The deliverable hash is stored on-chain for auditability.

### Stage 2 — Non-Deterministic Judgment

The `judge` method runs a leader/validator round:

- **Leader** calls `gl.nondet.exec_prompt` with the rubric and deliverable, requesting structured JSON:
  ```json
  { "verdict": "approve" | "reject" | "partial", "score": 0-100, "reasoning": "..." }
