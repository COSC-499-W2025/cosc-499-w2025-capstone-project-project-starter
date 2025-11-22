from collections import defaultdict

from . import file_classification
from ml.universal import predict


def parse_directory(root_dir, threshold=0.5):
    """
    Walk `root_dir`, classify each non-binary file, and return a list of:
      { "file": <path>, "predictions": [(skill, prob), ...] }
    """
    results = []

    text_files = file_classification.list_text_files(root_dir)

    for path in text_files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            # Skip unreadable files
            continue

        preds = predict.classify_text(content, threshold=threshold)
        results.append({"file": path, "predictions": preds})

    return results


def summarize_results(results):
    """
    Aggregate predictions across all files and print a summary.
    Returns a list of dicts with keys:
        - "skill"
        - "count" (# files where skill appears)
        - "avg_prob"
        - "max_prob"
    sorted by max_prob descending.
    """
    skill_scores = defaultdict(list)

    for item in results:
        for skill, prob in item.get("predictions", []):
            skill_scores[skill].append(prob)

    summary = []
    for skill, probs in skill_scores.items():
        if not probs:
            continue
        count = len(probs)
        avg_prob = sum(probs) / count
        max_prob = max(probs)
        summary.append(
            {
                "skill": skill,
                "count": count,
                "avg_prob": avg_prob,
                "max_prob": max_prob,
            }
        )

    summary.sort(key=lambda x: x["max_prob"], reverse=True)

    print("=== Skill summary across all non-binary files ===")
    for entry in summary:
        print(
            f"{entry['skill']}: "
            f"files={entry['count']}, "
            f"avg_prob={entry['avg_prob']:.3f}, "
            f"max_prob={entry['max_prob']:.3f}"
        )

    print("\n=== Per-file predictions (non-empty) ===")
    for item in results:
        if not item["predictions"]:
            continue
        print(f"\nFile: {item['file']}")
        for skill, prob in item["predictions"]:
            print(f"  {skill}: {prob:.3f}")

    return summary
