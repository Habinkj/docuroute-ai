"""
eval_harness.py - DocuRoute routing eval.

What this does that test_metrics.py does NOT:
  test_metrics.py fires queries and prints whatever intent comes back. It cannot fail.
  This harness compares every result against a GROUND TRUTH label and scores it.

Checks:
  1. Routing accuracy  - did the intent match the label in golden_set.json?
  2. Schema validation - is the payload exactly {response, intent} with a known intent?
  3. Max latency       - slowest round trip observed (NOT p99 - N is far too small)

Quota reality (measured from the AI Studio dashboard, not guessed):
  gemini-2.5-flash free tier = 5 RPM, 20 RPD.
  5 RPM  -> one request every 12s -> REQUEST_DELAY = 13s.
  20 RPD -> a TECHNICAL query costs ~2 calls (embed + generate), ambiguous ~3.
            8 cases in one pass ~= 13 calls. Fits. Two passes would NOT.

Resumable: results append to eval_results.jsonl. Already-run case IDs are skipped,
so you can run a few cases today and the rest tomorrow without losing the score.

Usage:
  1. Start the API in another terminal:  uvicorn main:app --reload
  2. python eval_harness.py
"""

import json
import os
import time

import requests

API_URL = "http://localhost:8000/api/chat"
GOLDEN_SET = "golden_set.json"
RESULTS_FILE = "eval_results.jsonl"

REQUEST_DELAY = 13          # seconds. 5 RPM = 1 per 12s. 13 gives headroom.
DAILY_CALL_BUDGET = 20      # free-tier RPD for gemini-2.5-flash
KNOWN_INTENTS = {"GENERAL", "TECHNICAL"}
REQUIRED_KEYS = {"response", "intent"}


def load_cases():
    with open(GOLDEN_SET, "r", encoding="utf-8") as f:
        return json.load(f)["cases"]


def already_run():
    """Case IDs from previous runs, so we can resume instead of re-spending quota."""
    if not os.path.exists(RESULTS_FILE):
        return set()
    done = set()
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def check_schema(payload):
    """Contract gate: backend must emit exactly {response, intent}, intent must be known."""
    if not isinstance(payload, dict):
        return False, "payload is not a JSON object"
    missing = REQUIRED_KEYS - payload.keys()
    if missing:
        return False, f"missing keys: {sorted(missing)}"
    if payload["intent"] not in KNOWN_INTENTS:
        return False, f"unknown intent value: {payload['intent']!r}"
    if not isinstance(payload["response"], str) or not payload["response"].strip():
        return False, "response is empty or not a string"
    return True, "ok"


def run_case(case):
    start = time.time()
    try:
        r = requests.post(API_URL, json={"message": case["query"]}, timeout=90)
        payload = r.json()
    except Exception as e:
        return {
            "id": case["id"], "query": case["query"],
            "expected": case["expected_intent"], "actual": None,
            "routing_pass": False, "schema_pass": False,
            "schema_note": f"request failed: {e}",
            "latency_s": round(time.time() - start, 2),
            "category": case["category"],
        }

    latency = round(time.time() - start, 2)
    schema_ok, note = check_schema(payload)
    actual = payload.get("intent") if isinstance(payload, dict) else None

    return {
        "id": case["id"], "query": case["query"],
        "expected": case["expected_intent"], "actual": actual,
        "routing_pass": actual == case["expected_intent"],
        "schema_pass": schema_ok, "schema_note": note,
        "latency_s": latency, "category": case["category"],
    }


def main():
    cases = load_cases()
    done = already_run()
    todo = [c for c in cases if c["id"] not in done]

    if not todo:
        print(f"All {len(cases)} cases already run. Delete {RESULTS_FILE} to start fresh.")
        return

    print(f"Golden set: {len(cases)} cases | already run: {len(done)} | to run: {len(todo)}")
    print(f"Pacing at {REQUEST_DELAY}s/request (5 RPM ceiling). "
          f"Est. wall time: ~{len(todo) * REQUEST_DELAY // 60} min.")
    print(f"Reminder: daily budget is {DAILY_CALL_BUDGET} requests. "
          f"TECHNICAL cases cost ~2 calls each.\n")

    results = []
    with open(RESULTS_FILE, "a", encoding="utf-8") as out:
        for i, case in enumerate(todo, 1):
            res = run_case(case)
            results.append(res)
            out.write(json.dumps(res) + "\n")
            out.flush()  # persist immediately - a crash must not lose paid-for results

            mark = "PASS" if res["routing_pass"] else "FAIL"
            schema = "" if res["schema_pass"] else f"  [SCHEMA: {res['schema_note']}]"
            print(f"[{i}/{len(todo)}] {mark} {res['id']} "
                  f"exp={res['expected']} got={res['actual']} "
                  f"{res['latency_s']}s{schema}")
            if not res["routing_pass"]:
                print(f"        query: {res['query']}")

            if i < len(todo):
                time.sleep(REQUEST_DELAY)

    # ---- honest scoring ----
    n = len(results)
    routed = sum(r["routing_pass"] for r in results)
    schema_ok = sum(r["schema_pass"] for r in results)
    latencies = [r["latency_s"] for r in results]

    print("\n" + "=" * 55)
    print(f"Routing accuracy : {routed}/{n} ({routed / n * 100:.1f}%)")
    print(f"Schema validation: {schema_ok}/{n} ({schema_ok / n * 100:.1f}%)")
    print(f"Max latency      : {max(latencies)}s  (N={n} - max observed, NOT p99)")
    print(f"Mean latency     : {sum(latencies) / n:.2f}s")
    print("=" * 55)

    fails = [r for r in results if not r["routing_pass"]]
    if fails:
        print("\nMISROUTED - this is the signal, go read these:")
        for r in fails:
            print(f"  {r['id']} [{r['category']}] exp={r['expected']} got={r['actual']}")
            print(f"       {r['query']}")
    else:
        print("\nAll cases routed correctly. Now go write harder cases - "
              "an eval that never fails is not measuring anything.")


if __name__ == "__main__":
    main()
