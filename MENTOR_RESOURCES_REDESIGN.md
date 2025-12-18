# Mentor Resources Redesign

## Overview

Redesign the Resources section in the Mentor Dashboard to include three distinct areas:
1. **Weekly Tip** - Rotating motivational tip (one per week)
2. **Mentor Guides** - Categorized reference articles for mentors
3. **My Shared Resources** - Custom materials mentors share with apprentices (existing functionality)

---

## Structure

```
📚 Resources
│
├── 💡 Weekly Tip
│   └── One rotating tip per week (bite-sized, actionable)
│   └── Quick read, motivational
│   └── Browse past tips archive
│
├── 📖 Mentor Guides
│   ├── Getting Started
│   ├── Communication Tips
│   ├── Assessment Guidance
│   ├── Spiritual Growth
│   ├── Milestone Celebrations
│   └── More...
│
└── 📎 My Shared Resources (Existing)
    └── Custom links/materials mentors share with apprentices
    └── Create, edit, delete
    └── Filter by apprentice
```

---

## Section Comparison

| Section | Content Type | Who Creates | Purpose |
|---------|-------------|-------------|---------|
| **Weekly Tip** | Single tip, rotates weekly | Admin/System | Quick motivation, keeps mentors engaged |
| **Mentor Guides** | Categorized articles/guides | Admin/System | Deep-dive reference material |
| **My Shared Resources** | Links, PDFs, notes | Mentor | Share materials with apprentices |

---

## UI Design

### Resources Screen Layout

```
┌─────────────────────────────────┐
│ 💡 This Week's Tip              │
│ Week 50 of 52                   │
│ "Active Listening: Before..."   │
│ [Read More] [Browse All Tips]   │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 📖 Mentor Guides                │
│ ┌───────────┐ ┌───────────┐    │
│ │🚀 Getting │ │💬 Commun- │    │
│ │  Started  │ │  ication  │    │
│ └───────────┘ └───────────┘    │
│ ┌───────────┐ ┌───────────┐    │
│ │📊 Assess- │ │🙏 Spiritual│   │
│ │   ment    │ │   Growth  │    │
│ └───────────┘ └───────────┘    │
│ ┌───────────┐ ┌───────────┐    │
│ │🎉 Mile-   │ │📚 More    │    │
│ │  stones   │ │           │    │
│ └───────────┘ └───────────┘    │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 📎 My Shared Resources (3)      │
│ • Resource 1 - Shared with John │
│ • Resource 2 - All Apprentices  │
│ • Resource 3 - Shared with Mary │
│ [+ Add Resource]                │
└─────────────────────────────────┘
```

---

## Data Models

### Weekly Tip

