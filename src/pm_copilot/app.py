import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from pm_copilot.state import init_session_state
from pm_copilot.orchestrator import run_turn


def extract_questions(text):
    """Extract numbered questions from assistant response."""
    pattern = r"\*{0,2}Question\s+(\d+)\*{0,2}[:\s]*\*{0,2}([^\n*]+)"
    matches = re.findall(pattern, text)
    return [(num, title.strip()) for num, title in matches]


st.set_page_config(page_title="PM Co-Pilot", layout="wide")

# Prevent sidebar expander labels from truncating
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p {
        white-space: normal;
        overflow: visible;
        text-overflow: unset;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Initialize ---
init_session_state()

# --- Sidebar ---
with st.sidebar:
    st.title("PM Co-Pilot")
    st.caption("Orchestrator + Mode 1: Discover & Frame")

    st.divider()

    # Current state indicator
    if st.session_state.active_mode:
        st.success(f"Active Mode: {st.session_state.active_mode.replace('_', ' ').title()}")
    else:
        st.info("Phase: Context Gathering")

    st.metric("Turn", st.session_state.turn_count)

    # Assumption register display
    st.divider()
    st.subheader("Assumptions")
    st.caption("🔴 High impact, unvalidated · 🟡 High impact, some evidence · 🟢 Lower impact")
    assumptions = st.session_state.assumption_register
    if assumptions:
        for aid, a in sorted(assumptions.items()):
            if a["impact"] == "high" and a["confidence"] == "guessed":
                icon = "🔴"
            elif a["impact"] == "high":
                icon = "🟡"
            else:
                icon = "🟢"
            with st.expander(f"{icon} {a['id']}: {a['claim']}", expanded=False):
                st.markdown(f"**{a['claim']}**")
                st.write(f"**Type:** {a['type']}")
                st.write(f"**Impact:** {a['impact']} | **Confidence:** {a['confidence']}")
                st.write(f"**Status:** {a['status']}")
                st.write(f"**Basis:** {a['basis']}")
                st.write(f"**Action:** {a['recommended_action']}")
    else:
        st.caption("No assumptions tracked yet.")

    # Document skeleton display
    st.divider()
    st.subheader("Document Skeleton")
    skeleton = st.session_state.document_skeleton
    if skeleton["problem_statement"]:
        with st.expander("**Problem Statement**", expanded=True):
            st.write(skeleton["problem_statement"])
    if skeleton["stakeholders"]:
        st.write(f"**Stakeholders:** {len(skeleton['stakeholders'])} identified")
    if any(skeleton["success_metrics"].values()):
        st.write("**Metrics:** Defined")

    # Artifact download
    if st.session_state.latest_artifact:
        st.divider()
        st.subheader("Latest Artifact")
        st.download_button(
            label="Download Problem Brief",
            data=st.session_state.latest_artifact,
            file_name="problem_brief.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Reset button
    st.divider()
    if st.button("New Session", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Modes roadmap
    st.divider()
    st.subheader("Modes")
    st.write("Mode 1: Discover & Frame")
    st.write("Mode 2: Evaluate Solution")
    st.write("Mode 3: Surface Constraints")
    st.write("Mode 4: Size & Value")
    st.write("Mode 5: Prioritize & Sequence")

# --- Main Chat ---
st.title("PM Co-Pilot")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Show question checkboxes if the last assistant response had questions
pending_qs = st.session_state.pending_questions
if pending_qs:
    st.markdown("**Which questions would you like to respond to?**")
    for num, title in pending_qs:
        st.checkbox(
            f"Question {num}: {title}",
            value=True,
            key=f"respond_q{num}",
        )

# Chat input
if user_input := st.chat_input("Describe your problem, opportunity, or idea..."):
    # Build orchestrator input with question selection context
    if pending_qs:
        selected = []
        for num, title in pending_qs:
            if st.session_state.get(f"respond_q{num}", True):
                selected.append(num)
        # Only add context if user deselected some questions
        if selected and len(selected) < len(pending_qs):
            labels = ", ".join(f"Question {n}" for n in selected)
            orchestrator_input = f"[User is responding to {labels}]\n\n{user_input}"
        else:
            orchestrator_input = user_input
        # Clean up checkbox state
        for num, _ in pending_qs:
            st.session_state.pop(f"respond_q{num}", None)
        st.session_state.pending_questions = None
    else:
        orchestrator_input = user_input

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = run_turn(orchestrator_input)
        st.markdown(response)

    # If user selectively responded, store clean version for display history
    if orchestrator_input != user_input:
        # run_turn stored orchestrator_input; replace with clean version
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user" and msg["content"] == orchestrator_input:
                msg["content"] = user_input
                break

    # Detect questions in new response for next turn's checkboxes
    questions = extract_questions(response)
    st.session_state.pending_questions = questions if questions else None
    st.rerun()
