# Mentor Notes Feature Implementation Guide

## Overview

The Mentor Notes feature allows mentors to add private notes and follow-up plans to their apprentices' completed assessments. This enables mentors to track observations, document growth areas, and plan future mentoring sessions.

---

## Backend Implementation (✅ Complete)

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/mentor-notes/` | Create a new note on an assessment |
| `GET` | `/mentor-notes/assessment/{assessment_id}` | List all notes for an assessment |
| `DELETE` | `/mentor-notes/{note_id}` | Delete a note (only by author) |

### Data Model

```python
class MentorNote:
    id: str                    # UUID primary key
    assessment_id: str         # FK to assessments.id
    mentor_id: str             # FK to users.id (the mentor who wrote it)
    content: str               # The note text (required)
    follow_up_plan: str | None # Optional follow-up plan
    is_private: bool           # Default: True (only mentor can see)
    created_at: datetime       # Auto-set on creation
```

### Request/Response Schemas

**Create Note Request (`MentorNoteCreate`):**
```json
{
  "assessment_id": "uuid-string",
  "content": "This apprentice shows strong leadership qualities...",
  "follow_up_plan": "Discuss service opportunities in next meeting",
  "is_private": true
}
```

**Note Response (`MentorNoteOut`):**
```json
{
  "id": "uuid-string",
  "assessment_id": "uuid-string",
  "mentor_id": "uuid-string",
  "content": "This apprentice shows strong leadership qualities...",
  "follow_up_plan": "Discuss service opportunities in next meeting",
  "is_private": true,
  "created_at": "2025-12-19T10:30:00Z"
}
```

### Authorization Rules

1. Only users with `mentor` role can access these endpoints
2. Mentor must have an active relationship with the apprentice (via `mentor_apprentice` table)
3. Notes can only be deleted by the mentor who created them

---

## Frontend Implementation (📋 TODO)

### Required API Service Methods

Add these methods to `lib/services/api_service.dart`:

```dart
/// Create a new mentor note on an assessment
Future<Map<String, dynamic>> createMentorNote({
  required String assessmentId,
  required String content,
  String? followUpPlan,
  bool isPrivate = true,
}) async {
  return await _request(
    'POST',
    '/mentor-notes/',
    body: {
      'assessment_id': assessmentId,
      'content': content,
      'follow_up_plan': followUpPlan,
      'is_private': isPrivate,
    },
  );
}

/// Get all notes for an assessment
Future<List<Map<String, dynamic>>> getMentorNotesForAssessment(String assessmentId) async {
  final response = await _request('GET', '/mentor-notes/assessment/$assessmentId');
  return List<Map<String, dynamic>>.from(response);
}

/// Delete a mentor note
Future<void> deleteMentorNote(String noteId) async {
  await _request('DELETE', '/mentor-notes/$noteId');
}
```

### Data Model

Create `lib/models/mentor_note.dart`:

```dart
class MentorNote {
  final String id;
  final String assessmentId;
  final String mentorId;
  final String content;
  final String? followUpPlan;
  final bool isPrivate;
  final DateTime createdAt;

  MentorNote({
    required this.id,
    required this.assessmentId,
    required this.mentorId,
    required this.content,
    this.followUpPlan,
    required this.isPrivate,
    required this.createdAt,
  });

