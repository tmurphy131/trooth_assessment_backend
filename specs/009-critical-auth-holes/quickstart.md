# Quickstart: Validate the Critical Auth Fixes

## 1. Automated tests
```bash
.venv/bin/python -m pytest tests/test_critical_auth_holes.py tests/test_agreements.py tests/test_connected_apprentice_linking.py -q
```
Expected: all pass. The new tests check that:
- a repeat signup can't change the role or become admin
- naming another person's email does nothing
- an unverified email doesn't re-link
- both removed routes are gone and create nothing
- the parent token link still activates the agreement

See [contracts/auth-holes.md](contracts/auth-holes.md) for the expected status codes.

## 2. Manual checks on dev (after `/deploy-dev`)
1. **New signup:** create a fresh account in the app (email and password, then Apple or Google). It lands on the right dashboard.
2. **Re-open:** sign out and back in. No error, same role.
3. **Abuse probe**, with a dev account's ID token in `$TOKEN`:
   ```bash
   curl -s -X POST "$DEV/users/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"uid":"x","email":"someone-else@example.com","name":"X","role":"admin"}'
   ```
   Expected: 200 with **your own** account and its original role (existing account), or 403 for a brand-new account. Never admin, and never another account.
   The removed routes in step 4 return 404 or 405 (`assign-apprentice` returns 405).
4. **Removed routes:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -X POST "$DEV/users/assign-apprentice?mentor_id=a&apprentice_id=b"   # 404/405
   curl -s -o /dev/null -w "%{http_code}\n" -X POST "$DEV/agreements/abc/sign/parent" -H 'Content-Type: application/json' -d '{"typed_name":"x"}'  # 404/405
   ```
5. **Minor agreement:** send one to a test minor, sign as the apprentice, then sign through the emailed parent link. Status becomes fully signed.

## 3. After the prod deploy: audit
```bash
DATABASE_URL=<prod read-only url> .venv/bin/python scripts/audit_admin_accounts.py
```
Expected: only known operator accounts are admins.

```bash
DATABASE_URL=<prod read-only url> .venv/bin/python scripts/find_role_changes_in_logs.py --freshness 30d
```
For each uid it lists, check whether the account existed before that request (a repeat signup, so a possible role change). Investigate and revert anything unexpected. Together these satisfy SC-006. Older changes can't be detected, because role history isn't stored.
