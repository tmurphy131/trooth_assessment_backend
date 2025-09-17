import pytest
from app.services.spiritual_gifts_scoring import validate_answers, score_spiritual_gifts, GIFT_ITEM_MAP


def _build_full_answers(val_map=None):
    ans = {}
    for items in GIFT_ITEM_MAP.values():
        for q in items:
            ans[q] = 2  # default mid value
    if val_map:
        ans.update(val_map)
    return ans


def test_validate_answers_ok():
    answers = _build_full_answers()
    errors = validate_answers(answers)
    assert errors == []


def test_validate_answers_missing():
    answers = _build_full_answers()
    # remove one
    first_q = next(iter(answers.keys()))
    del answers[first_q]
    errors = validate_answers(answers)
    assert any('Missing items' in e for e in errors)


def test_validate_answers_extraneous():
    answers = _build_full_answers({"Q99": 1})
    errors = validate_answers(answers)
    assert any('Unexpected items' in e for e in errors)


def test_validate_answers_out_of_range():
    answers = _build_full_answers({next(iter(GIFT_ITEM_MAP.values()))[0]: 7})
    errors = validate_answers(answers)
    assert any('Out-of-range' in e for e in errors)


def test_score_spiritual_gifts_ordering_and_ties():
    # Create pattern to force tie at third place.
    # We'll boost three gifts to same high score and ensure alphabetical tiebreak.
    answers = _build_full_answers()
    # Base all gifts: each item =2 -> per gift score = 6
    # Boost specific gifts with higher values for ordering
    def boost(gift, amount):
        for q in GIFT_ITEM_MAP[gift]:
            answers[q] = amount
    boost('Wisdom', 4)          # score 12
    boost('Faith', 4)           # score 12
    boost('Teaching', 3)        # score 9
    boost('Leadership', 3)      # score 9  (tie with Teaching -> alphabetical decides)

    scored = score_spiritual_gifts(answers)
    all_scores = scored['all_scores']
    # Top should start with Faith and Wisdom (alphabetical between equal scores) then Leadership or Teaching depending alpha among 9's
    # Among 12's: Faith vs Wisdom -> Faith then Wisdom
    assert all_scores[0]['gift'] == 'Faith'
    assert all_scores[1]['gift'] == 'Wisdom'
    # Scores 3rd and 4th should be Leadership and Teaching (alphabetical) both 9
    third_score = all_scores[2]['score']
    assert third_score == 9
    assert {all_scores[2]['gift'], all_scores[3]['gift']} == {'Leadership', 'Teaching'}

    # Truncated top3 should include first three only
    assert [g['gift'] for g in scored['top_gifts_truncated']] == [all_scores[0]['gift'], all_scores[1]['gift'], all_scores[2]['gift']]

    # Expanded should include both 9's (tie at third place)
    expanded_gifts = {g['gift'] for g in scored['top_gifts_expanded']}
    assert {'Leadership', 'Teaching', 'Faith', 'Wisdom'}.issubset(expanded_gifts)


def test_score_spiritual_gifts_validation_error():
    with pytest.raises(ValueError):
        score_spiritual_gifts({'Q01': 1})  # incomplete
