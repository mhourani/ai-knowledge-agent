"""
Evaluation runner for the AI Knowledge Agent.

Runs the agent against a suite of evaluation cases and reports
pass/fail results across multiple dimensions: retrieval quality,
hallucination resistance, latency, and graceful failure handling.

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --category retrieval
    python evals/run_evals.py --verbose
"""

import json
import time
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import ConversationManager


class EvalRunner:
    def __init__(self, cases_file: str, verbose: bool = False):
        with open(cases_file) as f:
            data = json.load(f)
        self.cases = data["cases"]
        self.verbose = verbose
        self.results = []

    def run_case(self, case: dict) -> dict:
        """Run a single evaluation case and return results."""
        conversation = ConversationManager()

        start = time.time()
        try:
            answer = conversation.ask(case["question"])
            latency = time.time() - start
            error = None
        except Exception as e:
            answer = ""
            latency = time.time() - start
            error = str(e)

        result = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "answer": answer[:500] if answer else "",
            "latency_seconds": round(latency, 2),
            "error": error,
            "checks": {},
        }

        # Check latency
        max_latency = case.get("max_latency_seconds", 60)
        result["checks"]["latency_ok"] = latency <= max_latency

        # Check for expected keywords
        if "expected_keywords" in case and case["expected_keywords"]:
            answer_lower = answer.lower() if answer else ""
            keywords_found = [
                kw for kw in case["expected_keywords"]
                if kw.lower() in answer_lower
            ]
            result["checks"]["keywords_found"] = len(keywords_found) == len(
                case["expected_keywords"]
            )
            result["checks"]["keywords_detail"] = keywords_found

        # Check for forbidden phrases (hallucinations, leaks)
        if "forbidden_phrases" in case:
            answer_lower = answer.lower() if answer else ""
            forbidden_found = [
                p for p in case["forbidden_phrases"]
                if p.lower() in answer_lower
            ]
            result["checks"]["no_forbidden_phrases"] = len(forbidden_found) == 0
            if forbidden_found:
                result["checks"]["forbidden_detail"] = forbidden_found

        # Check for refusal behavior
        if case.get("expected_behavior") in [
            "refuse_or_acknowledge_uncertainty",
            "refuse_or_redirect",
        ]:
            answer_lower = answer.lower() if answer else ""
            refusal_signals = [
                "i don't know",
                "i cannot",
                "i can't",
                "i'm not able",
                "no information",
                "not found",
                "cannot find",
                "unable to",
                "don't have",
                "isn't mentioned",
                "not mentioned",
                "no mention",
            ]
            refused = any(signal in answer_lower for signal in refusal_signals)
            result["checks"]["properly_refused"] = refused

        # Determine overall pass/fail
        checks = result["checks"]
        relevant_checks = {
            k: v for k, v in checks.items()
            if isinstance(v, bool)
        }
        result["passed"] = all(relevant_checks.values()) and error is None

        return result

    def run_all(self, category_filter: str = None):
        """Run all cases, optionally filtered by category."""
        cases_to_run = self.cases
        if category_filter:
            cases_to_run = [c for c in self.cases if c["category"] == category_filter]

        print(f"Running {len(cases_to_run)} evaluation cases...\n")

        for case in cases_to_run:
            print(f"  [{case['id']}] {case['description']}")
            result = self.run_case(case)
            self.results.append(result)

            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            print(f"    {status} ({result['latency_seconds']}s)")

            if self.verbose or not result["passed"]:
                if result.get("error"):
                    print(f"    ERROR: {result['error']}")
                for check, value in result["checks"].items():
                    if isinstance(value, bool) and not value:
                        print(f"    FAILED CHECK: {check}")
            print()

    def summary(self):
        """Print a summary of results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed

        print("=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total cases:   {total}")
        print(f"Passed:        {passed}")
        print(f"Failed:        {failed}")
        print(f"Pass rate:     {(passed / total * 100):.1f}%" if total else "N/A")

        # Category breakdown
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if r["passed"]:
                categories[cat]["passed"] += 1

        print("\nBy category:")
        for cat, stats in sorted(categories.items()):
            rate = (stats["passed"] / stats["total"] * 100) if stats["total"] else 0
            print(f"  {cat:20s} {stats['passed']}/{stats['total']} ({rate:.0f}%)")

        # Latency stats
        latencies = [r["latency_seconds"] for r in self.results if r["latency_seconds"]]
        if latencies:
            print(f"\nLatency:")
            print(f"  Min:    {min(latencies):.2f}s")
            print(f"  Max:    {max(latencies):.2f}s")
            print(f"  Avg:    {sum(latencies)/len(latencies):.2f}s")

        print()

    def save_report(self, output_dir: str = "evals/reports"):
        """Save a timestamped eval report."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"eval_report_{timestamp}.json")

        report = {
            "timestamp": timestamp,
            "total_cases": len(self.results),
            "passed": sum(1 for r in self.results if r["passed"]),
            "results": self.results,
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Run AI Knowledge Agent evaluations")
    parser.add_argument(
        "--cases",
        default="evals/eval_cases.json",
        help="Path to eval cases JSON file",
    )
    parser.add_argument(
        "--category",
        help="Only run cases matching this category",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for all cases",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip saving the JSON report",
    )

    args = parser.parse_args()

    runner = EvalRunner(args.cases, verbose=args.verbose)
    runner.run_all(category_filter=args.category)
    runner.summary()

    if not args.no_report:
        runner.save_report()


if __name__ == "__main__":
    main()