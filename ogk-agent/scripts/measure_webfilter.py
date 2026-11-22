import json
from pathlib import Path

from service.modules.webfilter.module import blocked_reason

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "testdata" / "web_domains.json"
DEFAULT_RULES = {
    "blocked_categories": ["adult", "social"],
    "category_domains": {
        "adult": [],
        "social": [],
    },
}


def measure() -> tuple[int, int, list[str]]:
    vectors = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    rules = {**DEFAULT_RULES, "category_domains": {"adult": [], "social": []}}
    rules["category_domains"]["adult"] = vectors["blocked"][:25]
    rules["category_domains"]["social"] = vectors["blocked"][25:]
    blocked = sum(blocked_reason(domain, rules) is not None for domain in vectors["blocked"])
    false_positives = [domain for domain in vectors["education"] if blocked_reason(domain, rules) is not None]
    rate = round(100 * blocked / len(vectors["blocked"]))
    false_rate = round(100 * len(false_positives) / len(vectors["education"]))
    print(f"Blocked: {rate}% ({blocked}/{len(vectors['blocked'])})")
    print(f"False positives: {false_rate}% ({len(false_positives)}/{len(vectors['education'])})")
    print("False positive domains: " + (", ".join(false_positives) if false_positives else "none"))
    return rate, false_rate, false_positives


if __name__ == "__main__":
    block_rate, false_rate, _ = measure()
    raise SystemExit(0 if block_rate >= 95 and false_rate == 0 else 1)
