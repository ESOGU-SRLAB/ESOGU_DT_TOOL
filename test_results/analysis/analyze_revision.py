"""Reproducible reviewer-revision analyses for the STLC Manager manuscript.

Uses only archived project data. It does not call an LLM or rerun generation.
Outputs item-level Human Oracle agreement, consensus labels, optimizer metrics,
and a fixed-threshold TF-IDF serial-deduplication analysis.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "test_results"
HUMAN = DATA / "human oracle"
OUT = Path(__file__).resolve().parent / "outputs"

SOURCE_NAMES = {
    "codestral-22b": "Codestral-22B",
    "gemini2.5-flash": "Gemini2.5-Flash",
    "gemini2.5-pro": "Gemini2.5-Pro",
    "gpt-oss-20b": "GPT-OSS-20B",
    "llama3.2-3b": "LLaMa3.2-3B",
    "llama3.3-70b": "LLaMa3.3-70B",
    "qwen3-coder-30b": "Qwen3-Coder-30B",
}


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def signature(item: dict) -> str:
    payload = "\x1f".join(norm(item.get(k)) for k in ("Title", "Description", "Objective"))
    if not payload.strip("\x1f"):
        payload = "\x1f".join(norm(item.get(k)) for k in ("title", "description", "objective"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def display_text(item: dict) -> str:
    vals = []
    for upper, lower in (("Title", "title"), ("Description", "description"), ("Objective", "objective")):
        vals.append(str(item.get(upper, item.get(lower, "")) or "").strip())
    return " ".join(vals)


def canonical_source(raw: str) -> str:
    value = raw.casefold().replace("_", ".")
    value = value.replace("llama", "llama").replace("c0der", "coder")
    value = re.sub(r"[^a-z0-9.]+", "-", value).strip("-")
    tests = [
        ("gemini2.5-pro", "Gemini2.5-Pro"),
        ("gemini2.5-flash", "Gemini2.5-Flash"),
        ("gpt-oss", "GPT-OSS-20B"),
        ("llama3.2", "LLaMa3.2-3B"),
        ("llama3.3", "LLaMa3.3-70B"),
        ("qwen3-coder", "Qwen3-Coder-30B"),
        ("codestral", "Codestral-22B"),
    ]
    for token, label in tests:
        if token in value:
            return label
    return raw


def load_human() -> tuple[pd.DataFrame, dict[str, list[dict]]]:
    records: list[dict] = []
    source_items: dict[str, list[dict]] = {}
    files = sorted(HUMAN.glob("Human */*.json"))
    for path in files:
        rater = path.parent.name
        data = json.loads(path.read_text(encoding="utf-8"))
        source = canonical_source(data["process_name"])
        if source not in source_items:
            source_items[source] = data["oracle"]
        for position, item in enumerate(data["oracle"]):
            records.append(
                {
                    "source_model": source,
                    "position": position,
                    "row_ref": item.get("row_ref", ""),
                    "test_case_id": item.get("original_id", ""),
                    "signature": signature(item),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "objective": item.get("objective", ""),
                    "rater": rater,
                    "label": item.get("decision", ""),
                }
            )
    df = pd.DataFrame(records)
    return df, source_items


def fleiss_kappa(matrix: np.ndarray) -> float:
    n, k = matrix.shape
    raters = matrix.sum(axis=1)
    if not np.all(raters == raters[0]):
        raise ValueError("Fleiss kappa requires a fixed number of ratings per item")
    m = raters[0]
    p_i = ((matrix * matrix).sum(axis=1) - m) / (m * (m - 1))
    p_bar = p_i.mean()
    p_j = matrix.sum(axis=0) / (n * m)
    p_e = (p_j * p_j).sum()
    return float((p_bar - p_e) / (1 - p_e)) if p_e != 1 else 1.0


def cohen_kappa_score(a, b) -> float:
    a, b = list(a), list(b)
    if len(a) != len(b) or not a:
        return float("nan")
    labels = sorted(set(a) | set(b))
    observed = sum(x == y for x, y in zip(a, b)) / len(a)
    pa = Counter(a)
    pb = Counter(b)
    expected = sum((pa[x] / len(a)) * (pb[x] / len(b)) for x in labels)
    return (observed - expected) / (1 - expected) if expected != 1 else 1.0


def human_agreement(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pivot = df.pivot(index=["source_model", "row_ref"], columns="rater", values="label").reset_index()
    raters = [c for c in pivot.columns if c.startswith("Human ")]
    rows = []
    consensus_rows = []
    for source, group in pivot.groupby("source_model", sort=True):
        labels = group[raters].to_numpy()
        counts = np.array([[np.sum(row == "Unique"), np.sum(row == "Similar")] for row in labels])
        pairwise = {}
        for i in range(len(raters)):
            for j in range(i + 1, len(raters)):
                pairwise[f"kappa_{raters[i].replace(' ', '')}_{raters[j].replace(' ', '')}"] = cohen_kappa_score(labels[:, i], labels[:, j])
        rows.append({"source_model": source, "items": len(group), "fleiss_kappa": fleiss_kappa(counts), **pairwise})
        for (_, item), row_labels in zip(group[["source_model", "row_ref"]].iterrows(), labels):
            votes = Counter(row_labels)
            consensus_rows.append({
                "source_model": source,
                "row_ref": item["row_ref"],
                "consensus": votes.most_common(1)[0][0],
                "unique_votes": votes["Unique"],
                "similar_votes": votes["Similar"],
                "unanimous": len(votes) == 1,
            })
    # Overall kappa across all 1,074 items.
    labels = pivot[raters].to_numpy()
    counts = np.array([[np.sum(row == "Unique"), np.sum(row == "Similar")] for row in labels])
    overall = {"source_model": "Overall", "items": len(pivot), "fleiss_kappa": fleiss_kappa(counts)}
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            overall[f"kappa_{raters[i].replace(' ', '')}_{raters[j].replace(' ', '')}"] = cohen_kappa_score(labels[:, i], labels[:, j])
    rows.append(overall)
    consensus = pd.DataFrame(consensus_rows)
    details = df.merge(consensus, on=["source_model", "row_ref"], how="left")
    return pd.DataFrame(rows), consensus, details


def classification_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    # Positive class is Similar: the decision that removes a case.
    truth = [x == "Similar" for x in y_true]
    pred = [x == "Similar" for x in y_pred]
    tn = sum(not t and not p for t, p in zip(truth, pred))
    fp = sum(not t and p for t, p in zip(truth, pred))
    fn = sum(t and not p for t, p in zip(truth, pred))
    tp = sum(t and p for t, p in zip(truth, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {
        "n": len(truth),
        "tn_unique_retained": int(tn),
        "fp_unique_removed": int(fp),
        "fn_similar_retained": int(fn),
        "tp_similar_removed": int(tp),
        "precision_similar": float(precision),
        "recall_similar": float(recall),
        "f1_similar": float(f1),
        "balanced_accuracy": float((recall + specificity) / 2),
        "cohen_kappa": float(cohen_kappa_score(truth, pred)),
    }


def build_item_table(df: pd.DataFrame, consensus: pd.DataFrame) -> pd.DataFrame:
    base = (
        df.sort_values(["source_model", "position", "rater"])
        .drop_duplicates(["source_model", "row_ref"])
        [["source_model", "position", "row_ref", "test_case_id", "signature", "title", "description", "objective"]]
    )
    wide = df.pivot(index=["source_model", "row_ref"], columns="rater", values="label").reset_index()
    return base.merge(wide, on=["source_model", "row_ref"]).merge(consensus, on=["source_model", "row_ref"])


def tfidf_baseline(item_table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = []
    predictions = []
    thresholds = [0.30, 0.50, 0.70]
    for source, group in item_table.sort_values("position").groupby("source_model", sort=True):
        group = group.sort_values("position").reset_index(drop=True)
        texts = (group["title"] + " " + group["description"] + " " + group["objective"]).fillna("").tolist()
        vectors = tfidf_vectors(texts)
        for threshold in thresholds:
            retained: list[int] = []
            pred: list[str] = []
            max_sims: list[float] = []
            for i in range(len(group)):
                if not retained:
                    label, max_sim = "Unique", 0.0
                    retained.append(i)
                else:
                    sims = [cosine_sparse(vectors[i], vectors[j]) for j in retained]
                    max_sim = float(max(sims)) if sims else 0.0
                    label = "Similar" if max_sim >= threshold else "Unique"
                    if label == "Unique":
                        retained.append(i)
                pred.append(label)
                max_sims.append(max_sim)
            metric = classification_metrics(group["consensus"].tolist(), pred)
            metrics.append({"source_model": source, "threshold": threshold, **metric})
            for idx, label in enumerate(pred):
                predictions.append({
                    "source_model": source,
                    "row_ref": group.loc[idx, "row_ref"],
                    "threshold": threshold,
                    "prediction": label,
                    "max_similarity_to_retained": max_sims[idx],
                    "consensus": group.loc[idx, "consensus"],
                })
    # Micro aggregate for each fixed analysis threshold.
    pred_df = pd.DataFrame(predictions)
    for threshold, group in pred_df.groupby("threshold"):
        metrics.append({"source_model": "Overall", "threshold": threshold, **classification_metrics(group["consensus"].tolist(), group["prediction"].tolist())})
    return pd.DataFrame(metrics), pred_df


def tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    """Lowercase word unigram+bigram TF-IDF with sublinear TF and L2 norm."""
    docs: list[Counter] = []
    document_frequency = Counter()
    for text in texts:
        tokens = re.findall(r"[a-z0-9]+", text.casefold())
        terms = tokens + [f"{a}__{b}" for a, b in zip(tokens, tokens[1:])]
        counts = Counter(terms)
        docs.append(counts)
        document_frequency.update(counts.keys())
    n = len(docs)
    vectors = []
    for counts in docs:
        vector = {
            term: (1.0 + math.log(freq)) * (math.log((1.0 + n) / (1.0 + document_frequency[term])) + 1.0)
            for term, freq in counts.items()
        }
        magnitude = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        vectors.append({term: value / magnitude for term, value in vector.items()})
    return vectors


def cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(term, 0.0) for term, value in a.items())


def infer_source_from_process(name: str, total: int) -> str | None:
    if "Test-Scenarios" in name:
        return canonical_source(name.split("Test-Scenarios", 1)[0])
    # Early 169-case experiments predate the systematic naming convention.
    if total == 169 and name:
        return "LLaMa3.2-3B"
    return None


def infer_strategy(record: dict, process_name: str) -> str:
    output = record.get("processes", {}).get("test_case_optimization", {}).get("output", {})
    explicit = output.get("optimization_type", "")
    name = process_name.casefold()
    if explicit:
        return str(explicit).capitalize()
    if "bulk" in name:
        return "Bulk"
    if "parallel" in name:
        return "Parallel"
    return "Serial"


def optimizer_metrics(item_table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = json.loads((DATA / "calculation_db.coverage_db.json").read_text(encoding="utf-8"))
    summary = pd.read_csv(DATA / "optimization_record_analysis_output" / "optimization_record_summary.csv")
    human_by_source = {s: g.sort_values("position") for s, g in item_table.groupby("source_model")}
    metric_rows, decision_rows = [], []
    for _, meta in summary.iterrows():
        idx = int(meta["record_index"])
        if idx >= len(records):
            continue
        rec = records[idx]
        proc = rec.get("processes", {}).get("test_case_optimization", {})
        out = proc.get("output", {}) if isinstance(proc, dict) else {}
        unique = out.get("unique_test_cases", []) or []
        similar_items = out.get("similar_test_cases", []) or []
        duplicates = [x.get("DuplicateCase", x) if isinstance(x, dict) else {} for x in similar_items]
        total = len(unique) + len(duplicates)
        name = str(meta.get("process_name", "") or "")
        source = infer_source_from_process(name, total)
        if source not in human_by_source or total != len(human_by_source[source]):
            continue
        pred_by_sig: dict[str, list[str]] = defaultdict(list)
        for item in unique:
            pred_by_sig[signature(item)].append("Unique")
        for item in duplicates:
            pred_by_sig[signature(item)].append("Similar")
        group = human_by_source[source]
        # Deterministic occurrence matching handles the one duplicated GPT-OSS text.
        cursors = Counter()
        y_true, y_pred = [], []
        unmatched = 0
        for _, item in group.iterrows():
            sig = item["signature"]
            pos = cursors[sig]
            labels = pred_by_sig.get(sig, [])
            if pos >= len(labels):
                unmatched += 1
                continue
            label = labels[pos]
            cursors[sig] += 1
            y_true.append(item["consensus"])
            y_pred.append(label)
            decision_rows.append({
                "record_index": idx,
                "process_name": name,
                "source_model": source,
                "optimizer_model": meta.get("used_model", ""),
                "strategy": infer_strategy(rec, name),
                "row_ref": item["row_ref"],
                "consensus": item["consensus"],
                "prediction": label,
            })
        if not y_true:
            continue
        metric_rows.append({
            "record_index": idx,
            "process_name": name,
            "source_model": source,
            "optimizer_model": meta.get("used_model", ""),
            "strategy": infer_strategy(rec, name),
            "unmatched_items": unmatched,
            **classification_metrics(y_true, y_pred),
        })
    return pd.DataFrame(metric_rows), pd.DataFrame(decision_rows)


def write_markdown_summary(agreement: pd.DataFrame, consensus: pd.DataFrame, baseline: pd.DataFrame, optimizer: pd.DataFrame) -> None:
    overall = agreement[agreement.source_model == "Overall"].iloc[0]
    c_counts = consensus.consensus.value_counts()
    b = baseline[(baseline.source_model == "Overall") & (baseline.threshold == 0.50)].iloc[0]
    lines = [
        "# Reproducible Revision Analysis Summary",
        "",
        f"- Human Oracle items: {len(consensus):,} across {consensus.source_model.nunique()} source-model suites.",
        f"- Evaluators: 3; all evaluated the same items; majority vote has no binary-label ties.",
        f"- Consensus: {int(c_counts.get('Unique', 0))} Unique and {int(c_counts.get('Similar', 0))} Similar.",
        f"- Overall Fleiss' kappa: {overall.fleiss_kappa:.4f}.",
        f"- TF-IDF threshold 0.50: precision={b.precision_similar:.4f}, recall={b.recall_similar:.4f}, F1={b.f1_similar:.4f}, balanced accuracy={b.balanced_accuracy:.4f}, false removals={int(b.fp_unique_removed)}.",
        f"- Matched optimizer configurations with item-level metrics: {len(optimizer)}.",
        "",
        "The analysis evaluates three fixed TF-IDF thresholds (0.30, 0.50, 0.70); the archive does not establish that they were chosen before the Human Oracle results were examined.",
        "The positive class is Similar/Removed; therefore false positives are consensus-Unique cases removed by an optimizer.",
    ]
    (OUT / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    human, _ = load_human()
    agreement, consensus, details = human_agreement(human)
    item_table = build_item_table(human, consensus)
    baseline, baseline_predictions = tfidf_baseline(item_table)
    optimizer, optimizer_decisions = optimizer_metrics(item_table)

    agreement.to_csv(OUT / "human_agreement.csv", index=False, float_format="%.6f")
    item_table.to_csv(OUT / "human_oracle_item_level.csv", index=False)
    details.to_csv(OUT / "human_oracle_ratings_long.csv", index=False)
    baseline.to_csv(OUT / "tfidf_baseline_metrics.csv", index=False, float_format="%.6f")
    baseline_predictions.to_csv(OUT / "tfidf_baseline_predictions.csv", index=False, float_format="%.6f")
    optimizer.to_csv(OUT / "optimizer_item_level_metrics.csv", index=False, float_format="%.6f")
    optimizer_decisions.to_csv(OUT / "optimizer_item_level_decisions.csv", index=False)
    write_markdown_summary(agreement, consensus, baseline, optimizer)
    print((OUT / "analysis_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
