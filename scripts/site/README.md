# onlyblv.com site tools

The marketing site (onlyblv.com) is static HTML in [`site_files/`](../../site_files), hosted on
Namecheap shared hosting (cPanel, document root `public_html`). `site_files/` mirrors the server.

## Credentials (local only)

| File | Contents |
|---|---|
| `~/.config/onlyblv/cpanel.env` | `CPANEL_HOST`, `CPANEL_USER`, `CPANEL_TOKEN` (cPanel API token, chmod 600) |
| `~/.config/onlyblv/test_accounts.env` | Guide test-account emails and passwords (written by `create_accounts.py`) |

Never commit or print these. A cPanel token has full account access; revoke it in
cPanel > Security > Manage API Tokens if a machine is lost.

## Publish site changes

```bash
scripts/site/deploy.sh --dry-run index.html guides.html guides   # see what would upload
scripts/site/deploy.sh index.html guides.html guides             # upload
```

Paths are relative to `site_files/` (files or folders). Live copies of anything being overwritten
are saved to `~/.cache/onlyblv/site-backups/<timestamp>/` first; nothing on the server is deleted.
Check the result at https://onlyblv.com (hard-refresh if a page looks stale).

## Refresh the user-guide screenshots

The guides (`site_files/guides.html`) use real app screenshots under `site_files/guides/`.

**T[root]H Armory** (no accounts or network; needs the Armory repo next to this one):

```bash
python3 scripts/site/guide_capture/capture_armory.py
```

**T[root]H Discipleship** (DEV backend, two linked test accounts: mentor "Marcus Johnson" and
apprentice "Jordan Davis"; needs the Flutter app repo next to this one):

```bash
cd scripts/site/guide_capture
python3 seed/create_accounts.py        # create or reuse the accounts (+ pending invite if not linked)
python3 seed/seed_data.py draft        # an unsubmitted assessment for the "draft" shots
python3 capture.py a                   # sign-up, dashboard with draft, invitation, assessment, gifts
python3 seed/seed_data.py complete     # accept invite, submit work, prayers (waits for AI scoring)
python3 capture.py b                   # everything else (free plan)
seed/set_plan.sh premium               # optional: Premium report and gift-seat shots
python3 seed/seed_data.py complete     # warms the Premium full reports
python3 capture.py b TIER=premium ONLY=apprentice_report,apprentice_premium,mentor_full_report,mentor_premium
```

`capture.py` copies `guide_capture_test.dart` into the app repo's `integration_test/`, runs it on
the "iPhone 17 Pro" simulator (`SIM_NAME` to change), screenshots each `CAPTURE:<name>`, then removes
the file and resets the iOS build config. It talks to dev through the Cloud Run URL so the app's DEV
corner banner stays out of the shots. Use `ONLY=<step>,<step>` to retake single steps. Screenshots
land in `~/.cache/onlyblv/guide-shots/`.

Then build the web images and publish:

```bash
uv run --with pillow python scripts/site/guide_capture/prepare_images.py    # all, or pass output names
scripts/site/deploy.sh guides
```

`prepare_images.py` holds the map from capture names to the image names the pages use; update it
(and the HTML) when adding a screenshot.

### Notes

- The Firebase project (`only-blv`) is shared by dev and prod, so the test logins exist in prod
  Firebase Auth too, but they only have backend data on dev. The seed scripts refuse prod API URLs.
- If AI scoring is down on dev, reports come back empty; `seed_data.py complete` warns about it.
- The app logs a few debug-only framework assertions, so `flutter test` may report a failure even
  when every shot was taken. `capture.py` judges the run by its own `SHOTFAIL` lines.
