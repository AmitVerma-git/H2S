# StadiumOps AI

**Challenge 4: Smart Stadiums & Tournament Operations**

A context-aware operations assistant for a single stadium/venue on event day.
It watches a live (simulated) feed of gate crowding, concession stock/queues,
weather, and security incidents, and gives **different, role-appropriate
recommendations** to ops managers, security staff, concessions leads, and
fans — all grounded in one shared, auditable state.

## The vertical

Real stadiums run four operational threads in parallel and staff on each
thread only sees their slice: crowd flow at the gates, security/incident
response, concessions and staffing, and the fan-facing experience
(wayfinding, schedule, food). StadiumOps AI is a single assistant that sits
across all four, using **the same live state**, but reasons differently
depending on who's asking.

## Approach & logic

**State is the single source of truth.** `src/state.py` defines the venue
(gates, concession stands, incidents, schedule). Nothing else mutates it
except the simulator; everything else reads an immutable snapshot
(`StadiumState.snapshot()`), which is what keeps the decision logic pure and
unit-testable with plain dicts instead of live objects.

**Decision engine is rule-based, not a black box.** Each operational domain
is a pure function in `src/engine/`: given a state snapshot, return a list of
prioritized recommendations with a human-readable reason.

- `crowd_flow.py` — gate density thresholds → restrict / close / reopen /
  redirect arrivals toward the least-loaded gate.
- `security.py` — incident severity + type → triage tier (log / dispatch
  steward / dispatch security / dispatch emergency services), with a
  cross-incident rule that activates full incident command if multiple
  criticals are open at once.
- `concessions.py` — low stock → restock alert; long queue → add staff;
  also looks *across* stands to suggest moving staff from a quiet stand to
  a busy one before asking for more headcount.
- `fan_qa.py` — the one query-driven module: matches free-text intent
  (gates/lines, schedule, food) against live state to answer fan questions.

Keeping the engine rule-based (rather than asking an LLM to "decide"
directly) means every recommendation is auditable and testable — you can
point at exactly which threshold fired and why. This is deliberate: for
anything touching crowd safety or security dispatch, a system that can
explain itself in one line is more trustworthy than one that can't.

**Context-driven role routing is the "smart, dynamic" part.** `src/assistant.py`
is the orchestrator. The *same* request pipeline behaves differently based
on the caller's role:

| Role | Engine modules run |
|---|---|
| `ops_manager` | crowd_flow + security + concessions (full picture) |
| `security` | security (full) + crowd_flow (critical/high only — overcrowding is a security concern too) |
| `concessions` | concessions only |
| `fan` | fan_qa only, driven by their free-text question |

**Claude is an explanation layer, not the decision-maker.** If
`ANTHROPIC_API_KEY` is set, the structured recommendations are handed to
Claude with an explicit system prompt instructing it not to invent facts —
only to phrase the given recommendations clearly for the role asking. If no
key is set, a deterministic plain-text formatter is used instead. **The
assistant is fully functional with zero external dependencies or API
calls** — this was a deliberate reliability choice for something that could
plausibly run in a real operations booth with unreliable network access.

## How it works (running it)

```bash
git clone <your-repo-url>
cd stadiumops-ai
pip install -r requirements.txt   # optional — only needed for the Claude explanation layer
cp .env.example .env              # optional — add ANTHROPIC_API_KEY if you want NL answers
python -m src.cli
```

In the CLI:
- Press **Enter** on a blank line to advance the simulated live feed by one
  tick (new arrivals, incidents, stock drain, occasional weather shifts).
- `ask <question>` to consult the assistant as your current role.
- `role <name>` to switch between `ops_manager`, `security`, `concessions`,
  `fan`.
- `status` for a full snapshot of the venue right now.

Example session:

```
Choose your role [ops_manager]: security
(security)> [blank enter a few times to let incidents accumulate]
  [incident] INC-001 (high) medical reported at Gate B
(security)> ask what's the priority right now?
[HIGH] dispatch_security_team (INC-001): INC-001: medical (high) at Gate B.
(security)> role fan
(fan)> ask which gate is fastest?
[INFO] suggest_gate (A): Gate A - North currently has the shortest line (24% full).
```

## Project structure

```
src/
  state.py       # data model + thread-safe snapshot
  simulator.py   # generates the live feed (stands in for real sensor/POS/CCTV feeds)
  engine/
    crowd_flow.py
    security.py
    concessions.py
    fan_qa.py
  assistant.py   # role-based orchestration + optional Claude explanation layer
  cli.py         # interactive demo
tests/           # unit tests per engine module + role-routing tests (stdlib unittest,
                 # no external deps required to run)
```

Run tests: `python -m unittest discover -v`

## Assumptions

- Single venue, single event day — no multi-venue or multi-day scheduling.
- No real stadium hardware/API integrations exist for this challenge, so
  `simulator.py` generates a plausible live feed with a fixed random seed
  for reproducible demos. In production, this module would be replaced by
  real turnstile counters, a camera-based crowd-density model, POS stock
  feeds, and an incident-reporting system — the rest of the codebase
  (state, engine, assistant) would be unaffected, since they only depend
  on the `StadiumState` shape.
- Thresholds in the engine modules (e.g. 85% density → restrict) are
  reasonable placeholder values for a demo, not validated safety figures —
  a real deployment would tune these with venue safety officers.
- Claude usage is optional and additive (explanation only); the assistant
  never depends on it for correctness of the recommendation itself.
- No PII or real user data is involved — fan interactions are anonymous,
  free-text questions with no accounts or tracking.
