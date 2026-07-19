"""
StadiumOps AI — Streamlit web UI.

Thin presentation layer only: all decision logic still lives in
src/engine/*, src/assistant.py, src/simulator.py, src/state.py. This file
just wires them to widgets so the assistant can be deployed as a live demo
(e.g. Streamlit Community Cloud) without changing any of the tested logic.

Run locally:   streamlit run streamlit_app.py
Deploy:        push to GitHub, then point share.streamlit.io at this file.
"""
from __future__ import annotations

import streamlit as st

from src.assistant import handle_request, VALID_ROLES
from src.simulator import StadiumSimulator
from src.state import build_seed_state

st.set_page_config(page_title="StadiumOps AI", page_icon="🏟️", layout="wide")


def init_session() -> None:
    if "state" not in st.session_state:
        st.session_state.state = build_seed_state()
        st.session_state.sim = StadiumSimulator(st.session_state.state)
        st.session_state.log: list[str] = []
        st.session_state.chat: list[dict] = []


def render_snapshot() -> None:
    snap = st.session_state.state.snapshot()
    st.caption(f"Tick {snap['tick']} · Weather: {snap['weather']}")

    cols = st.columns(len(snap["gates"]))
    for col, g in zip(cols, snap["gates"].values()):
        with col:
            st.metric(
                f"Gate {g['id']}",
                f"{g['current_count']}/{g['capacity']}",
                f"{g['density']:.0%} · {g['status']}",
            )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Concessions")
        for c in snap["concessions"].values():
            st.write(f"**{c['name']}** — stock {c['stock_pct']}% · queue {c['queue_length']} · staff {c['staff_count']}")
    with c2:
        st.subheader("Open incidents")
        open_incidents = [i for i in snap["incidents"] if i["status"] == "open"]
        if not open_incidents:
            st.write("None")
        for i in open_incidents:
            st.write(f"**{i['id']}** {i['type']} ({i['severity']}) @ {i['location']}")


def main() -> None:
    init_session()
    st.title("🏟️ StadiumOps AI")
    st.caption("Smart Stadiums & Tournament Operations — role-based operations assistant")

    with st.sidebar:
        st.header("Controls")
        role = st.selectbox("Your role", sorted(VALID_ROLES), index=sorted(VALID_ROLES).index("ops_manager"))
        if st.button("⏭️ Advance live feed (1 tick)"):
            events = st.session_state.sim.tick()
            st.session_state.log = events + st.session_state.log
        st.divider()
        st.caption("Recent feed events")
        for e in st.session_state.log[:8]:
            st.write(e)

    render_snapshot()
    st.divider()

    st.subheader(f"Ask the assistant (as {role})")
    query = st.text_input("Your question or situation", placeholder="e.g. what should I do about crowding?")
    if st.button("Ask") and query:
        result = handle_request(role, st.session_state.state, query)
        st.session_state.chat.insert(0, {"role": role, "query": query, "answer": result["answer"]})

    for entry in st.session_state.chat:
        st.markdown(f"**[{entry['role']}]** {entry['query']}")
        st.info(entry["answer"])


if __name__ == "__main__":
    main()