  factory MentorNote.fromJson(Map<String, dynamic> json) {
    return MentorNote(
      id: json['id'],
      assessmentId: json['assessment_id'],
      mentorId: json['mentor_id'],
      content: json['content'],
      followUpPlan: json['follow_up_plan'],
      isPrivate: json['is_private'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
```

---

## UI Implementation

### Mentor Perspective

#### 1. Notes Section on Assessment Report

**Location:** Add to `MentorReportV2Screen` (or equivalent mentor report screen)

**Design:**
```
┌─────────────────────────────────────────────────┐
│  📝 Mentor Notes                          [+ Add] │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐ │
│  │ Dec 19, 2025                           [🗑️] │ │
│  │ Shows strong spiritual awareness and        │ │
│  │ genuine desire to serve others.             │ │
│  │                                             │ │
│  │ 📋 Follow-up: Discuss youth group          │ │
│  │    leadership role                          │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │ Dec 12, 2025                           [🗑️] │ │
│  │ Completed first assessment - establishing   │ │
│  │ baseline for spiritual gifts profile.       │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### 2. Add Note Dialog

**Trigger:** Tap "+ Add" button in notes section

**Design:**
```
┌─────────────────────────────────────────────────┐
│                  Add Note                    ✕  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Note *                                         │
│  ┌─────────────────────────────────────────────┐│
│  │                                             ││
│  │ Enter your observations...                  ││
│  │                                             ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  Follow-up Plan (optional)                      │
│  ┌─────────────────────────────────────────────┐│
│  │ Enter follow-up actions...                  ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  ☑️ Private (only visible to me)               │
│                                                 │
│         [Cancel]            [Save Note]         │
└─────────────────────────────────────────────────┘
```

#### 3. Delete Confirmation

**Trigger:** Tap trash icon on a note

```
┌─────────────────────────────────────────────────┐
│              Delete Note?                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  Are you sure you want to delete this note?     │
│  This action cannot be undone.                  │
│                                                 │
│         [Cancel]            [Delete]            │
└─────────────────────────────────────────────────┘
```

### Apprentice Perspective

#### Current Design: Private Notes Only

With `is_private: true` (default), apprentices **do not see** mentor notes. This allows mentors to keep candid observations.

#### Future Enhancement: Shared Notes

If `is_private: false`, the note could be visible to the apprentice on their assessment report:

```
┌─────────────────────────────────────────────────┐
│  💬 Mentor Feedback                             │
├─────────────────────────────────────────────────┤
│  From: Pastor John                              │
│  Dec 19, 2025                                   │
│                                                 │
│  "Great progress! Your gifts in teaching and   │
│   encouragement are really developing."         │
│                                                 │
│  📋 Next Steps: Let's discuss leading a small  │
│     group study next semester.                  │
└─────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 1: Core Functionality
- [ ] Add API methods to `api_service.dart`
- [ ] Create `MentorNote` model class
- [ ] Add notes section to mentor report screen
- [ ] Implement "Add Note" dialog
- [ ] Implement note deletion with confirmation
- [ ] Add loading states and error handling

### Phase 2: Polish
- [ ] Add empty state ("No notes yet. Add your first note!")
- [ ] Add character counter for note content
- [ ] Implement pull-to-refresh for notes list
- [ ] Add optimistic UI updates (show note immediately, sync in background)

### Phase 3: Enhanced Features (Future)
- [ ] Allow sharing notes with apprentice (`is_private: false`)
- [ ] Add note editing capability (requires new backend endpoint)
- [ ] Add note categories/tags
- [ ] Add ability to attach notes to specific assessment questions
- [ ] Export notes to PDF with assessment report

---

## Testing Scenarios

### Happy Path
1. Mentor views apprentice assessment
2. Mentor taps "Add Note"
3. Mentor enters note content and optional follow-up plan
4. Note appears in list immediately
5. Mentor can delete their own notes

### Edge Cases
1. **No relationship:** Mentor tries to add note to unlinked apprentice's assessment → 403 error
2. **Empty content:** Validate that content is required before API call
3. **Network error:** Show retry option, don't lose draft content
4. **Delete someone else's note:** Backend returns 404 (note not found for this mentor)

### Authorization Tests
1. Apprentice cannot access `/mentor-notes/` endpoints
2. Mentor A cannot see Mentor B's notes on shared apprentice
3. Mentor cannot add note to assessment of unlinked apprentice

---

## Related Files

### Backend
- `app/routes/mentor_notes.py` - API endpoints
- `app/models/mentor_note.py` - Database model
- `app/schemas/mentor_note.py` - Pydantic schemas
- `tests/test_mentor_notes.py` - API tests

### Frontend (to create)
- `lib/models/mentor_note.dart` - Data model
- `lib/widgets/mentor_notes_section.dart` - Notes list widget
- `lib/widgets/add_note_dialog.dart` - Add note modal
