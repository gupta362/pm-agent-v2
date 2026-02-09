"""
E2E Test Scenario 3: Brief High-Risk Input (Density-to-Risk Test)
Section 14.3 of the implementation spec.

Expected:
- System does NOT match the user's brief, action-oriented energy
- Probe 1 fires aggressively: What problem does GenAI solve here?
- Pattern 3 fires: conference-driven solution anchoring (GenAI is buzzworthy)
- System stays concise but asks the hard question
- Something like: "You're ready to move fast — before we do, one thing: what specific
  campaign decision is being made poorly today that GenAI would fix?"
"""
import json
from e2e_test_harness import run_scenario, verify_scenario, print_report

USER_MESSAGES = [
    # Turn 1: Brief, action-oriented input from Section 14
    "Build a GenAI tool for campaign optimization. Go.",
    # Turn 2: Terse response matching user's energy level (to test density-to-risk)
    "We run 500 campaigns a quarter. Manual optimization is leaving money on the table. Our data science team thinks GenAI can automate the targeting and budget allocation.",
    # Turn 3: More detail under probing
    "Campaign managers spend about 2 days per campaign on audience selection and budget splits. Success rate is around 40% — meaning 60% of campaigns underperform their targets. The CMO wants a 'next-gen' solution. We're a mid-size CPG company.",
    # Turn 4: Honest about gaps
    "No, we haven't tested whether better data or simpler rules would fix the 60% underperformance. The GenAI angle came from a board presentation by our CTO. Campaign managers are skeptical about black-box optimization — they want to understand why recommendations are made.",
    # Turn 5: Push for brief
    "OK I think you've probed enough. Generate the problem brief.",
    # Turn 6: Confirm
    "Finalize it.",
]


def run():
    results = run_scenario("Scenario 3: GenAI Density-to-Risk", USER_MESSAGES, max_turns=10)

    # Save raw results
    with open("/tmp/e2e_scenario3_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    checks = [
        # Density-to-risk: Does NOT match user's brief energy
        {
            "name": "Turn 1 response is NOT just 'let's go build it' (density-to-risk)",
            "spec_item": "S14.3 - does NOT match brief energy",
            "check": lambda r: (
                len(r["turns"]) > 0 and r["turns"][0]["response_length"] > 100 and
                not any(phrase in r["turns"][0]["response_preview"].lower() for phrase in [
                    "let's build", "let's start building", "here's the plan", "i'll create",
                    "great, let's go", "sure, let's build"
                ]),
                f"Turn 1 response ({r['turns'][0]['response_length']} chars): {r['turns'][0]['response_preview'][:150]}"
            ),
        },
        {
            "name": "Turn 1 asks probing question (not action-oriented)",
            "spec_item": "S14.3 - asks the hard question",
            "check": lambda r: (
                len(r["turns"]) > 0 and "?" in r["turns"][0]["response_full"],
                f"Contains question mark: {'?' in r['turns'][0]['response_full'] if r['turns'] else 'no turns'}"
            ),
        },
        # Probe 1
        {
            "name": "Probe 1 fired (Solution-Problem Separation for GenAI)",
            "spec_item": "S14.3 - Probe 1 fires aggressively",
            "check": lambda r: (
                any("probe 1" in p["name"].lower() or "solution" in p["name"].lower() for p in r["probes_fired"]),
                f"Probes fired: {[p['name'] for p in r['probes_fired']]}"
            ),
        },
        # Pattern 3
        {
            "name": "Pattern 3 fired (conference/buzzword-driven solution anchoring)",
            "spec_item": "S14.3 - Pattern 3 fires (GenAI is buzzworthy)",
            "check": lambda r: (
                any("pattern 3" in p["name"].lower() or "conference" in p["name"].lower() or
                    "anchor" in p["name"].lower() or "solution" in p["name"].lower() or
                    "hype" in p["name"].lower() or "buzz" in p["name"].lower()
                    for p in r["patterns_fired"]),
                f"Patterns fired: {[p['name'] for p in r['patterns_fired']]}"
            ),
        },
        # Probes and patterns recorded
        {
            "name": "Probes recorded via record_probe_fired",
            "spec_item": "Bug #2b - probes tracked by Phase B tool",
            "check": lambda r: (
                len(r["probes_fired"]) >= 1,
                f"{len(r['probes_fired'])} probes recorded"
            ),
        },
        {
            "name": "Patterns recorded via record_pattern_fired",
            "spec_item": "Bug #2 - patterns tracked by Phase B tool",
            "check": lambda r: (
                len(r["patterns_fired"]) >= 1,
                f"{len(r['patterns_fired'])} patterns recorded"
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
            "name": "Assumptions registered (GenAI-specific risks surfaced)",
            "spec_item": "S14.3 - assumptions tracked",
            "check": lambda r: (
                len(r["assumptions"]) >= 2,
                f"{len(r['assumptions'])} assumptions: " + "; ".join(
                    f"{aid}=[{a['type']}/{a['confidence']}] {a['claim'][:50]}"
                    for aid, a in list(r["assumptions"].items())[:5]
                )
            ),
        },
        {
            "name": "High-impact guessed assumption about GenAI being the right approach",
            "spec_item": "S14.3 - unvalidated GenAI assumption",
            "check": lambda r: (
                any(a["impact"] == "high" and a["confidence"] == "guessed" for a in r["assumptions"].values()),
                f"High/guessed: {[aid + ': ' + a['claim'][:60] for aid, a in r['assumptions'].items() if a['impact']=='high' and a['confidence']=='guessed']}"
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
            "spec_item": "S14.3 - skeleton populated",
            "check": lambda r: (
                r["skeleton"]["problem_statement"] is not None and len(r["skeleton"]["problem_statement"]) > 20,
                f"Problem: {(r['skeleton']['problem_statement'] or '')[:80]}"
            ),
        },
    ]

    outcomes = verify_scenario(results, checks)
    passed, total = print_report("Scenario 3: GenAI Density-to-Risk", outcomes)
    print(f"\nSCENARIO_3_RESULT: {passed}/{total}")
    return passed, total


if __name__ == "__main__":
    run()
