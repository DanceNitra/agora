"""CLI: python -m aiaudit <spec.json>   (or pipe JSON on stdin). Prints the reliability report;
exit code 2 if any dimension FAILs (so it can gate CI)."""
import json
import sys

from .aiaudit import audit, format_report


def main():
    if len(sys.argv) > 1:
        spec = json.loads(open(sys.argv[1], encoding="utf-8").read())
    else:
        data = sys.stdin.read().strip()
        if not data:
            print("usage: python -m aiaudit <spec.json>   (or pipe a JSON spec on stdin)")
            print('spec keys (all optional): ab_test, metric, training_mix, multi_agent, causal, rag_store, memory')
            sys.exit(1)
        spec = json.loads(data)
    rep = audit(spec)
    print(format_report(rep))
    sys.exit(2 if rep["overall"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
