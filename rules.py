"""
Rule Engine for RuleBot
- Matches a user's message to the best Q&A for a given bot.
- Uses: keywords (CSV), optional regex (prefix with `re:` or wrap in /slashes/),
  priority weighting, exact-match bonus, and similarity scoring.
- Minimal deps: stdlib only. Works with the db.py already set up.
"""

from __future__ import annotations
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Any, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import fetch_bot_by_slug, fetch_qna

# ---- Tunable weights ---------------------------------------------------------

KW_WORD_POINTS = 12       # per matched keyword/phrase
KW_REGEX_POINTS = 14      # per matched regex pattern
EXACT_MATCH_BONUS = 40    # if user's text == question (normalized)
PRIORITY_WEIGHT = 2       # multiplied by qna['priority']
SIMILARITY_WEIGHT = 30    # similarity ratio (0..1) * this weight
SIMILARITY_MIN_FOR_MATCH = 0.55  # below this, similarity alone won't count as a match

DEBUG = os.getenv("RULEBOT_DEBUG") == "1"

# ---- Helpers ----------------------------------------------------------------

_norm_ws = re.compile(r"\s+")
_strip_chars = re.compile(r"[^a-z0-9\s]+")

def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation (keep spaces), collapse whitespace."""
    t = text.strip().lower()
    t = _strip_chars.sub(" ", t)
    t = _norm_ws.sub(" ", t)
    return t

def tokenize(text: str) -> List[str]:
    return [tok for tok in text.split(" ") if tok]

def parse_keywords(keywords: Optional[str]) -> Tuple[List[str], List[re.Pattern]]:
    """
    Split a CSV keywords string into:
      - plain phrases (list[str])
      - compiled regex patterns (list[Pattern])
    Conventions:
      - 're:^foo$'   -> regex
      - '/foo|bar/i' -> regex (with trailing '/i' for IGNORECASE)
      - plain words/phrases -> phrase matches
    """
    plain: List[str] = []
    patterns: List[re.Pattern] = []
    if not keywords:
        return plain, patterns

    for raw in keywords.split(","):
        kw = raw.strip()
        if not kw:
            continue

        # re: pattern
        if kw.startswith("re:"):
            pat = kw[3:].strip()
            try:
                patterns.append(re.compile(pat, flags=re.IGNORECASE))
            except re.error:
                # ignore bad regex silently
                pass
            continue

        # /pattern/flags
        if len(kw) >= 2 and kw.startswith("/") and kw.count("/") >= 2:
            # find last slash
            last = kw.rfind("/")
            pat = kw[1:last]
            flags_str = kw[last + 1:].lower()
            flags = 0
            if "i" in flags_str:
                flags |= re.IGNORECASE
            try:
                patterns.append(re.compile(pat, flags=flags))
            except re.error:
                pass
            continue

        # otherwise a plain phrase
        plain.append(kw.lower())

    return plain, patterns

def phrase_in_text(text: str, phrase: str) -> bool:
    """
    True if 'phrase' appears in 'text'.
    If phrase is a single token -> use word boundary match.
    If multi-token -> substring check on normalized strings.
    """
    if not phrase:
        return False
    toks = phrase.split()
    if len(toks) == 1:
        # whole-word search
        return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
    # multi-word phrase -> substring on normalized text
    return phrase in text

# ---- Scoring ----------------------------------------------------------------

def score_qna(user_norm: str, qna_row: Any) -> Tuple[int, Dict[str, Any]]:
    """
    Compute a score for a single Q&A row.
    Returns (score, details)
    details includes: matched_keywords, matched_regex, exact, ratio
    """
    score = 0
    details = {
        "matched_keywords": [],
        "matched_regex": [],
        "exact": False,
        "ratio": 0.0,
        "priority": int(qna_row["priority"]) if qna_row["priority"] is not None else 0,
    }

    q_norm = normalize_text(qna_row["question"])
    if user_norm == q_norm:
        score += EXACT_MATCH_BONUS
        details["exact"] = True

    # Keywords / regex
    plain, patterns = parse_keywords(qna_row["keywords"])
    for kw in plain:
        if phrase_in_text(user_norm, kw):
            score += KW_WORD_POINTS
            details["matched_keywords"].append(kw)

    for pat in patterns:
        if pat.search(user_norm):
            score += KW_REGEX_POINTS
            details["matched_regex"].append(pat.pattern)

    # Similarity
    ratio = SequenceMatcher(None, user_norm, q_norm).ratio()
    details["ratio"] = ratio
    score += int(round(SIMILARITY_WEIGHT * ratio))

    # Priority
    score += details["priority"] * PRIORITY_WEIGHT

    return score, details

# ---- Public API --------------------------------------------------------------

def match_rule(bot_slug: str, user_message: str) -> Dict[str, Any]:
    """
    Given a bot slug and user message, return the best response dict:
        {
          "matched": bool,
          "answer": str,
          "question": Optional[str],
          "qna_id": Optional[int],
          "confidence": int,
          "debug": {...}   # only if RULEBOT_DEBUG=1
        }
    """
    bot = fetch_bot_by_slug(bot_slug)
    if not bot:
        return {
            "matched": False,
            "answer": "Bot not found.",
            "question": None,
            "qna_id": None,
            "confidence": 0,
        }

    user_norm = normalize_text(user_message)
    qnas = fetch_qna(bot["id"])
    if not qnas:
        return {
            "matched": False,
            "answer": bot["fallback_message"],
            "question": None,
            "qna_id": None,
            "confidence": 0,
        }

    best_row = None
    best_score = -10**9
    best_details = None

    for row in qnas:
        s, details = score_qna(user_norm, row)
        if DEBUG:
            print(f"[DEBUG] QNA {row['id']} score={s} :: {details} :: Q='{row['question'][:70]}'")
        if s > best_score:
            best_score, best_row, best_details = s, row, details

    # Decide if it's a real match:
    kw_hits = len(best_details["matched_keywords"]) + len(best_details["matched_regex"])
    matched = (
        best_details["exact"]
        or kw_hits > 0
        or best_details["ratio"] >= SIMILARITY_MIN_FOR_MATCH
    )

    if not matched:
        return {
            "matched": False,
            "answer": bot["fallback_message"],
            "question": None,
            "qna_id": None,
            "confidence": max(0, best_score),
            "debug": best_details if DEBUG else None,
        }

    result = {
        "matched": True,
        "answer": best_row["answer"],
        "question": best_row["question"],
        "qna_id": int(best_row["id"]),
        "confidence": max(0, best_score),
    }
    if DEBUG:
        result["debug"] = best_details
    return result

def chat_once(bot_slug: str, user_message: str) -> str:
    """Convenience: return just the answer string (uses fallback if needed)."""
    r = match_rule(bot_slug, user_message)
    return r["answer"]

# ---- CLI tester --------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RuleBot CLI tester")
    parser.add_argument("--bot", "-b", default="cozy-cafe", help="Bot slug to chat with")
    args = parser.parse_args()

    print(f"RuleBot CLI — chatting with bot '{args.bot}'. Type 'exit' to quit.")
    if DEBUG:
        print("DEBUG mode is ON (RULEBOT_DEBUG=1) — showing scoring details.\n")

    try:
        while True:
            msg = input("> ").strip()
            if msg.lower() in {"exit", "quit"}:
                print("Bye!")
                break
            res = match_rule(args.bot, msg)
            print(res["answer"])
            if DEBUG and res.get("debug"):
                print(f"   [via] {res['debug']}")
    except (EOFError, KeyboardInterrupt):
        print("\nBye!")
