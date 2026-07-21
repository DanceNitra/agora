"""Official MemoryAgentBench scoring — the exact functions from HUST-AI-HYZ/MemoryAgentBench
utils/eval_other_utils.py (normalize_answer + substring/exact match + max-over-ground-truths), copied
VERBATIM so our FactConsolidation number is scored identically to their published leaderboard. These four
functions depend only on the stdlib (string, re); the upstream file also pulls nltk/rouge/tiktoken, which
FactConsolidation's substring scoring does not use, so we vendor only what the metric needs.
"""
import string
import re


def normalize_answer(answer_text):
    text = answer_text.lower()
    text = ''.join(char for char in text if char not in string.punctuation)
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    text = ' '.join(text.split())
    return text


def drqa_exact_match_score(prediction, ground_truth):
    return normalize_answer(prediction) == normalize_answer(ground_truth)


def substring_exact_match_score(prediction, ground_truth):
    return normalize_answer(ground_truth) in normalize_answer(prediction)


def drqa_metric_max_over_ground_truths(metric_function, prediction, ground_truths):
    if isinstance(ground_truths, str):
        ground_truth_list = [ground_truths]
    elif ground_truths and isinstance(ground_truths[0], list):
        ground_truth_list = [gt for gt_sublist in ground_truths for gt in gt_sublist]
    else:
        ground_truth_list = ground_truths
    return max(metric_function(prediction, gt) for gt in ground_truth_list)
