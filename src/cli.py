"""
Interactive demo.

Run: python -m src.cli

Picks a role, then drops you into a loop where each Enter press advances
the live simulation by one tick (printing any new alerts) and you can type
a question at any time to consult the assistant for that role.
"""
from __future__ import annotations

from .assistant import handle_request, VALID_ROLES
from .simulator import StadiumSimulator
from .state import build_seed_state

HELP = """
Commands:
  <blank line>   advance the simulated live feed by one tick
  ask <question> ask the assistant something (uses your current role)
  role <name>    switch role (ops_manager | security | concessions | fan)
  status         show a full snapshot summary
  help           show this help
  quit           exit
"""


def print_snapshot(state) -> None:
    snap = state.snapshot()
    print(f"-- tick {snap['tick']} | weather: {snap['weather']} --")
    for g in snap["gates"].values():
        print(f"  Gate {g['id']}: {g['current_count']}/{g['capacity']} ({g['density']:.0%}) [{g['status']}]")
    for c in snap["concessions"].values():
        print(f"  {c['name']}: stock {c['stock_pct']}% | queue {c['queue_length']} | staff {c['staff_count']}")
    open_incidents = [i for i in snap["incidents"] if i["status"] == "open"]
    print(f"  Open incidents: {len(open_incidents)}")
    for i in open_incidents:
        print(f"    {i['id']} {i['type']} ({i['severity']}) @ {i['location']}")


def main() -> None:
    state = build_seed_state()
    sim = StadiumSimulator(state)

    print("StadiumOps AI — smart stadium & tournament operations assistant")
    print(f"Roles: {sorted(VALID_ROLES)}")
    role = input("Choose your role [ops_manager]: ").strip() or "ops_manager"
    while role not in VALID_ROLES:
        role = input(f"Unknown role. Choose from {sorted(VALID_ROLES)}: ").strip()
    print(HELP)

    while True:
        raw = input(f"({role})> ").strip()

        if raw == "":
            events = sim.tick()
            for e in events:
                print(" ", e)
            continue
        if raw in ("quit", "exit"):
            break
        if raw == "help":
            print(HELP)
            continue
        if raw == "status":
            print_snapshot(state)
            continue
        if raw.startswith("role "):
            new_role = raw.split(" ", 1)[1].strip()
            if new_role in VALID_ROLES:
                role = new_role
                print(f"Switched to role: {role}")
            else:
                print(f"Unknown role. Choose from {sorted(VALID_ROLES)}")
            continue
        if raw.startswith("ask "):
            query = raw.split(" ", 1)[1].strip()
        else:
            query = raw  # treat bare text as a question too

        result = handle_request(role, state, query)
        print(result["answer"])


if __name__ == "__main__":
    main()
