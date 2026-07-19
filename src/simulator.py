"""
Simulated live feed.

Stands in for the real sensor/POS/CCTV/ticketing integrations a real
stadium would have (turnstile counters, camera crowd-density models,
POS stock feeds, incident reports). Each `tick()` nudges the state in a
plausible direction and occasionally injects an event, so the assistant
has something dynamic to react to during a demo.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from .state import StadiumState, SecurityIncident

INCIDENT_TYPES = [
    ("medical", "medium"),
    ("medical", "high"),
    ("altercation", "medium"),
    ("altercation", "high"),
    ("suspicious_item", "critical"),
    ("lost_child", "low"),
    ("overcrowding", "high"),
]


class StadiumSimulator:
    def __init__(self, state: StadiumState, seed: int | None = 42):
        self.state = state
        self.rng = random.Random(seed)
        self._incident_counter = 0

    def tick(self) -> list[str]:
        """Advance the world by one step. Returns a list of human-readable
        event log lines for anything notable that happened this tick."""
        events: list[str] = []
        self.state.bump_tick()

        # --- crowd movement at gates ---
        for gate in self.state.gates.values():
            if gate.status == "closed":
                continue
            delta = self.rng.randint(-40, 120)  # net arrivals tend to be positive pre-event
            gate.current_count = max(0, min(gate.capacity, gate.current_count + delta))

        # --- concessions: stock drains, queues fluctuate ---
        for stand in self.state.concessions.values():
            stand.stock_pct = max(0, stand.stock_pct - self.rng.randint(0, 3))
            stand.queue_length = max(0, stand.queue_length + self.rng.randint(-3, 6))

        # --- weather occasionally shifts ---
        if self.rng.random() < 0.03:
            self.state.weather = self.rng.choice(["clear", "rain", "storm_warning", "extreme_heat"])
            events.append(f"[weather] conditions changed to {self.state.weather}")

        # --- random incident injection ---
        if self.rng.random() < 0.12:
            itype, sev = self.rng.choice(INCIDENT_TYPES)
            gate_id = self.rng.choice(list(self.state.gates.keys()))
            self._incident_counter += 1
            incident = SecurityIncident(
                id=f"INC-{self._incident_counter:03d}",
                type=itype,
                location=f"Gate {gate_id}",
                severity=sev,
                timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            )
            self.state.add_incident(incident)
            events.append(f"[incident] {incident.id} ({sev}) {itype} reported at Gate {gate_id}")

        return events
