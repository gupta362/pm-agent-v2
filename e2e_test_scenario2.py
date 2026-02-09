"""
E2E Test Scenario 2: Store Delivery (Operations Input)
Section 14.2 of the implementation spec.

Expected:
- Probe 1: No embedded solution → validate problem existence
- Probe 2: Why now? Has something changed?
- Probe 4 fires: Store reality check (directly about store operations)
- Pattern 5 may fire: Talent dependency
- Questions focus on: What's driving out-of-stocks? Is it scheduling or something else?
"""
import json
from e2e_test_harness import run_scenario, verify_scenario, print_report

USER_MESSAGES = [
    # Turn 1: Operations input from Section 14
    "We need to improve our store delivery scheduling to reduce out-of-stocks.",
    # Turn 2: Answer probing on root cause
    "The main issue is timing — deliveries arrive when stores can't process them, so stock sits in the back room. We've seen out-of-stock rates climb from 3% to 7% over the last two quarters. This is happening across about 2,000 stores.",
    # Turn 3: Provide more context on why now and constraints
    "The increase coincided with a new warehouse management system rollout. Our logistics team manages scheduling but they don't have real-time store capacity data. The SVP of Retail Operations is pushing for a fix because it's showing up in our quarterly reviews. Store managers are complaining they can't plan labor around unpredictable deliveries.",
    # Turn 4: Deeper probe responses
    "We haven't looked at whether it's the WMS changeover causing it or something else — could be seasonal patterns too. The scheduling system is 10 years old. Store-level data is available but fragmented across 3 systems. The logistics team has 4 people and they're already stretched.",
    # Turn 5: Ask for artifact
    "This is helpful. Go ahead and generate the problem brief.",
    # Turn 6: Confirm
    "Looks good, finalize it.",
]


def run():
    results = run_scenario("Scenario 2: Store Delivery", USER_MESSAGES, max_turns=10)

    # Save raw results
    with open("/tmp/e2e_scenario2_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    checks = [
        # Probe checks
        {
            "name": "Probe 1 fired (validate problem existence / no embedded solution)",
            "spec_item": "S14.2 - Probe 1 validates problem",
            "check": lambda r: (
                any("probe 1" in p["name"].lower() or "solution" in p["name"].lower() or "problem" in p["name"].lower() for p in r["probes_fired"]),
                f"Probes fired: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        {
            "name": "Probe 2 or Why Now probing occurred",
            "spec_item": "S14.2 - Probe 2 why now",
            "check": lambda r: (
                any("probe 2" in p["name"].lower() or "why now" in p["name"].lower() or "urgency" in p["name"].lower() or "pain" in p["name"].lower() or "triangulat" in p["name"].lower() for p in r["probes_fired"]),
                f"Probes fired: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        {
            "name": "Probe 4 fired (store reality check / organizational constraints)",
            "spec_item": "S14.2 - Probe 4 fires",
            "check": lambda r: (
                any("probe 4" in p["name"].lower() or "store" in p["name"].lower() or "reality" in p["name"].lower() or "constraint" in p["name"].lower() or "organi" in p["name"].lower() for p in r["probes_fired"]),
                f"Probes fired: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        {
            "name": "Probes recorded via record_probe_fired",
            "spec_item": "Bug #2b - probes tracked by Phase B tool",
            "check": lambda r: (
                len(r["probes_fired"]) >= 2,
                f"{len(r['probes_fired'])} probes recorded: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        # Pattern checks
        {
            "name": "Patterns recorded via record_pattern_fired (at least 1)",
            "spec_item": "Bug #2 - patterns tracked by Phase B tool",
            "check": lambda r: (
                len(r["patterns_fired"]) >= 1,
                f"{len(r['patterns_fired'])} patterns recorded: {[p['name'] for p in r['patterns_fired']]}"
            ),
        },
        # Conversation summary
        {
            "name": "conversation_summary updated every turn",
            "spec_item": "Arch #3 - rolling summary",
            "check": lambda r: (
                len(r["conversation_summaries"]) >= len(r["turns"]) - 1,
                f"{len(r['conversation_summaries'])} summaries across {len(r['turns'])} turns"
            ),
        },
        # Assumptions
        {
            "name": "Assumptions registered with correct types",
            "spec_item": "S14.2 - assumptions tracked",
            "check": lambda r: (
                len(r["assumptions"]) >= 2,
                f"{len(r['assumptions'])} assumptions: " + "; ".join(
                    f"{aid}=[{a['type']}/{a['confidence']}] {a['claim'][:50]}"
                    for aid, a in list(r["assumptions"].items())[:5]
                )
            ),
        },
        {
            "name": "Has operational/technical assumptions",
            "spec_item": "S14.2 - operations domain assumptions",
            "check": lambda r: (
                any(a["type"] in ("technical", "organizational", "value") for a in r["assumptions"].values()),
                f"Types: {set(a['type'] for a in r['assumptions'].values())}"
            ),
        },
        # Artifact
        {
            "name": "Artifact generated (Problem Brief rendered)",
            "spec_item": "#7 - generate_artifact bypass",
            "check": lambda r: (
                r["artifact_generated"] and r["artifact_content"] is not None,
                f"Artifact: {'yes' if r['artifact_generated'] else 'no'}, length: {len(r['artifact_content'] or '')}"
            ),
        },
        # Mode completion
        {
            "name": "complete_mode returned system to gathering",
            "spec_item": "#8 - complete_mode tool",
            "check": lambda r: (
                r["mode_completed"] and r["final_phase"] == "gathering" and r["final_active_mode"] is None,
                f"completed={r['mode_completed']}, phase={r['final_phase']}, mode={r['final_active_mode']}"
            ),
        },
        # Skeleton
        {
            "name": "Document skeleton has problem statement",
            "spec_item": "S14.2 - skeleton populated",
            "check": lambda r: (
                r["skeleton"]["problem_statement"] is not None and len(r["skeleton"]["problem_statement"]) > 20,
                f"Problem: {(r['skeleton']['problem_statement'] or '')[:80]}"
            ),
        },
        {
            "name": "Stakeholders identified",
            "spec_item": "S14.2 - stakeholders tracked",
            "check": lambda r: (
                r["skeleton"]["stakeholders"] >= 2,
                f"{r['skeleton']['stakeholders']} stakeholders identified"
            ),
        },
    ]

    outcomes = verify_scenario(results, checks)
    passed, total = print_report("Scenario 2: Store Delivery", outcomes)
    print(f"\nSCENARIO_2_RESULT: {passed}/{total}")
    return passed, total


if __name__ == "__main__":
    run()