```python
class MentorWeeklyTip(Base):
    __tablename__ = "mentor_weekly_tips"
    
    id = Column(String, primary_key=True)
    week_number = Column(Integer, nullable=False)  # 1-52
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # 1-2 paragraphs
    scripture = Column(String(200), nullable=True)
    action_step = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Mentor Guide Category

```python
class MentorGuideCategory(Base):
    __tablename__ = "mentor_guide_categories"
    
    id = Column(String, primary_key=True)  # e.g., "getting_started"
    name = Column(String(100), nullable=False)  # e.g., "Getting Started"
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # emoji or icon name
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
```

### Mentor Guide

```python
class MentorGuide(Base):
    __tablename__ = "mentor_guides"
    
    id = Column(String, primary_key=True)
    category_id = Column(String, ForeignKey("mentor_guide_categories.id"))
    title = Column(String(200), nullable=False)
    summary = Column(String(500), nullable=True)  # Preview text
    content = Column(Text, nullable=False)  # Markdown content
    scripture = Column(String(200), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    category = relationship("MentorGuideCategory")
```

### My Shared Resources (Existing - No Changes)

```python
# Already exists: MentorResource
# - mentor_id, apprentice_id, title, description, link_url, is_shared
```

---

## API Endpoints

### Weekly Tips

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mentor/tips/weekly` | Get this week's tip |
| GET | `/mentor/tips` | List all tips (for archive browsing) |
| GET | `/mentor/tips/{tip_id}` | Get specific tip details |

### Mentor Guides

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mentor/guides/categories` | List all guide categories |
| GET | `/mentor/guides?category={id}` | List guides, optionally by category |
| GET | `/mentor/guides/{guide_id}` | Get full guide content |

### My Shared Resources (Existing - No Changes)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mentor/resources` | List mentor's shared resources |
| POST | `/mentor/resources` | Create new resource |
| PATCH | `/mentor/resources/{id}` | Update resource |
| DELETE | `/mentor/resources/{id}` | Delete resource |

---

## Guide Categories & Initial Content

### Categories

1. **🚀 Getting Started**
   - Welcome to Mentoring
   - Setting Expectations with Your Apprentice
   - Your First Meeting: What to Discuss
   - Creating a Mentorship Agreement

2. **💬 Communication Tips**
   - Active Listening Techniques
   - Asking Open-Ended Questions
   - Navigating Difficult Conversations
   - Providing Constructive Feedback
   - When to Listen vs. When to Advise

3. **📊 Assessment Guidance**
   - Understanding Assessment Scores
   - How to Discuss Results with Your Apprentice
   - Identifying Growth Areas
   - Tracking Progress Over Time
   - When Scores Don't Match Expectations

4. **🙏 Spiritual Growth**
   - Praying for Your Apprentice
   - Scripture Study Together
   - Modeling Spiritual Disciplines
   - Encouraging Daily Devotion
   - Faith During Difficult Seasons

5. **🎉 Milestone Celebrations**
   - Recognizing Progress
   - Celebrating Spiritual Breakthroughs
   - Anniversary & Checkpoint Ideas
   - Transitioning When Mentorship Ends
   - Staying Connected After Formal Mentorship

6. **📚 More Resources**
   - Recommended Books
   - External Links & Tools
   - Community Resources
   - FAQ for Mentors

---

## Weekly Tips (Sample - 52 Tips)

| Week | Title | Preview |
|------|-------|---------|
| 1 | Start with Prayer | Begin each mentoring session by praying together... |
| 2 | Listen More Than You Speak | Your apprentice needs to be heard before... |
| 3 | Ask "How Can I Help?" | Sometimes the best guidance comes from asking... |
| 4 | Share Your Struggles | Vulnerability builds trust. Share a time when... |
| 5 | Celebrate Small Wins | Progress isn't always dramatic. Notice the small... |
| ... | ... | ... |
| 52 | Reflect on the Year | Take time to look back at how far your apprentice... |

---

## Implementation Phases

### Phase 1: UI Restructure (Frontend Only)
**Goal**: Reorganize the Resources screen with all three sections

**Tasks**:
- [ ] Refactor `mentor_resources_screen.dart` layout
- [ ] Add Weekly Tip card component at top
- [ ] Add Mentor Guides grid section (category cards)
- [ ] Move existing Shared Resources to bottom section
- [ ] Create `weekly_tips_data.dart` with hardcoded 52 tips
- [ ] Create `mentor_guides_data.dart` with hardcoded categories and sample guides
- [ ] Implement week number calculation for tip rotation

**Files to Create/Modify**:
- `lib/screens/mentor_resources_screen.dart` (modify)
- `lib/data/weekly_tips_data.dart` (create)
- `lib/data/mentor_guides_data.dart` (create)
- `lib/screens/weekly_tip_detail_screen.dart` (create)
- `lib/screens/mentor_guides_list_screen.dart` (create)
- `lib/screens/mentor_guide_detail_screen.dart` (create)

---

### Phase 2: Mentor Guides Content
**Goal**: Populate all guide categories with actual content

**Tasks**:
- [ ] Write 3-5 guides for "Getting Started" category
- [ ] Write 3-5 guides for "Communication Tips" category
- [ ] Write 3-5 guides for "Assessment Guidance" category
- [ ] Write 3-5 guides for "Spiritual Growth" category
- [ ] Write 3-5 guides for "Milestone Celebrations" category
- [ ] Add placeholder for "More Resources" category
- [ ] Review and edit all content

**Content Format**:
```dart
MentorGuide(
  id: 'guide_001',
  categoryId: 'getting_started',
  title: 'Welcome to Mentoring',
  summary: 'An introduction to your role as a spiritual mentor...',
  content: '''
# Welcome to Mentoring

Your role as a mentor is one of the most impactful...

## What to Expect

...

## Scripture Foundation

> "And the things you have heard me say in the presence of many witnesses 
> entrust to reliable people who will also be qualified to teach others."
> — 2 Timothy 2:2

## Action Steps

1. Pray for your apprentice daily
2. Schedule your first meeting
3. Review the Getting Started guides
  ''',
  scripture: '2 Timothy 2:2',
)
```

---

### Phase 3: Weekly Tips Content
**Goal**: Create all 52 weekly tips

**Tasks**:
- [ ] Write tips for weeks 1-13 (Q1)
- [ ] Write tips for weeks 14-26 (Q2)
- [ ] Write tips for weeks 27-39 (Q3)
- [ ] Write tips for weeks 40-52 (Q4)
- [ ] Add scripture references to each tip
- [ ] Add action steps to each tip
- [ ] Review and edit all tips

**Tip Format**:
```dart
WeeklyTip(
  weekNumber: 1,
  title: 'Start with Prayer',
  content: '''
Begin each mentoring session by praying together. This sets the 
tone for your time and invites God into your conversation.

Prayer doesn't need to be long or formal. A simple "Lord, guide 
our conversation today" can be powerful.
  ''',
  scripture: 'Philippians 4:6',
  actionStep: 'At your next meeting, ask your apprentice if you can open in prayer together.',
)
```

---

### Phase 4: Backend Implementation
**Goal**: Move tips and guides to database for admin management

**Tasks**:
- [ ] Create database migrations for new models
- [ ] Create `MentorWeeklyTip` model
- [ ] Create `MentorGuideCategory` model
- [ ] Create `MentorGuide` model
- [ ] Create API endpoints for tips
- [ ] Create API endpoints for guides
- [ ] Seed database with existing hardcoded content
- [ ] Update Flutter to fetch from API instead of local data

**Files to Create**:
- `app/models/mentor_weekly_tip.py`
- `app/models/mentor_guide.py`
- `app/schemas/mentor_tip.py`
- `app/schemas/mentor_guide.py`
- `app/routes/mentor_tips.py`
- `app/routes/mentor_guides.py`
- `alembic/versions/xxx_add_mentor_tips_and_guides.py`
- `scripts/seed_mentor_content.py`

---

### Phase 5: Admin Management (Optional)
**Goal**: Allow admins to manage tips and guides via admin panel

**Tasks**:
- [ ] Add admin endpoints for CRUD operations
- [ ] Create admin UI for managing weekly tips
- [ ] Create admin UI for managing guide categories
- [ ] Create admin UI for managing guides
- [ ] Add rich text/markdown editor for guide content
- [ ] Add preview functionality

---

### Phase 6: Push Notifications (Future)
**Goal**: Send weekly tip notifications to mentors

**Tasks**:
- [ ] Set up Firebase Cloud Messaging (FCM)
- [ ] Create Cloud Scheduler job for weekly notifications
- [ ] Add notification preferences to user settings
- [ ] Implement notification handling in Flutter
- [ ] Test notification delivery

---

## Success Metrics

- [ ] Mentors can view weekly rotating tips
- [ ] Mentors can browse tips archive
- [ ] Mentors can navigate guide categories
- [ ] Mentors can read full guide content
- [ ] Existing shared resources functionality unchanged
- [ ] UI is intuitive and matches app theme

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1 | 4-6 hours | None |
| Phase 2 | 8-12 hours | Phase 1 |
| Phase 3 | 4-6 hours | Phase 1 |
| Phase 4 | 6-8 hours | Phases 1-3 |
| Phase 5 | 8-12 hours | Phase 4 |
| Phase 6 | 6-8 hours | Phase 4 |

**MVP (Phases 1-3)**: ~20-24 hours
**Full Implementation**: ~40-50 hours

---

## Notes

- Start with hardcoded data to validate UX before building backend
- Guide content can be written incrementally
- Push notifications are nice-to-have, not essential for MVP
- Consider allowing mentors to bookmark/save favorite guides in future
