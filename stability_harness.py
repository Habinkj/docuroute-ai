"""
stability_harness.py - Pillar 2, Part A: output stability under repeated runs.

THE QUESTION THIS ANSWERS:
  eval_harness.py fires each case ONCE. A single green run can hide a flaky router:
  a case that routes TECHNICAL, TECHNICAL, GENERAL would still "pass" if you happened
  to catch it on a TECHNICAL run. This harness fires each case N times and asks:
  did it route THE SAME WAY every time?

  Two DIFFERENT properties, reported separately (do not confuse them):
    - STABILITY : did all N runs agree with each other? (new - this is Pillar 2)
    - CORRECTNESS: did that agreed route match the golden-set label? (from Part 1)

  A case can be stable-but-wrong (consistently misrouted) or unstable (flaky).
  Under STRICT policy, ANY variance = FAIL, even if the majority route was correct.
  Rationale: an unpredictable router is a broken router.

QUOTA MATH (measured, not guessed):
  Only LLM-classified cases can vary. Level-0 (pure greetings) are plain Python and
  cannot flicker, so testing them 3x wastes quota. We test only the 5 cases that reach
  the Level-2 LLM classifier: C05, C06, C09, C10, C11.
  5 cases x 3 runs = 15 LLM calls. Ceiling is 20 RPD. Fits with headroom.

Usage:
  Terminal 1:  uvicorn main:app --reload
  Terminal 2:  python stability_harness.py
"""

import json
import time
from collections import Counter

import requests

API_URL = "http://localhost:8000/api/chat"
GOLDEN_SET = "golden_set.json"
RESULTS_FILE = "stability_results.jsonl"

# Only cases that actually reach the LLM classifier - the only place variance can live.
CASES_TO_TEST = {"C07", "C10", "C11"}

RUNS_PER_CASE = 3
REQUEST_DELAY = 13          # 5 RPM ceiling -> 1 request / 12s. 13 = headroom.
VARIANCE_POLICY = "strict"  # any disagreement across runs = FAIL


def load_selected_cases():
    with open(GOLDEN_SET, "r", encoding="utf-8") as f:
        allcases = json.load(f)["cases"]
    selected = [c for c in allcases if c["id"] in CASES_TO_TEST]
    missing = CASES_TO_TEST - {c["id"] for c in selected}
    if missing:
        print(f"WARNING: these requested IDs are not in the golden set: {sorted(missing)}")
    return selected


VALID_ROUTES = {"GENERAL", "TECHNICAL"}


def fire_once(query):
    """One request. Returns a valid route string, or None if this run did not
    produce a genuine routing decision.

    A None is returned for BOTH failure modes:
      1. the HTTP request itself threw (network / connection error), and
      2. the request SUCCEEDED but the agent returned a non-route intent such as
         ERROR_FALLBACK - which is what main.py emits when the LLM call fails
         (e.g. a 429 rate-limit). That is the API refusing to answer, NOT the
         router 'deciding' ERROR_FALLBACK. Treating it as a route would poison
         stability with a fake 'stable but wrong' verdict, so we discard it.
    Discarded runs surface as INCOMPLETE downstream and get re-run, never scored."""
    try:
        r = requests.post(API_URL, json={"message": query}, timeout=90)
        payload = r.json()
    except Exception as e:
        print(f"    request error: {e}")
        return None

    if not isinstance(payload, dict):
        return None
    intent = payload.get("intent")
    if intent not in VALID_ROUTES:
        print(f"    non-route intent: {intent!r}  (discarded - not a real routing decision)")
        return None
    return intent


def evaluate_case(case):
    """Fire the same query RUNS_PER_CASE times; analyse stability and correctness."""
    routes = []
    for run in range(1, RUNS_PER_CASE + 1):
        intent = fire_once(case["query"])
        routes.append(intent)
        print(f"    run {run}/{RUNS_PER_CASE}: {intent}")
        if run < RUNS_PER_CASE:
            time.sleep(REQUEST_DELAY)

    # A request failure (None) makes stability unknowable - do NOT score it as a pass/fail.
    if None in routes:
        return {
            "id": case["id"], "query": case["query"],
            "runs": routes, "stable": None, "correct": None,
            "verdict": "INCOMPLETE", "note": "a request failed - rerun this case",
            "expected": case["expected_intent"],
        }

    counts = Counter(routes)
    stable = len(counts) == 1                      # all N runs agreed
    majority_route = counts.most_common(1)[0][0]   # what it mostly said
    correct = majority_route == case["expected_intent"]

    if VARIANCE_POLICY == "strict":
        verdict = "PASS" if (stable and correct) else "FAIL"
    else:  # majority
        verdict = "PASS" if correct else "FAIL"

    note = ""
    if not stable:
        note = f"UNSTABLE: {dict(counts)} across {RUNS_PER_CASE} runs"
    elif not correct:
        note = f"stable but WRONG: always {majority_route}, expected {case['expected_intent']}"

    return {
        "id": case["id"], "query": case["query"],
        "runs": routes, "stable": stable, "correct": correct,
        "majority_route": majority_route, "verdict": verdict, "note": note,
        "expected": case["expected_intent"],
    }


def main():
    cases = load_selected_cases()
    total_calls = len(cases) * RUNS_PER_CASE
    print(f"Pillar 2 / Part A - stability under STRICT policy")
    print(f"Cases: {sorted(c['id'] for c in cases)} | {RUNS_PER_CASE} runs each")
    print(f"API calls: {total_calls} (ceiling 20 RPD) | pacing {REQUEST_DELAY}s")
    print(f"Est. wall time: ~{total_calls * REQUEST_DELAY // 60} min\n")

    results = []
    with open(RESULTS_FILE, "a", encoding="utf-8") as out:
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case['id']}: {case['query']}")
            res = evaluate_case(case)
            results.append(res)
            out.write(json.dumps(res) + "\n")
            out.flush()
            print(f"    -> {res['verdict']}"
                  f"{('  | ' + res['note']) if res['note'] else ''}\n")
            if i < len(cases):
                time.sleep(REQUEST_DELAY)

    scored = [r for r in results if r["verdict"] != "INCOMPLETE"]
    incomplete = [r for r in results if r["verdict"] == "INCOMPLETE"]
    n = len(scored)

    print("=" * 58)
    if n:
        stable_n = sum(r["stable"] for r in scored)
        passed = sum(r["verdict"] == "PASS" for r in scored)
        print(f"Stability : {stable_n}/{n} cases routed identically across {RUNS_PER_CASE} runs")
        print(f"Strict pass: {passed}/{n} (stable AND correct)")
    if incomplete:
        print(f"Incomplete: {len(incomplete)} case(s) had a request failure - rerun them")
    print("=" * 58)

    flaky = [r for r in scored if not r["stable"]]
    if flaky:
        print("\nFLAKY - this is the Pillar 2 finding, go investigate:")
        for r in flaky:
            print(f"  {r['id']}: {r['runs']}  expected {r['expected']}")
            print(f"       {r['query']}")
    elif n:
        print("\nAll tested cases were deterministic across runs at temp=0.")
        print("That is now a MEASURED claim, not an assumption - the senior version.")


if __name__ == "__main__":
    main()