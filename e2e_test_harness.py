"""
E2E Test Harness for PM Co-Pilot.
Simulates multi-turn conversations without Streamlit.
"""
import json
import os
import sys
import time
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


# Minimal st.session_state mock
class MockSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)
    def __setattr__(self, key, value):
        self[key] = value


def setup_mock():
    """Patch streamlit session_state and initialize."""
    import streamlit as st
    st.session_state = MockSessionState()
    from state import init_session_state
    init_session_state()


def run_scenario(scenario_name: str, user_messages: list[str], max_turns: int = 10) -> dict:
    """
    Run a multi-turn scenario through the full two-phase architecture.

    Args:
        scenario_name: Name for logging
        user_messages: List of user messages to send in order.
                       After user_messages are exhausted, auto-generates
                       cooperative responses to drive the conversation forward.
        max_turns: Safety limit

    Returns:
        dict with all verification data
    """
    setup_mock()

    import streamlit as st
    from orchestrator import run_turn

    results = {
        "scenario": scenario_name,
        "turns": [],
        "probes_fired": [],
        "patterns_fired": [],
        "assumptions": {},
        "conversation_summaries": [],
        "artifact_generated": False,
        "artifact_content": None,
        "mode_completed": False,
        "final_phase": None,
        "final_active_mode": None,
        "errors": [],
    }

    # Auto-response messages when user_messages run out
    auto_responses = [
        "That's a good question. We haven't validated that directly — it's based on internal team observations. What else do you need to know?",
        "Good point. Let me think about that. The main stakeholders would be the team leads and our VP of Product. We haven't had formal conversations about this with all of them.",
        "You're right to push on that. We don't have hard data yet. The timeline pressure is coming from our quarterly planning cycle — we need a recommendation by end of month.",
        "I think you have enough context now. Can you generate the problem brief?",
        "Yes, that looks right. Please finalize it.",
    ]

    turn = 0
    for i in range(max_turns):
        # Pick user message
        if i < len(user_messages):
            msg = user_messages[i]
        elif i - len(user_messages) < len(auto_responses):
            msg = auto_responses[i - len(user_messages)]
        else:
            msg = "Please generate the problem brief now."

        turn += 1
        t0 = time.time()
        print(f"\n{'='*60}")
        print(f"[{scenario_name}] Turn {turn}: USER: {msg[:80]}...")
        sys.stdout.flush()

        try:
            response = run_turn(msg)
            elapsed = time.time() - t0

            # Capture turn data
            turn_data = {
                "turn": turn,
                "user": msg[:200],
                "response_length": len(response),
                "response_preview": response[:300],
                "response_full": response,
                "elapsed_seconds": round(elapsed, 1),
                "phase": st.session_state.current_phase,
                "mode": st.session_state.active_mode,
                "routing": st.session_state.routing_context.get("last_routing_decision", {}),
            }
            results["turns"].append(turn_data)

            print(f"[{scenario_name}] Turn {turn}: Response ({len(response)} chars, {elapsed:.1f}s)")
            print(f"  Phase: {st.session_state.current_phase}, Mode: {st.session_state.active_mode}")
            print(f"  Probes: {len(st.session_state.routing_context['probes_fired'])}")
            print(f"  Patterns: {len(st.session_state.routing_context['patterns_fired'])}")
            print(f"  Assumptions: {len(st.session_state.assumption_register)}")
            print(f"  Summary: {st.session_state.routing_context.get('conversation_summary', '')[:100]}")
            sys.stdout.flush()

            # Track conversation summary updates
            summary = st.session_state.routing_context.get("conversation_summary", "")
            if summary:
                results["conversation_summaries"].append({
                    "turn": turn,
                    "summary": summary,
                })

            # Check if artifact was generated
            if st.session_state.latest_artifact and not results["artifact_generated"]:
                results["artifact_generated"] = True
                results["artifact_content"] = st.session_state.latest_artifact

            # Check if mode completed (returned to gathering after being in mode)
            if results.get("_was_in_mode") and st.session_state.active_mode is None:
                results["mode_completed"] = True
            if st.session_state.active_mode is not None:
                results["_was_in_mode"] = True

            # If mode completed and artifact generated, we're done
            if results["mode_completed"] and results["artifact_generated"]:
                print(f"\n[{scenario_name}] Mode completed + artifact generated. Done after {turn} turns.")
                break

        except Exception as e:
            results["errors"].append({"turn": turn, "error": str(e)})
            print(f"[{scenario_name}] Turn {turn} ERROR: {e}")
            sys.stdout.flush()

    # Capture final state
    results["probes_fired"] = list(st.session_state.routing_context["probes_fired"])
    results["patterns_fired"] = list(st.session_state.routing_context["patterns_fired"])
    results["assumptions"] = {
        aid: {
            "claim": a["claim"],
            "type": a["type"],
            "impact": a["impact"],
            "confidence": a["confidence"],
            "status": a["status"],
        }
        for aid, a in st.session_state.assumption_register.items()
    }
    results["final_phase"] = st.session_state.current_phase
    results["final_active_mode"] = st.session_state.active_mode
    results["skeleton"] = {
        "problem_statement": st.session_state.document_skeleton["problem_statement"],
        "stakeholders": len(st.session_state.document_skeleton["stakeholders"]),
        "has_metrics": any(st.session_state.document_skeleton["success_metrics"].values()),
        "proceed_if_count": len(st.session_state.document_skeleton["decision_criteria"]["proceed_if"]),
        "do_not_count": len(st.session_state.document_skeleton["decision_criteria"]["do_not_proceed_if"]),
    }

    # Clean up internal tracking key
    results.pop("_was_in_mode", None)

    return results


def verify_scenario(results: dict, checks: list[dict]) -> list[dict]:
    """
    Run verification checks against scenario results.

    Each check is: {"name": str, "check": callable, "spec_item": str}
    Returns list of {"name", "passed", "detail", "spec_item"}
    """
    outcomes = []
    for check in checks:
        try:
            passed, detail = check["check"](results)
            outcomes.append({
                "name": check["name"],
                "passed": passed,
                "detail": detail,
                "spec_item": check.get("spec_item", ""),
            })
        except Exception as e:
            outcomes.append({
                "name": check["name"],
                "passed": False,
                "detail": f"Check raised exception: {e}",
                "spec_item": check.get("spec_item", ""),
            })
    return outcomes


def print_report(scenario_name: str, outcomes: list[dict]):
    """Print formatted verification report."""
    print(f"\n{'='*70}")
    print(f"  VERIFICATION REPORT: {scenario_name}")
    print(f"{'='*70}")
    passed = sum(1 for o in outcomes if o["passed"])
    total = len(outcomes)
    for o in outcomes:
        icon = "✓" if o["passed"] else "✗"
        spec = f" [{o['spec_item']}]" if o["spec_item"] else ""
        print(f"  {icon} {o['name']}{spec}")
        if o["detail"]:
            print(f"    → {o['detail']}")
    print(f"\n  Result: {passed}/{total} passed")
    print(f"{'='*70}")
    return passed, total
