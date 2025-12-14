---
title: "T[root]H Mentor Report"
subtitle: "Master Assessment Summary"
author: "{{apprentice_name}}"
date: "{{submitted_date}}"
---

# Snapshot
- **Biblical Knowledge:** **{{overall_mc_percent}}%** — *{{knowledge_band}}*
- **Spiritual Life (Open-ended):** **{{overall_open_level}}**
- **Top Strengths:** {{top_strengths | join(", ")}}
- **Top Gaps:** {{top_gaps | join(", ")}}

---

# Category Scores (0–10)
{% for c in categories %}
- **{{c.name}}** — {{c.score}}/10 (Level: {{c.level}})
{% endfor %}

---

# Biblical Knowledge Breakdown
- **Total:** {{mc.total_questions}} · **Correct:** {{mc.correct_count}} · **Accuracy:** {{overall_mc_percent}}%
{% for t in knowledge_topics %}
- **{{t.topic}}:** {{t.correct}} / {{t.total}} ({{t.percent}}%) — {{t.note}}
{% endfor %}

---

# Open‑Ended Insights (by Category)
{% for i in open_insights %}
## {{i.category}} — *{{i.level}}*
**Evidence:** {{i.evidence}}

**Discernment:** {{i.discernment}}

**Scripture Anchor:** {{i.scripture_anchor}}

**Mentor Moves:** 
{% if i.mentor_moves and i.mentor_moves | length > 0 %}
{% for move in i.mentor_moves %}- {{ move }}
{% endfor %}
{% else %}- (No suggested moves yet)
{% endif %}

---
{% endfor %}

# Four‑Week Plan
**Weekly Rhythm**
{% for r in four_week.rhythm %}- {{r}}{% endfor %}

**Checkpoints**
{% for cp in four_week.checkpoints %}- {{cp}}{% endfor %}

---

# Conversation Starters
{% for q in starters %}- {{q}}{% endfor %}

---

# Recommended Resources
{% for res in resources %}- **{{res.title}}** — {{res.why}} ({{res.type}}){% endfor %}