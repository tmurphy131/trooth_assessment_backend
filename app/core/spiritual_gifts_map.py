"""Canonical Spiritual Gifts question definitions & mapping.

This module centralizes the QUESTION_ITEMS (code, gift_slug, text) and the MAP
(gift_slug -> list[question_code]) so both seeding and scoring logic share a
single authoritative source.

Validation helpers ensure integrity (72 total items, 24 gifts * 3 each, full
coverage, no duplicates). Importing this module will raise if invariants break.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass(frozen=True)
class SpiritualGiftQuestion:
    code: str
    gift_slug: str
    text: str

# Each tuple: (code, gift_slug, text)
QUESTION_ITEMS: List[Tuple[str, str, str]] = [
    ("Q01", "wisdom", "I offer practical, Christlike solutions from Scripture."),
    ("Q02", "hospitality", "I enjoy creating warm, welcoming spaces for people."),
    ("Q03", "evangelism", "I naturally guide conversations toward the gospel."),
    ("Q04", "leadership", "People look to me for direction when plans are unclear."),
    ("Q05", "faith", "My faith often inspires courage in others."),
    ("Q06", "helps", "I willingly do unnoticed tasks to meet needs."),
    ("Q07", "teaching", "People say I make complex ideas understandable."),
    ("Q08", "prophecy", "I boldly speak Biblical truth to bring clarity."),
    ("Q09", "craftsmanship", "I enjoy building/making things that serve ministry."),
    ("Q10", "pastor-shepherd", "I check in on people’s well‑being and follow up consistently."),
    ("Q11", "intercession", "I maintain prayer lists and pray with expectancy."),
    ("Q12", "mercy", "I feel deep compassion for those in pain."),
    ("Q13", "knowledge", "I connect Scriptures to explain complex situations."),
    ("Q14", "administration", "I track details so teams deliver reliably."),
    ("Q15", "music-worship", "I steward musical/creative skills for God’s glory."),
    ("Q16", "healing", "I’m drawn to minister to the sick and hurting."),
    ("Q17", "service", "I prefer doing what’s needed over being noticed."),
    ("Q18", "giving", "I enjoy resourcing ministry beyond the minimum."),
    ("Q19", "discernment", "I often perceive motives behind words or actions."),
    ("Q20", "missionary", "I adapt to new environments for the gospel."),
    ("Q21", "tongues-interpretation", "I pray in a spiritual language privately."),
    ("Q22", "exhortation", "I encourage others with timely, Scripture‑rooted words."),
    ("Q23", "leadership", "I align tasks and people to keep the big picture in focus."),
    ("Q24", "faith", "I confidently trust God for unseen outcomes."),
    ("Q25", "miracles", "I expect God to act beyond natural limitations."),
    ("Q26", "service", "I organize my time to consistently meet tangible needs."),
    ("Q27", "exhortation", "I help others take practical next steps of faith."),
    ("Q28", "craftsmanship", "I plan and execute hands‑on projects well."),
    ("Q29", "prophecy", "I sense timely messages God wants emphasized."),
    ("Q30", "pastor-shepherd", "I’m drawn to nurture those working through life issues."),
    ("Q31", "music-worship", "I lead or support musical worship effectively."),
    ("Q32", "helps", "I feel satisfied when practical work enables the mission."),
    ("Q33", "intercession", "I feel burdened to pray until breakthrough comes."),
    ("Q34", "evangelism", "I explain salvation clearly to non‑Christians."),
    ("Q35", "administration", "I design systems that make work efficient."),
    ("Q36", "giving", "I plan my finances to give generously to God’s work."),
    ("Q37", "discernment", "I can identify truth from error in confusing situations."),
    ("Q38", "wisdom", "I can apply Biblical principles fruitfully in grey areas."),
    ("Q39", "miracles", "I have prayed and seen outcomes shift in remarkable ways."),
    ("Q40", "teaching", "I enjoy studying and communicating Biblical truth."),
    ("Q41", "knowledge", "I often clarify confusion by bringing relevant truth."),
    ("Q42", "hospitality", "I notice newcomers and help them feel at home."),
    ("Q43", "mercy", "I advocate for the vulnerable and overlooked."),
    ("Q44", "leadership", "I naturally motivate groups to move toward a clear vision."),
    ("Q45", "missionary", "I build relationships that cross cultural boundaries."),
    ("Q46", "faith", "I choose obedience even when results aren’t visible."),
    ("Q47", "healing", "I pray for physical/mental healing with persistent faith."),
    ("Q48", "pastor-shepherd", "I notice and respond to spiritual and emotional needs."),
    ("Q49", "tongues-interpretation", "Praying in tongues is encouraging and important to me."),
    ("Q50", "service", "I’m quick to volunteer for practical tasks."),
    ("Q51", "miracles", "Others seek my faith when situations appear impossible."),
    ("Q52", "intercession", "I regularly “stand in the gap” for people in prayer."),
    ("Q53", "prophecy", "I feel compelled to confront error with Scripture."),
    ("Q54", "apostleship", "I thrive in breaking new ground for the church."),
    ("Q55", "exhortation", "People say my feedback lifts and directs them."),
    ("Q56", "knowledge", "I retain Biblical facts and contexts that help others."),
    ("Q57", "helps", "I enjoy supporting others so ministry succeeds."),
    ("Q58", "music-worship", "I help others engage God through music/arts."),
    ("Q59", "discernment", "I sense when something sounds off spiritually or doctrinally."),
    ("Q60", "administration", "I organize people and tasks to hit goals."),
    ("Q61", "apostleship", "I start or pioneer new ministries."),
    ("Q62", "hospitality", "I think about details that make gatherings comfortable."),
    ("Q63", "healing", "People report healing after I intercede for them."),
    ("Q64", "giving", "I notice strategic opportunities to fund Kingdom impact."),
    ("Q65", "evangelism", "I actively look for opportunities to share Jesus."),
    ("Q66", "teaching", "I structure content so others understand Scripture."),
    ("Q67", "apostleship", "I recruit and equip teams to launch new work."),
    ("Q68", "wisdom", "People seek my counsel for next steps."),
    ("Q69", "craftsmanship", "I contribute skilled work (sets, spaces, tools)."),
    ("Q70", "tongues-interpretation", "God uses me to interpret what someone speaking in tongues is saying."),
    ("Q71", "missionary", "I’m drawn to reach people of different cultures."),
    ("Q72", "mercy", "I sit with people in their suffering without rushing them."),
]

MAP: Dict[str, List[str]] = {
    "leadership": ["Q04", "Q23", "Q44"],
    "pastor-shepherd": ["Q10", "Q30", "Q48"],
    "discernment": ["Q19", "Q37", "Q59"],
    "exhortation": ["Q22", "Q27", "Q55"],
    "hospitality": ["Q02", "Q42", "Q62"],
    "prophecy": ["Q08", "Q29", "Q53"],
    "knowledge": ["Q13", "Q41", "Q56"],
    "miracles": ["Q25", "Q39", "Q51"],
    "healing": ["Q16", "Q47", "Q63"],
    "helps": ["Q06", "Q32", "Q57"],
    "mercy": ["Q12", "Q43", "Q72"],
    "evangelism": ["Q03", "Q34", "Q65"],
    "faith": ["Q05", "Q24", "Q46"],
    "teaching": ["Q07", "Q40", "Q66"],
    "wisdom": ["Q01", "Q38", "Q68"],
    "intercession": ["Q11", "Q33", "Q52"],
    "service": ["Q17", "Q26", "Q50"],
    "tongues-interpretation": ["Q21", "Q49", "Q70"],
    "giving": ["Q18", "Q36", "Q64"],
    "missionary": ["Q20", "Q45", "Q71"],
    "apostleship": ["Q54", "Q61", "Q67"],
    "craftsmanship": ["Q09", "Q28", "Q69"],
    "administration": ["Q14", "Q35", "Q60"],
    "music-worship": ["Q15", "Q31", "Q58"],
}

# Derived lookups (useful for scoring logic)
CODE_TO_GIFT: Dict[str, str] = {code: gift for code, gift, _ in QUESTION_ITEMS}
GIFT_TO_CODES: Dict[str, List[str]] = MAP


def _validate_integrity() -> None:
    codes = [c for c, _g, _t in QUESTION_ITEMS]
    if len(codes) != 72:
        raise ValueError(f"Expected 72 items, found {len(codes)}")
    if len(set(codes)) != 72:
        raise ValueError("Duplicate question codes detected")
    # MAP coverage
    mapped = {c for lst in MAP.values() for c in lst}
    if set(codes) != mapped:
        missing = set(codes) - mapped
        extra = mapped - set(codes)
        raise ValueError(f"MAP coverage mismatch missing={missing} extra={extra}")
    # Each gift exactly 3
    bad = {g: lst for g, lst in MAP.items() if len(lst) != 3}
    if bad:
        raise ValueError(f"Gifts without exactly 3 codes: {bad}")

_validate_integrity()

__all__ = [
    "SpiritualGiftQuestion",
    "QUESTION_ITEMS",
    "MAP",
    "CODE_TO_GIFT",
    "GIFT_TO_CODES",
]
