import uuid
from datetime import datetime, timedelta

def test_create_and_submit_agreement(client, db_session, mentor_user, auth_headers_factory):
    # Seed template (if not seeded)
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if r.status_code == 200 and len(r.json()) == 0:
        tpl_resp = client.post('/agreements/templates', json={
            'markdown_source': 'Agreement v1: Location {{meeting_location}} Duration {{meeting_duration_minutes}}',
            'notes': 'init'
    }, headers={"Authorization": "Bearer mock-admin-token"})
        assert tpl_resp.status_code == 200
    else:
        assert r.status_code == 200

    # Create agreement
    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': False,
        'parent_required': False,
        'fields': {
            'meeting_location': 'Cafe',
            'meeting_duration_minutes': 45
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    assert create_resp.status_code == 200, create_resp.text
    agreement_id = create_resp.json()['id']

    # Submit
    submit_resp = client.post(f'/agreements/{agreement_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})
    assert submit_resp.status_code == 200
    assert submit_resp.json()['status'] == 'awaiting_apprentice'


def test_apprentice_sign_flow(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Ensure template exists
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        tpl_resp = client.post('/agreements/templates', json={
            'markdown_source': 'Agreement Template {{meeting_location}}',
            'notes': 'init'
    }, headers={"Authorization": "Bearer mock-admin-token"})
        assert tpl_resp.status_code == 200

    # Create agreement
    # Use static apprentice email to match mock-apprentice-token user
    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': False,
        'parent_required': False,
        'fields': {
            'meeting_location': 'Library',
            'meeting_duration_minutes': 60
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    agreement_id = create_resp.json()['id']

    submit_resp = client.post(f'/agreements/{agreement_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})
    assert submit_resp.status_code == 200

    # Apprentice signs
    sign_resp = client.post(f'/agreements/{agreement_id}/sign/apprentice', json={'typed_name': 'Apprentice User'}, headers={"Authorization": "Bearer mock-apprentice-token"})
    assert sign_resp.status_code == 200
    data = sign_resp.json()
    assert data['status'] == 'fully_signed'
    assert data['apprentice_signature_name'] == 'Apprentice User'
    assert data['activated_at'] is not None


def test_parent_required_flow(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Template ensured
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        client.post('/agreements/templates', json={'markdown_source': 'Agreement X {{meeting_location}}', 'notes': 'init'}, headers={"Authorization": "Bearer mock-admin-token"})

    # Create with parent requirement
    resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': True,
        'parent_required': True,
        'parent_email': 'parent@example.com',
        'fields': {
            'meeting_location': 'Hall',
            'meeting_duration_minutes': 30
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    agreement_id = resp.json()['id']

    client.post(f'/agreements/{agreement_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})

    # Apprentice signs (moves to awaiting_parent)
    sign1 = client.post(f'/agreements/{agreement_id}/sign/apprentice', json={'typed_name': 'Apprentice Minor'}, headers={"Authorization": "Bearer mock-apprentice-token"})
    assert sign1.status_code == 200
    assert sign1.json()['status'] == 'awaiting_parent'

    # Parent token workflow (simplified: use public endpoints via token extraction is skipped for now)
    # Force-create a parent token and sign via public if needed (future enhancement).


def test_revoke_flow(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Ensure template
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        client.post('/agreements/templates', json={'markdown_source': 'Agreement Rev {{meeting_location}}', 'notes': 'init'}, headers={"Authorization": "Bearer mock-admin-token"})

    # Create + submit + sign
    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': False,
        'parent_required': False,
        'fields': {
            'meeting_location': 'Cafe',
            'meeting_duration_minutes': 25
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    agreement_id = create_resp.json()['id']
    client.post(f'/agreements/{agreement_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})
    client.post(f'/agreements/{agreement_id}/sign/apprentice', json={'typed_name': 'Apprentice User'}, headers={"Authorization": "Bearer mock-apprentice-token"})

    # Revoke
    revoke_resp = client.post(f'/agreements/{agreement_id}/revoke', headers={"Authorization": "Bearer mock-mentor-token"})
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()['status'] == 'revoked'


def test_integrity_endpoint(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Ensure template
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        client.post('/agreements/templates', json={'markdown_source': 'IntegrityTpl {{meeting_location}}', 'notes': 'init'}, headers={"Authorization": "Bearer mock-admin-token"})

    # Create + submit
    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': False,
        'parent_required': False,
        'fields': {
            'meeting_location': 'Integrity Hall',
            'meeting_duration_minutes': 20
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    ag_id = create_resp.json()['id']
    client.post(f'/agreements/{ag_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})

    integ = client.get(f'/agreements/{ag_id}/integrity', headers={"Authorization": "Bearer mock-mentor-token"})
    assert integ.status_code == 200
    data = integ.json()
    assert data['match'] is True


def test_public_apprentice_sign_flow(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Ensure template exists
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        client.post('/agreements/templates', json={'markdown_source': 'PublicFlow {{meeting_location}}', 'notes': 'init'}, headers={"Authorization": "Bearer mock-admin-token"})

    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'anon_apprentice@example.com',
        'apprentice_is_minor': False,
        'parent_required': False,
        'fields': {
            'meeting_location': 'Lobby',
            'meeting_duration_minutes': 30
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    ag_id = create_resp.json()['id']
    submit_resp = client.post(f'/agreements/{ag_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})
    assert submit_resp.status_code == 200

    # fetch tokens directly via DB fixture (assuming helper) else call public token endpoint by scanning? Simplify: call integrity then query tokens through an endpoint - not available yet.
    # Instead, hit public token endpoint by iterating possible tokens via internal db_session (fixture exposes session)
    from app.models.agreement import AgreementToken
    token_obj = db_session.query(AgreementToken).filter_by(agreement_id=ag_id, token_type='apprentice').first()
    assert token_obj is not None
    token = token_obj.token

    view_resp = client.get(f'/agreements/public/{token}')
    assert view_resp.status_code == 200
    sign_resp = client.post(f'/agreements/public/{token}/sign', json={'typed_name': 'Anon User'})
    assert sign_resp.status_code == 200
    assert sign_resp.json()['status'] == 'fully_signed'


def test_parent_token_resend_and_sign(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Template
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        client.post('/agreements/templates', json={'markdown_source': 'ParentFlow {{meeting_location}}', 'notes': 'init'}, headers={"Authorization": "Bearer mock-admin-token"})

    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': True,
        'parent_required': True,
        'parent_email': 'parent2@example.com',
        'fields': {
            'meeting_location': 'Gym',
            'meeting_duration_minutes': 40
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    ag_id = create_resp.json()['id']
    client.post(f'/agreements/{ag_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})
    client.post(f'/agreements/{ag_id}/sign/apprentice', json={'typed_name': 'Minor User'}, headers={"Authorization": "Bearer mock-apprentice-token"})

    # Resend parent token (should exist already)
    resend = client.post(f'/agreements/{ag_id}/resend/parent-token', json={}, headers={"Authorization": "Bearer mock-mentor-token"})
    assert resend.status_code == 200
    assert resend.json()['status'] == 'awaiting_parent'

    from app.models.agreement import AgreementToken
    parent_token = db_session.query(AgreementToken).filter_by(agreement_id=ag_id, token_type='parent', used_at=None).first()
    assert parent_token is not None

    sign_parent = client.post(f'/agreements/public/{parent_token.token}/sign', json={'typed_name': 'Parent User'})
    assert sign_parent.status_code == 200
    assert sign_parent.json()['status'] == 'fully_signed'


def test_duplicate_sign_attempt(client, db_session, mentor_user, apprentice_user, auth_headers_factory):
    # Template ensure
    r = client.get('/agreements/templates', headers={"Authorization": "Bearer mock-mentor-token"})
    if len(r.json()) == 0:
        client.post('/agreements/templates', json={'markdown_source': 'DupSign {{meeting_location}}', 'notes': 'init'}, headers={"Authorization": "Bearer mock-admin-token"})

    create_resp = client.post('/agreements', json={
        'template_version': 1,
        'apprentice_email': 'apprentice@example.com',
        'apprentice_is_minor': False,
        'parent_required': False,
        'fields': {
            'meeting_location': 'Lab',
            'meeting_duration_minutes': 55
        }
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    ag_id = create_resp.json()['id']
    client.post(f'/agreements/{ag_id}/submit', headers={"Authorization": "Bearer mock-mentor-token"})
    first = client.post(f'/agreements/{ag_id}/sign/apprentice', json={'typed_name': 'Apprentice User'}, headers={"Authorization": "Bearer mock-apprentice-token"})
    assert first.status_code == 200
    second = client.post(f'/agreements/{ag_id}/sign/apprentice', json={'typed_name': 'Apprentice User'}, headers={"Authorization": "Bearer mock-apprentice-token"})
    assert second.status_code == 409
