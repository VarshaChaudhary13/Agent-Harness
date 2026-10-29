#!/usr/bin/env python3
"""Run the eval set against the Agent Harness API and report pass/fail."""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg
import requests

API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000") + "/api/v1/query"
QUESTIONS = Path(__file__).parent / "questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

DB = dict(
    dbname=os.getenv("DATABASE_NAME", "ecommerce"),
    user=os.getenv("DATABASE_USER", "student_user"),
    password=os.getenv("DATABASE_PASSWORD", "student_dev"),
    host=os.getenv("DATABASE_HOST", "localhost"),
    port=os.getenv("DATABASE_PORT", "5433"),
)


def run_gold_sql(sql: str):
    """Run the reference SQL against the live database and return its first value."""
    with psycopg.connect(**DB) as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


def numbers_in(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text)}


def ask(query: str) -> dict:
    resp = requests.post(API_URL, json={"query": query}, timeout=300)
    resp.raise_for_status()
    return resp.json()


def main():
    questions = json.loads(QUESTIONS.read_text())
    results = []
    passed = 0

    for q in questions:
        row = {"id": q["id"], "query": q["query"], "expected_agent": q["expected_agent"]}
        try:
            data = ask(q["query"])
            # Field names depend on src/api/models.py. Adjust these keys to match it.
            row["selected_agent"] = data.get("selected_agent")
            row["answer"] = data.get("response") or data.get("answer") or ""

            agent_ok = row["selected_agent"] == q["expected_agent"]
            value_ok = True
            if q["gold_sql"]:
                expected = float(run_gold_sql(q["gold_sql"]))
                value_ok = expected in numbers_in(row["answer"])
                row["expected_value"] = expected

            row["pass"] = agent_ok and value_ok
        except Exception as exc:  # keep going if one request fails
            row["pass"] = False
            row["error"] = str(exc)

        passed += row["pass"]
        status = "PASS" if row["pass"] else "FAIL"
        print(f"[{status}] {q['id']:8} expected={q['expected_agent']:10} got={row.get('selected_agent')}")
        results.append(row)

    total = len(questions)
    print(f"\n{passed}/{total} passed")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"Saved details to {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())