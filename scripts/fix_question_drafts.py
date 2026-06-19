#!/usr/bin/env python3
"""Fix confirmed issues in all 12 question draft files.

Removes:
  - Exact duplicates (TD Expert Q99-155, NT Challenger Q81)
  - Questions with confirmed wrong answers
  - Contested denominational T/F questions
  - DL Beginner questions with obvious joke distractors
"""

import json
from pathlib import Path

DRAFTS_DIR = Path(__file__).parent / "question_drafts"


def load(fname: str) -> list[dict]:
    return json.loads((DRAFTS_DIR / fname).read_text())


def save(fname: str, questions: list[dict]) -> None:
    (DRAFTS_DIR / fname).write_text(json.dumps(questions, indent=2, ensure_ascii=False))


def remove_by_text(questions: list[dict], texts: list[str]) -> tuple[list[dict], int]:
    texts_lower = {t.lower().strip() for t in texts}
    kept = [q for q in questions if q.get("question", "").lower().strip() not in texts_lower]
    return kept, len(questions) - len(kept)


def dedup_exact(questions: list[dict]) -> tuple[list[dict], int]:
    """Remove exact duplicate questions keeping the first occurrence."""
    seen = set()
    kept = []
    for q in questions:
        key = q.get("question", "").strip().lower()
        if key not in seen:
            seen.add(key)
            kept.append(q)
    return kept, len(questions) - len(kept)


# ─── Wrong-answer removals by question text ────────────────────────────────

NT_BEGINNER_REMOVE = [
    # NT never names Jesus's sisters; Mary/Martha are Lazarus's sisters (John 11)
    "Which of these women was NOT one of Jesus' sisters mentioned in the Gospels?",
]

NT_EXPERT_REMOVE = [
    # Eph 2:6 explicitly says believers ARE raised and seated in heavenly places with Christ
    "Which of the following is NOT a specific 'heavenly place' (en tois epouraniois) Paul refers to in Ephesians, describing the believer's position or spiritual realities?",
    # John 21:17 — Jesus switches to phileo on the third question, so "Jesus asks agape all three times" is False; answer "True" is wrong
    "True or False: In John 21, after His resurrection, Jesus asks Peter three times, 'Do you love me?' (agape), and Peter consistently responds with a less intense form of love, 'I love you' (phileo).",
    # Eph 4:11 explicitly lists "shepherds and teachers" (= pastors and teachers); correct answer claiming they're NOT listed is wrong
    "In Ephesians 4:11, Paul lists various gifted individuals given to the church for its equipping. Which of the following is NOT explicitly mentioned in this list?",
    # "prologue" framing is ambiguous and "Angels only" excludes Moses/Levitical priesthood which Hebrews also addresses
    "The prologue of Hebrews argues for Christ's superiority over which of the following figures or concepts?",
]

OT_BEGINNER_REMOVE = [
    # 2 Kings 2:11: whirlwind took Elijah; chariot of fire only separated them; statement is misleading
    "Elijah was taken to heaven in a whirlwind by a chariot of fire.",
    # Contested hermeneutical position (young-earth vs day-age vs other interpretations)
    "The book of Genesis describes the creation of the world in seven literal 24-hour days.",
]

OT_CHALLENGER_REMOVE = [
    # Temple destroyed ~587 BC, dedicated ~516 BC ≈ 71 years; "exactly 70 years" is inaccurate
    "The book of Ezra records that the dedication of the rebuilt temple was celebrated with great joy and sacrifices, exactly 70 years after its destruction.",
    # Daniel 7:5 explicitly describes the bear with three ribs; goat with prominent horn is Daniel 8 — correct answer (d=bear) is wrong
    "In Daniel 7, Daniel sees four beasts representing four kingdoms. Which of the following is NOT one of the animals described?",
    # Job 1:15 states no direction; fabricated geographical detail
    "From which direction did the Sabeans come to raid Job's oxen and donkeys and kill his servants?",
]

OT_EXPERT_REMOVE = [
    # Ruth 1:4 says Orpah married Chilion; correct answer claiming she didn't marry anyone is wrong
    "What was the name of the man who married Naomi's daughter-in-law Orpah, according to the book of Ruth?",
]

DL_CHALLENGER_REMOVE = [
    # Gal 6:1 says only "spirit of gentleness"; correct answer "Both A and B" includes "firm discipline" which isn't in the text
    "Paul, in Galatians 6:1, gives instructions on how to restore a brother caught in a transgression. What specific attitude or spirit should the one doing the restoring possess?",
    # "In him we live and move and have our being" is Epimenides; Aratus is for "we are his offspring" — correct answer (d=Aratus) is wrong
    "In the book of Acts, when Paul is in Athens and addresses the Areopagus, he quotes from one of their own poets, stating, 'For in him we live and move and have our being.' Which specific Greek poet is traditionally associated with this quotation?",
]

TD_BEGINNER_REMOVE = [
    # Contested Calvinist vs Wesleyan/Arminian position; "False" favors one tradition
    "True or False: The Bible teaches that human free will means humans can choose to believe in Christ without any divine enablement.",
]

