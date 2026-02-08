# LLM Comparison & Enhanced Reports Design

**Branch**: `develop/llm-enhanced-reports`  
**Date**: January 31, 2026  
**Status**: In Development

---

## Table of Contents

1. [OpenAI vs Gemini Comparison](#1-openai-vs-gemini-comparison)
2. [Current Report Structure](#2-current-report-structure)
3. [Enhanced Full Report Proposal](#3-enhanced-full-report-proposal)
4. [Premium vs Free Tier Differentiation](#4-premium-vs-free-tier-differentiation)
5. [Implementation Plan](#5-implementation-plan)

---

## 1. OpenAI vs Gemini Comparison

### Performance Metrics (3-run average)

| Metric | OpenAI (gpt-4o-mini) | Vertex AI (gemini-2.0-flash) | Winner |
|--------|---------------------|------------------------------|--------|
| **Avg Latency** | 15,520 ms | 6,954 ms | ✅ Gemini (55% faster) |
| **JSON Validity** | 100% | 100% | Tie |
| **Schema Compliance** | 100% | 100% | Tie |
| **Est. Cost/call** | ~$0.0006 | ~$0.0001 | ✅ Gemini (~5x cheaper) |

### Output Quality Comparison

#### Health Assessment
| Aspect | OpenAI | Gemini |
|--------|--------|--------|
| Health Score | 72 (Maturing) | 69 (Stable) |
| Score Reasoning | More generous | More conservative |
| Band Assignment | Accurate to score | Accurate to score |

#### Strengths Identified
| OpenAI | Gemini |
|--------|--------|
| "Consistent prayer routine" | "Consistent prayer attempts" |
| "Regular Bible reading" | "Regular Bible reading" |
| "Participation in small group" | "Desire for deeper community" |

**Analysis**: OpenAI is more affirming ("consistent routine" vs "attempts"). Gemini is more nuanced (acknowledges "desire" rather than claiming achievement).

#### Gaps Identified
| OpenAI | Gemini |
|--------|--------|
| "Inconsistent prayer journaling" | "Inconsistent prayer life" |
| "Limited deep study of Scripture" | "Lack of deep Bible study methods" |
| "Lack of deeper fellowship discussions" | "Superficial fellowship" |

**Analysis**: Gemini uses more direct language ("superficial fellowship" vs "lack of deeper discussions"). Both are accurate but Gemini is more pastoral-direct.

#### Priority Action Comparison

**OpenAI**:
```json
{
  "title": "Enhance Prayer and Scripture Engagement",
  "description": "Improving your prayer life and deepening your engagement with Scripture will help you grow spiritually...",
  "steps": [
    "Set a specific time each day for prayer and stick to it.",
    "Choose a Bible study method to explore deeper meanings in Scripture.",
    "Engage with a mentor or group for accountability and discussion."
  ],
  "scripture": "James 1:5 - Seek wisdom from God in prayer, and He will guide you."
}
```

**Gemini**:
```json
{
  "title": "Establish a Consistent Prayer Rhythm",
  "description": "Consistent prayer cultivates intimacy with God and strengthens our reliance on Him. Prioritizing a set time and place, even for a short duration, can transform your spiritual life...",
  "steps": [
    "Choose a specific time and place for prayer each day.",
    "Start with 5-10 minutes and gradually increase the duration.",
    "Use a prayer journal to focus your thoughts and track requests."
  ],
  "scripture": "Matthew 6:6 - But when you pray, go into your room, close the door and pray to your Father, who is unseen..."
}
```

**Analysis**:
- OpenAI: More generic title, combines two areas (prayer + Scripture)
- Gemini: Focused on single most important area, more specific steps ("5-10 minutes"), better Scripture choice with fuller quotation
- **Winner**: Gemini - more actionable, more pastoral, better Scripture integration

#### Insights Quality

**OpenAI (Prayer Life)**:
```json
{
  "category": "Prayer Life",
  "level": "Maturing",
  "observation": "You have a consistent prayer routine but struggle with distractions. Incorporating listening time can enhance your prayer experience.",
  "next_step": "Try setting aside a few minutes specifically for listening after your prayers."
}
```

**Gemini (Prayer Life)**:
```json
{
  "category": "Prayer Life",
  "level": "Developing",
  "observation": "Jordan is making an effort to pray regularly, but struggles with consistency and focus. The use of a prayer journal is a positive step, but further development is needed to establish a more consistent and meaningful prayer life.",
  "next_step": "Experiment with different prayer methods, such as praying scripture or using guided meditations, to find what helps you focus and connect with God more deeply."
}
```

**Analysis**:
- OpenAI: Shorter, more generic advice
- Gemini: Uses apprentice's name, references specific details from answers (prayer journal), provides concrete alternatives (praying scripture, guided meditations)
- Gemini's "Developing" level is more accurate than OpenAI's "Maturing" given the inconsistency mentioned
- **Winner**: Gemini - more personalized, more detailed, more accurate level assessment

#### Recommended Resources

| OpenAI | Gemini |
|--------|--------|
| "How to Study the Bible" (generic title) | "Prayer: Experiencing Awe and Intimacy with God by Timothy Keller" |
| "This book provides practical methods..." | "This book provides a comprehensive guide to prayer, exploring different types of prayer and offering practical advice for developing a more meaningful prayer life." |

**Analysis**: Gemini provides a specific author (Timothy Keller), more detailed explanation of why the resource fits this apprentice.
- **Winner**: Gemini

### Summary: OpenAI vs Gemini

| Dimension | OpenAI | Gemini | Notes |
|-----------|--------|--------|-------|
| Speed | ⭐⭐ | ⭐⭐⭐⭐⭐ | 55% faster |
| Cost | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 5x cheaper |
| JSON Reliability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Both 100% |
| Personalization | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gemini uses names, quotes answers |
| Actionability | ⭐⭐⭐ | ⭐⭐⭐⭐ | Gemini more specific steps |
| Scripture Usage | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gemini provides fuller quotes |
| Accuracy | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gemini more conservative/accurate |
| Pastoral Tone | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gemini more direct yet caring |

**Recommendation**: **Switch to Gemini** with LLM abstraction layer for flexibility.

---

## 2. Current Report Structure

### What We Have Today

#### Simplified Report (Currently Used)
The `MentorReportSimplifiedScreen` displays:

**Tier 1 (Always Visible)**:
- Health Score + Band (e.g., 72 "Maturing")
- Top 3 Strengths
- Top 3 Gaps
- 1 Priority Action
- Urgent Flags (red only)

**Tier 2 (Expandable Sections)**:
- Biblical Knowledge (percent + weak topics)
- Spiritual Insights (3-5 categories with level/observation)
- Four-Week Plan (rhythm + checkpoints)

**Tier 3 (Full Report Button)**:
- Currently links to same data in different view
- No additional content

#### Data Available But Not Shown

From the AI output, we have:
- Detailed per-question feedback
- Study recommendations with specific book suggestions
- Scripture references with explanations
- Conversation starters
- Recommended resources
- Yellow/green flags (only red shown prominently)
- Trend analysis (if historical data exists)

### Current API Response Shape (`/mentor/reports/{id}/simplified`)

```json
{
  "health_score": 72,
  "health_band": "Maturing",
  "strengths": ["...", "...", "..."],
  "gaps": ["...", "...", "..."],
  "priority_action": {
    "title": "...",
    "description": "...",
    "scripture": "..."
  },
  "flags": {"red": [], "yellow": [], "green": []},
  "biblical_knowledge": {"percent": 72.0, "topics": [], "weak_topics": []},
  "insights": [{"category": "...", "level": "...", "observation": "...", "next_step": "..."}],
  "conversation_starters": ["...", "..."],
  "trend_note": null,
  "mc_percent": 72.0,
  "full_report_url": "/mentor/assessment/{id}"
}
```

---

## 3. Enhanced Full Report Proposal

### Vision: A Report Worth Paying For

The full report should feel like receiving a personalized consultation from a seasoned mentor, not just more data. It should:

1. **Save the mentor time** - Pre-written talking points, not raw data
2. **Deepen understanding** - Explain the "why" behind each insight
3. **Provide tools** - Ready-to-use conversation guides, prayer points, study plans
4. **Track progress** - Historical comparison, growth trajectory
5. **Enable action** - Printable/shareable formats, calendar integration

### Full Report Structure (Premium)

#### Section 1: Executive Summary (Same as Simplified)
- Health Score visualization
- Strengths & Gaps at a glance
- Priority Action card

#### Section 2: Deep Dive - Biblical Knowledge (NEW)
```json
{
  "biblical_knowledge_deep": {
    "overall_percent": 72.0,
    "grade": "B-",
    "topic_breakdown": [
      {
        "topic": "Gospels",
        "correct": 8,
        "total": 10,
        "percent": 80,
        "grade": "B+",
        "missed_concepts": ["Parables of Jesus - missed 2/3 questions"],
        "study_priority": "low"
      },
      {
        "topic": "Pentateuch",
        "correct": 4,
        "total": 8,
        "percent": 50,
        "grade": "F",
        "missed_concepts": ["Creation account details", "Covenant with Abraham"],
        "study_priority": "high"
      }
    ],
    "personalized_study_plan": {
      "focus_area": "Pentateuch",
      "why": "Your assessment reveals gaps in foundational Old Testament knowledge that affects understanding of covenant, salvation, and God's character.",
      "weekly_plan": [
        {"week": 1, "topic": "Genesis 1-11: Creation & Fall", "reading": "Genesis 1-3", "reflection_question": "How does understanding God as Creator change how you view your own life?"},
        {"week": 2, "topic": "Genesis 12-25: Abraham's Covenant", "reading": "Genesis 12, 15, 17", "reflection_question": "What promises did God make to Abraham that still apply to you?"},
        {"week": 3, "topic": "Exodus 1-20: Deliverance & Law", "reading": "Exodus 1-3, 12, 20", "reflection_question": "How is the Passover a picture of Christ's sacrifice for you?"},
        {"week": 4, "topic": "Review & Application", "reading": "Review notes", "reflection_question": "What's one thing you learned that changes how you'll live this week?"}
      ],
      "recommended_resource": {
        "title": "The Bible Project: Torah Series",
        "type": "video",
        "url": "https://bibleproject.com/explore/torah/",
        "why": "Visual learner-friendly, explains how Genesis-Deuteronomy connects to Jesus"
      }
    }
  }
}
```

#### Section 3: Spiritual Life Analysis (Enhanced)
```json
{
  "spiritual_insights_deep": [
    {
      "category": "Prayer Life",
      "level": "Developing",
      "summary": "Growing but inconsistent",
      
      "what_we_observed": "Jordan prays 10-15 minutes most mornings, uses a prayer journal twice weekly, and desires to grow in listening prayer. However, consistency breaks down during busy periods, and prayers focus primarily on personal needs.",
      
      "what_this_means": "This pattern is very common for Christians in the 'Developing' stage. You have the desire and some discipline, but haven't yet built the muscle memory that makes prayer automatic. The good news: you're closer than you think.",
      
      "growth_path": {
        "current_stage": "Developing",
        "next_stage": "Stable",
        "what_stable_looks_like": "Stable prayer life means 5+ days/week consistency, expanding beyond personal requests to include intercession and worship, and beginning to recognize God's voice.",
        "estimated_time": "2-3 months with intentional practice"
      },
      
      "mentor_talking_points": [
        "Ask: 'What usually happens on the days you don't pray? What's the trigger that breaks your routine?'",
        "Share your own struggle with consistency if relevant",
        "Explore: 'You mentioned wanting to listen more. What do you think God's voice sounds like?'",
        "Challenge: 'What if we started with just 5 minutes but made it unbreakable? What would that take?'"
      ],
      
      "prayer_points_for_mentor": [
        "Pray for Jordan to experience God's presence during prayer, not just obligation",
        "Pray for protection from the enemy's attacks on prayer consistency",
        "Pray for a breakthrough in hearing God's voice"
      ],
      
      "scripture_meditation": {
        "verse": "Matthew 6:6",
        "text": "But when you pray, go into your room, close the door and pray to your Father, who is unseen. Then your Father, who sees what is done in secret, will reward you.",
        "application": "Jesus assumes private prayer is non-negotiable for His followers. The 'reward' isn't just answered prayers—it's intimacy with the Father."
      },
      
      "practical_exercises": [
        {
          "name": "ACTS Prayer Model",
          "description": "Structure your 10 minutes: 2 min Adoration (praise), 2 min Confession, 3 min Thanksgiving, 3 min Supplication",
          "why_it_helps": "Eliminates 'I don't know what to say' and ensures balanced prayer life"
        },
        {
          "name": "Prayer Walking",
          "description": "Combine prayer with your existing morning routine - pray while walking, commuting, or exercising",
          "why_it_helps": "Removes the barrier of 'finding time' by stacking habits"
        }
      ]
    }
  ]
}
```

#### Section 4: Conversation Guide (NEW for Premium)
```json
{
  "conversation_guide": {
    "session_focus": "Prayer Life & Community",
    "estimated_time": "45-60 minutes",
    
    "opening": {
      "prayer_prompt": "Lord, open Jordan's heart to receive truth and give me wisdom to guide well...",
      "icebreaker": "Before we dive in, tell me about one good thing that happened this week."
    },
    
    "discussion_flow": [
      {
        "topic": "Celebrate Wins",
        "time": "5 min",
        "prompt": "I noticed you've been consistent with morning prayer. That's real growth! What's made that possible?",
        "listen_for": "Signs of intrinsic motivation vs. guilt-driven discipline"
      },
      {
        "topic": "Explore Challenges",
        "time": "10 min",
        "prompt": "You mentioned sometimes forgetting when busy. Walk me through what a 'busy morning' looks like.",
        "listen_for": "Specific triggers, patterns, competing priorities"
      },
      {
        "topic": "Address the Gap",
        "time": "15 min",
        "prompt": "Your assessment shows community as an area for growth. What's your honest feeling about small groups?",
        "listen_for": "Fear of vulnerability, past wounds, practical barriers",
        "potential_pivot": "If they resist small groups, explore 1-on-1 friendship with another believer first"
      },
      {
        "topic": "Set One Goal",
        "time": "10 min",
        "prompt": "If you could change one thing about your spiritual life in the next month, what would it be?",
        "coaching_tip": "Help them narrow to something specific and measurable"
      }
    ],
    
    "closing": {
      "prayer_points": ["Consistency in prayer", "Courage to pursue community", "Protection from discouragement"],
      "next_meeting_focus": "Follow up on prayer consistency goal",
      "homework_for_apprentice": "Try the ACTS prayer model 3x this week and text me how it goes"
    }
  }
}
```

#### Section 5: Progress Tracking (Premium)
```json
{
  "progress_tracking": {
    "current_assessment": {
      "date": "2026-01-31",
      "health_score": 69,
      "health_band": "Stable"
    },
    "previous_assessments": [
      {
        "date": "2025-10-15",
        "health_score": 58,
        "health_band": "Developing"
      },
      {
        "date": "2025-07-01",
        "health_score": 45,
        "health_band": "Developing"
      }
    ],
    "growth_trajectory": {
      "trend": "positive",
      "points_gained": 24,
      "average_growth_rate": "3.4 points/month",
      "projected_next_band": "Maturing",
      "projected_date": "April 2026"
    },
    "category_changes": [
      {"category": "Prayer Life", "previous": "Beginning", "current": "Developing", "change": "+1 level"},
      {"category": "Scripture Engagement", "previous": "Developing", "current": "Stable", "change": "+1 level"},
      {"category": "Community", "previous": "Developing", "current": "Developing", "change": "No change"}
    ],
    "celebration_note": "Jordan has grown 24 points since starting the mentorship! That's exceptional progress. Take time to celebrate specific wins.",
    "concern_note": "Community hasn't improved despite prayer and Scripture gains. This may need focused attention."
  }
}
```

#### Section 6: Exportable Formats (Premium)
- **PDF Report**: Professionally formatted, printable
- **Email Summary**: Condensed version for sending to apprentice
- **Calendar Integration**: Add follow-up reminders
- **Share with Accountability Partner**: Optional secondary mentor view

---

## 4. Premium vs Free Tier Differentiation

### Free Tier (Simplified Report)
| Feature | Included |
|---------|----------|
| Health Score + Band | ✅ |
| Top 3 Strengths | ✅ |
| Top 3 Gaps | ✅ |
| Priority Action (title only) | ✅ |
| Red Flags | ✅ |
| Basic Biblical Knowledge % | ✅ |
| Basic Insights (level only) | ✅ |
| 2 Conversation Starters | ✅ |

### Premium Tier (Full Report)
| Feature | Included |
|---------|----------|
| Everything in Free | ✅ |
| Priority Action with full description + steps | ✅ |
| All Flags (red, yellow, green) with explanations | ✅ |
| Deep Biblical Knowledge Analysis | ✅ |
| Personalized 4-Week Study Plan | ✅ |
| Deep Spiritual Insights with "what this means" | ✅ |
| Mentor Talking Points per category | ✅ |
| Prayer Points for Mentor | ✅ |
| Scripture Meditations | ✅ |
| Practical Exercises | ✅ |
| Full Conversation Guide | ✅ |
| Progress Tracking + Trends | ✅ |
| PDF Export | ✅ |
| Email Summary | ✅ |
| Recommended Resources with "why it fits you" | ✅ |

### Visual Comparison

**Free User View**:
```
┌──────────────────────────────────────────┐
│ 🎯 Health Score: 69 (Stable)             │
├──────────────────────────────────────────┤
│ ✅ Strengths: 3 items                    │
│ ⚠️ Gaps: 3 items                         │
├──────────────────────────────────────────┤
│ 📋 Priority Action: "Establish Prayer"  │
│    [🔒 See full steps - Premium]         │
├──────────────────────────────────────────┤
│ 📖 Biblical Knowledge: 72%               │
│    [🔒 See study plan - Premium]         │
├──────────────────────────────────────────┤
│ 💡 Insights: 3 categories (levels only) │
│    [🔒 See talking points - Premium]     │
├──────────────────────────────────────────┤
│ 💬 Conversation Starters: 2              │
│    [🔒 See full guide - Premium]         │
└──────────────────────────────────────────┘
        [⭐ Upgrade for Full Report]
```

**Premium User View**:
```
┌──────────────────────────────────────────┐
│ 🎯 Health Score: 69 (Stable)             │
│ 📈 +11 pts since last assessment!        │
├──────────────────────────────────────────┤
│ [Full Report with all sections expanded] │
│ [PDF Download] [Email Apprentice]        │
│ [Add to Calendar]                        │
└──────────────────────────────────────────┘
```

---

## 5. Implementation Plan

### Phase 1: LLM Abstraction (Week 1)
- [ ] Create `LLMService` interface
- [ ] Implement `OpenAIProvider`
- [ ] Implement `VertexGeminiProvider`
- [ ] Add config-based provider selection
- [ ] Add structured output validation
- [ ] Add retry logic for JSON parsing

### Phase 2: Enhanced Prompt Engineering (Week 1-2)
- [ ] Create "full report" prompt variant
- [ ] Add conversation guide generation
- [ ] Add study plan generation
- [ ] Add progress analysis generation
- [ ] Test with both OpenAI and Gemini

### Phase 3: Backend API Changes (Week 2)
- [ ] Create `/mentor/reports/{id}/full` endpoint
- [ ] Create `/apprentice/reports/{id}/full` endpoint
- [ ] Add subscription tier check to endpoints
- [ ] Store full vs simplified report preference
- [ ] Add PDF generation service

### Phase 4: Frontend Implementation (Week 3-4)
- [ ] Create `MentorReportFullScreen`
- [ ] Create premium gate UI components
- [ ] Add PDF export functionality
- [ ] Add email sharing functionality
- [ ] Create progress visualization charts

### Phase 5: Testing & Polish (Week 4-5)
- [ ] Test with real assessments
- [ ] Compare full reports across LLM providers
- [ ] Gather mentor feedback
- [ ] Performance optimization
- [ ] Documentation

---

## Appendix: API Changes Required

### New Endpoint: `/mentor/reports/{id}/full`

```python
@router.get("/reports/{assessment_id}/full", response_model=FullMentorReport)
def get_full_mentor_report(
    assessment_id: str,
    current_user: User = Depends(require_premium_mentor),  # NEW: subscription check
    db: Session = Depends(get_db)
):
    """Returns the complete enhanced report for premium mentors."""
    # ... implementation
```

### New Models

```python
class FullMentorReport(BaseModel):
    # Everything from SimplifiedReport +
    biblical_knowledge_deep: BiblicalKnowledgeDeep
    spiritual_insights_deep: List[SpiritualInsightDeep]
    conversation_guide: ConversationGuide
    progress_tracking: Optional[ProgressTracking]
    export_options: ExportOptions
```

### Database Changes

```sql
-- Track report tier preference
ALTER TABLE assessments ADD COLUMN report_tier VARCHAR(20) DEFAULT 'simplified';
-- Values: 'simplified', 'full'

-- Store full report cache (expensive to regenerate)
ALTER TABLE assessments ADD COLUMN full_report_blob JSONB;
ALTER TABLE assessments ADD COLUMN full_report_generated_at TIMESTAMP;
```

---

*Document created: January 31, 2026*
