from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running as script from repo root
ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from benchmark.evaluator import load_fixture, list_fixture_names, result_to_dict, run_all_benchmarks, run_benchmark  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Chronos benchmark on fixture dataset")
    parser.add_argument("--fixture", default="demo", help="Fixture name prefix (default: demo)")
    parser.add_argument("--all", action="store_true", help="Run all fixtures")
    parser.add_argument("--save", action="store_true", help="Write result to data/benchmark/")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    if args.all:
        results = run_all_benchmarks(use_llm=False)
        payload = {
            "ranAt": results[-1].ran_at if results else "",
            "fixtures": [result_to_dict(r) for r in results],
        }
    else:
        entries, labels, contexts = load_fixture(args.fixture)
        result = run_benchmark(entries, labels, use_llm=False, contexts=contexts)
        payload = result_to_dict(result)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.save:
        data_dir = Path(os.environ.get("CHRONOS_DATA_DIR", "data"))
        out_dir = data_dir / "benchmark"
        out_dir.mkdir(parents=True, exist_ok=True)
        if args.all:
            (out_dir / "last_suite.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if isinstance(payload, dict) and payload.get("fixtures"):
                (out_dir / "last_result.json").write_text(
                    json.dumps(payload["fixtures"][-1], ensure_ascii=False, indent=2), encoding="utf-8"
                )
            if not args.json:
                print(f"Saved suite ({len(list_fixture_names())} fixtures) to {out_dir / 'last_suite.json'}")
        else:
            (out_dir / "last_result.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if not args.json:
                print(f"Saved to {out_dir / 'last_result.json'}")

    if not args.json and not args.save and not args.all:
        for key in ("anchor", "theme", "relationship"):
            if key not in payload:
                continue
            m = payload[key]
            print(f"{key}: P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f} (tp={m['tp']} fp={m['fp']} fn={m['fn']})")
        if "warning" in payload:
            m = payload["warning"]
            met = payload.get("details", {}).get("warningTargets", {}).get("met")
            print(
                f"warning: P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f} "
                f"(tp={m['tp']} fp={m['fp']} fn={m['fn']}) targets_met={met}"
            )
    elif not args.json and not args.save and args.all:
        for item in payload["fixtures"]:
            print(f"\n=== {item['name']} ===")
            for key in ("anchor", "theme", "relationship"):
                m = item[key]
                print(f"{key}: P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f} (tp={m['tp']} fp={m['fp']} fn={m['fn']})")
            if "warning" in item:
                m = item["warning"]
                met = item.get("details", {}).get("warningTargets", {}).get("met")
                print(
                    f"warning: P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f} "
                    f"(tp={m['tp']} fp={m['fp']} fn={m['fn']}) targets_met={met}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
