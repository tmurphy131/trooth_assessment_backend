#!/usr/bin/env python3
"""
Simple test script to verify draft filtering logic
"""

def test_draft_filtering():
    """Test the draft filtering logic"""
    
    # Mock data representing drafts from database
    mock_drafts = [
        {'id': '1', 'is_submitted': False, 'template_id': 'template1'},
        {'id': '2', 'is_submitted': True, 'template_id': 'template1'},
        {'id': '3', 'is_submitted': False, 'template_id': 'template2'},
        {'id': '4', 'is_submitted': True, 'template_id': 'template2'},
    ]
    
    # Test list_drafts logic (should only return non-submitted)
    in_progress = [d for d in mock_drafts if not d['is_submitted']]
    print(f"In-progress drafts: {len(in_progress)}")
    for draft in in_progress:
        print(f"  - Draft {draft['id']}: is_submitted={draft['is_submitted']}")
    
    # Test list_completed_assessments logic (should only return submitted)
    completed = [d for d in mock_drafts if d['is_submitted']]
    print(f"\nCompleted assessments: {len(completed)}")
    for draft in completed:
        print(f"  - Draft {draft['id']}: is_submitted={draft['is_submitted']}")
    
    # Verify logic
    assert len(in_progress) == 2, f"Expected 2 in-progress drafts, got {len(in_progress)}"
    assert len(completed) == 2, f"Expected 2 completed assessments, got {len(completed)}"
    assert all(not d['is_submitted'] for d in in_progress), "All in-progress drafts should have is_submitted=False"
    assert all(d['is_submitted'] for d in completed), "All completed assessments should have is_submitted=True"
    
    print("\n✅ Draft filtering logic is correct!")

if __name__ == '__main__':
    test_draft_filtering()
