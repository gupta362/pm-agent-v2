"""
E2E Test Scenario 1: Digital Twins (Solution-First Input)
Section 14.1 of the implementation spec.

Expected:
- Probe 1 fires: separates digital twins (solution) from campaign prediction (need)
- Pattern 3 fires: conference-driven solution anchoring
- Pattern 2 fires: dual-customer ambiguity (KPM vs platform)
- Pattern 1 may fire: store reality check
- Pattern 6 may fire: alternative profit framing
- Questions focus on: What's the current estimation process? What breaks? Why now?
"""
import json
from e2e_test_harness import run_scenario, verify_scenario, print_report

USER_MESSAGES = [
    # Turn 1: The solution-first input from Section 14
    "The UCM could benefit from a pre-activation decision capability that uses linked digital twins to predict campaign performance before budget is committed.",
    # Turn 2: Answer probing questions about current process
    "Right now campaign managers estimate performance manually using historical data and gut feel. The estimates are often off by 30-40%. This came up at the NRF conference where we saw a vendor demo digital twins for retail. We serve both KPMs (key partner manufacturers) and retail chains as customers.",
    # Turn 3: Provide more context on pain and stakeholders
    "The biggest pain is that bad campaign predictions waste budget — KPMs are spending on campaigns that don't move the needle in stores. Our campaign team runs 200+ campaigns per quarter. The VP of Campaign Strategy is pushing for this. Store execution teams have no visibility into campaign predictions.",
    # Turn 4: Respond to deeper probing
    "We haven't validated with KPMs directly whether prediction accuracy is their top pain point. It could also be attribution — knowing which campaigns drove results. The digital twins idea specifically was from the conference, we haven't done any technical feasibility assessment.",
    # Turn 5: Push for artifact
    "I think we've covered the key points. Can you generate the problem brief?",
    # Turn 6: Confirm
    "Yes, finalize it.",
]


def run():
    results = run_scenario("Scenario 1: Digital Twins", USER_MESSAGES, max_turns=10)

    # Save raw results
    with open("/tmp/e2e_scenario1_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Define verification checks
    checks = [
        # Probe checks
        {
            "name": "Probe 1 fired (Solution-Problem Separation)",
            "spec_item": "S14.1 - Probe 1 fires",
            "check": lambda r: (
                any("probe 1" in p["name"].lower() or "solution" in p["name"].lower() for p in r["probes_fired"]),
                f"Probes fired: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        {
            "name": "Probes recorded via record_probe_fired",
            "spec_item": "Bug #2b - probes tracked by Phase B tool",
            "check": lambda r: (
                len(r["probes_fired"]) >= 1,
                f"{len(r['probes_fired'])} probes recorded: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        # Pattern checks
        {
            "name": "Pattern 3 fired (conference-driven solution anchoring)",
            "spec_item": "S14.1 - Pattern 3 fires",
            "check": lambda r: (
                any("pattern 3" in p["name"].lower() or "conference" in p["name"].lower() or "anchor" in p["name"].lower() or "solution" in p["name"].lower() for p in r["patterns_fired"]),
                f"Patterns fired: {[p['name'] for p in r['patterns_fired']]}"
            ),
        },
        {
            "name": "Patterns recorded via record_pattern_fired",
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
            "name": "Assumptions registered with types and confidence",
            "spec_item": "S14.1 - assumptions tracked",
            "check": lambda r: (
                len(r["assumptions"]) >= 2,
                f"{len(r['assumptions'])} assumptions: " + "; ".join(
                    f"{aid}=[{a['type']}/{a['confidence']}] {a['claim'][:50]}"
                    for aid, a in list(r["assumptions"].items())[:5]
                )
            ),
        },
        {
            "name": "At least one high-impact guessed assumption",
            "spec_item": "S14.1 - unvalidated assumptions surfaced",
            "check": lambda r: (
                any(a["impact"] == "high" and a["confidence"] == "guessed" for a in r["assumptions"].values()),
                f"High/guessed: {[aid for aid, a in r['assumptions'].items() if a['impact']=='high' and a['confidence']=='guessed']}"
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
        {
            "name": "Artifact contains Problem Brief header",
            "spec_item": "#14 - download button content",
            "check": lambda r: (
                r["artifact_content"] is not None and "# Problem Brief" in r["artifact_content"],
                "Has '# Problem Brief' header" if r.get("artifact_content") and "# Problem Brief" in r["artifact_content"] else "Missing header"
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
        # Document skeleton populated
        {
            "name": "Document skeleton has problem statement",
            "spec_item": "S14.1 - skeleton populated",
            "check": lambda r: (
                r["skeleton"]["problem_statement"] is not None and len(r["skeleton"]["problem_statement"]) > 20,
                f"Problem: {(r['skeleton']['problem_statement'] or '')[:80]}"
            ),
        },
        {
            "name": "Stakeholders identified",
            "spec_item": "S14.1 - stakeholders tracked",
            "check": lambda r: (
                r["skeleton"]["stakeholders"] >= 2,
                f"{r['skeleton']['stakeholders']} stakeholders identified"
            ),
        },
    ]

    outcomes = verify_scenario(results, checks)
    passed, total = print_report("Scenario 1: Digital Twins", outcomes)

    # Print summary for parsing
    print(f"\nSCENARIO_1_RESULT: {passed}/{total}")
    return passed, total


if __name__ == "__main__":
    run()