TD_CHALLENGER_REMOVE = [
    # Impassibility: classical doctrine does say God doesn't suffer, but question oversimplifies a contested theological area
    "The concept of 'divine impassibility' traditionally states that God is incapable of suffering or being affected by external forces.",
    # Kenosis: "emptying of divine attributes" is the heterodox view; orthodox kenosis is self-limitation not loss of attributes
    "The theological term 'kenosis' (from Philippians 2:7) refers to Christ's emptying himself of his divine attributes during the incarnation.",
    # Impassibility does not imply inability to empathize — misleading logical inference
    "The 'doctrine of divine impassibility' teaches that God is unaffected by suffering, which implies He cannot truly empathize with human pain.",
    # Fabricated document: it's the Stuttgart Declaration of Guilt, not the "Munich Statement"
    "The 'Munich Statement' (1945) was a declaration by German Protestant leaders acknowledging guilt for failing to resist Nazism.",
    # Conflates impassibility (not moved by passions) with immutability (not changing)
    "The doctrine of 'impassibility' states that God is incapable of changing or being affected by external events.",
]

# DL Beginner: after reviewing the current file, the obvious-joke options described in earlier
# review notes ("Going on vacation", "Sending emails") are not present in the current version.
# Skipping removals — no action needed.
DL_BEGINNER_OBVIOUS_REMOVE: list[str] = []


def fix_file(fname: str, remove_texts: list[str], also_dedup: bool = False) -> None:
    questions = load(fname)
    before = len(questions)

    removed_wrong = 0
    if remove_texts:
        questions, removed_wrong = remove_by_text(questions, remove_texts)

    removed_dup = 0
    if also_dedup:
        questions, removed_dup = dedup_exact(questions)

    after = len(questions)
    save(fname, questions)
    print(
        f"  {fname}: {before} → {after} "
        f"(-{removed_wrong} wrong/-{removed_dup} dup = -{removed_wrong + removed_dup} total)"
    )


def fix_td_expert_duplicates() -> None:
    """TD Expert has indices 99-155 as exact duplicates of 43-98 (57 questions)."""
    fname = "questions_draft_theology_doctrine_expert.json"
    questions = load(fname)
    before = len(questions)
    questions, removed = dedup_exact(questions)
    after = len(questions)
    save(fname, questions)
    print(f"  {fname}: {before} → {after} (-{removed} exact duplicates)")


def fix_nt_challenger_duplicate() -> None:
    """NT Challenger has one exact duplicate at index 81."""
    fname = "questions_draft_new_testament_challenger.json"
    questions = load(fname)
    before = len(questions)
    questions, removed = dedup_exact(questions)
    after = len(questions)
    save(fname, questions)
    print(f"  {fname}: {before} → {after} (-{removed} exact duplicates)")


def fix_remaining_near_duplicates() -> None:
    """Apply dedup to all files to catch any remaining exact text duplicates."""
    files = [
        "questions_draft_discipleship_living_expert.json",
        "questions_draft_new_testament_beginner.json",
        "questions_draft_new_testament_expert.json",
        "questions_draft_old_testament_beginner.json",
        "questions_draft_old_testament_expert.json",
        "questions_draft_discipleship_living_beginner.json",
    ]
    for fname in files:
        questions = load(fname)
        before = len(questions)
        questions, removed = dedup_exact(questions)
        after = len(questions)
        save(fname, questions)
        if removed:
            print(f"  {fname}: {before} → {after} (-{removed} exact duplicates)")
        else:
            print(f"  {fname}: {before} (no duplicates found)")


def main() -> None:
    print("=== Fixing question draft files ===\n")

    print("-- Exact duplicate removal --")
    fix_td_expert_duplicates()
    fix_nt_challenger_duplicate()
    fix_remaining_near_duplicates()

    print("\n-- Wrong-answer / contested question removal --")
    fix_file("questions_draft_new_testament_beginner.json", NT_BEGINNER_REMOVE)
    fix_file("questions_draft_new_testament_expert.json", NT_EXPERT_REMOVE)
    fix_file("questions_draft_old_testament_beginner.json", OT_BEGINNER_REMOVE)
    fix_file("questions_draft_old_testament_challenger.json", OT_CHALLENGER_REMOVE)
    fix_file("questions_draft_old_testament_expert.json", OT_EXPERT_REMOVE)
    fix_file("questions_draft_discipleship_living_challenger.json", DL_CHALLENGER_REMOVE)
    fix_file("questions_draft_theology_doctrine_beginner.json", TD_BEGINNER_REMOVE)
    fix_file("questions_draft_theology_doctrine_challenger.json", TD_CHALLENGER_REMOVE)

    print("\n-- DL Beginner obvious-option removal --")
    fix_file("questions_draft_discipleship_living_beginner.json", DL_BEGINNER_OBVIOUS_REMOVE)

    print("\n=== Final counts ===")
    total = 0
    for f in sorted(DRAFTS_DIR.glob("questions_draft_*.json")):
        questions = json.loads(f.read_text())
        n = len(questions)
        total += n
        print(f"  {f.name}: {n}")
    print(f"\n  TOTAL: {total}")


if __name__ == "__main__":
    main()
