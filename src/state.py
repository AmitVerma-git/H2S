"""
Central state store for the stadium.

This is the single source of truth. The simulator writes to it (mimicking
sensors/POS/ticketing feeds); the decision engine and assistant only ever
read from it via `StadiumState.snapshot()`. Keeping mutation and reading
separate is what makes the engine testable with plain dicts.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class Gate:
    id: str
    name: str
    capacity: int
    current_count: int = 0
    status: str = "open"  # open | restricted | closed

    @property
    def density(self) -> float:
        return round(self.current_count / self.capacity, 2) if self.capacity else 0.0


@dataclass
class ConcessionStand:
    id: str
    name: str
    location: str
    stock_pct: int = 100
    queue_length: int = 0
    staff_count: int = 2


@dataclass
class SecurityIncident:
    id: str
    type: str
    location: str
    severity: str  # low | medium | high | critical
    timestamp: str
    status: str = "open"  # open | escalated | resolved


@dataclass
class ScheduleEvent:
    id: str
    name: str
    location: str
    start_time: str
    end_time: str


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


@dataclass
class StadiumState:
    gates: Dict[str, Gate] = field(default_factory=dict)
    concessions: Dict[str, ConcessionStand] = field(default_factory=dict)
    incidents: List[SecurityIncident] = field(default_factory=list)
    schedule: List[ScheduleEvent] = field(default_factory=list)
    weather: str = "clear"
    tick: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    # ---- mutation helpers (used only by the simulator) ----------------
    def add_incident(self, incident: SecurityIncident) -> None:
        with self._lock:
            self.incidents.append(incident)

    def bump_tick(self) -> None:
        with self._lock:
            self.tick += 1

    # ---- read path (used by the engine / assistant) --------------------
    def snapshot(self) -> dict:
        """Thread-safe, read-only view of current state as plain dicts.
        Decision-engine functions take this snapshot, never the live object,
        so they stay pure and easy to unit test."""
        with self._lock:
            return {
                "tick": self.tick,
                "weather": self.weather,
                "gates": {gid: {**vars(g), "density": g.density} for gid, g in self.gates.items()},
                "concessions": {cid: vars(c).copy() for cid, c in self.concessions.items()},
                "incidents": [vars(i).copy() for i in self.incidents if i.status != "resolved"],
                "schedule": [vars(s).copy() for s in self.schedule],
            }


def build_seed_state() -> StadiumState:
    """A small, fixed starting layout for a single-venue demo."""
    state = StadiumState()
    state.gates = {
        "A": Gate(id="A", name="Gate A - North", capacity=2000, current_count=400),
        "B": Gate(id="B", name="Gate B - South", capacity=2000, current_count=350),
        "C": Gate(id="C", name="Gate C - East (main)", capacity=3000, current_count=900),
        "D": Gate(id="D", name="Gate D - West", capacity=1500, current_count=200),
    }
    state.concessions = {
        "F1": ConcessionStand(id="F1", name="North Concourse Grill", location="near Gate A"),
        "F2": ConcessionStand(id="F2", name="South Snack Bar", location="near Gate B"),
        "F3": ConcessionStand(id="F3", name="East Food Court", location="near Gate C"),
    }
    state.schedule = [
        ScheduleEvent(id="E1", name="Gates Open", location="all gates", start_time="17:00", end_time="18:30"),
        ScheduleEvent(id="E2", name="Main Event", location="Field", start_time="19:00", end_time="21:30"),
        ScheduleEvent(id="E3", name="Egress", location="all gates", start_time="21:30", end_time="22:30"),
    ]
    return state
