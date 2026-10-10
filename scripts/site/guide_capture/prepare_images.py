"""Turn raw guide screenshots into the web images used by site_files/guides.html and index.html.

    uv run --with pillow python scripts/site/guide_capture/prepare_images.py [name ...]

Reads ~/.cache/onlyblv/guide-shots/{discipleship,armory}/*.png (from capture.py and
capture_armory.py), resizes to 600px wide JPEG (quality 85), and writes them into
site_files/guides/{discipleship,armory}/ under the names the pages use. Pass output names
(e.g. mentor_gifts report_free_summary) to only rebuild those; missing sources are skipped.
Then upload with: scripts/site/deploy.sh guides
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "site_files"))
SHOTS = os.path.expanduser(os.environ.get("GUIDE_SHOTS_ROOT", "~/.cache/onlyblv/guide-shots"))
WIDTH = 600

# output name in site_files/guides/<app>/  ->  capture name (<app> shots folder, .png)
DISCIPLESHIP = {
    "signup": "signup",
    "apprentice_dashboard": "apprentice_dashboard_draft",
    "apprentice_invites": "apprentice_invites",
    "apprentice_mentor": "apprentice_mentor",
    "choose_assessment": "apprentice_new_assessment",
    "assessment_question": "apprentice_assessment",
    "report_free_summary": "apprentice_report_free_1",
    "report_free_insights": "apprentice_report_free_3",
    "report_premium_summary": "apprentice_report_premium_1",
    "report_premium_pathway": "apprentice_report_premium_4",
    "report_premium_knowledge": "apprentice_report_premium_5",
    "gifts_assessment": "gifts_assessment",
    "gifts_results": "gifts_results",
    "apprentice_progress": "apprentice_progress",
    "apprentice_resources": "apprentice_resources",
    "prayer_journal": "prayer_journal",
    "prayer_editor": "prayer_editor",
    "trivia_home": "trivia_home",
    "choose_assessment_premium": "choose_assessment_premium",
    "apprentice_subscription_premium": "apprentice_subscription_premium",
    "mentor_dashboard": "mentor_dashboard",
    "mentor_invite": "mentor_invite",
    "mentor_menu": "mentor_menu",
    "mentor_agreements": "mentor_agreements",
    "mentor_assessments": "mentor_assessments",
    "mentor_report_answers": "mentor_report",  # Answers tab
    "mentor_report_summary": "mentor_report_free_2",  # _1 shows a debug overflow stripe on "Growth Areas"
    "mentor_full_report": "mentor_full_report_1",
    "mentor_full_report_pathway": "mentor_full_report_3",
    "mentor_gifts": "mentor_gifts",
    "mentor_prayers": "mentor_prayers",
    "mentor_resources": "mentor_resources",
    "mentor_subscription_premium": "mentor_subscription_premium",
    "mentor_gift_seats": "mentor_gift_seats",
}
ARMORY = {
    "home": "01_home",
    "topic": "02_category",
    "search": "03_search",
    "share_card": "04_share",
    "saved": "05_saved",
    "dark_mode": "06_dark",
    "get_help": "07_help",
    "verse_options": "g_options",
    "personalize": "g_personalize",
    "settings": "g_settings",
}


def convert(src, dst):
    im = Image.open(src).convert("RGB")
    im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, "JPEG", quality=85, optimize=True, progressive=True)


def main():
    wanted = set(sys.argv[1:])
    done = skipped = 0
    for app, mapping in (("discipleship", DISCIPLESHIP), ("armory", ARMORY)):
        for out_name, shot in mapping.items():
            if wanted and out_name not in wanted:
                continue
            src = os.path.join(SHOTS, app, f"{shot}.png")
            if not os.path.exists(src):
                skipped += 1
                continue
            convert(src, os.path.join(SITE, "guides", app, f"{out_name}.jpg"))
            done += 1
    print(f"Wrote {done} image(s) to site_files/guides/ ({skipped} skipped: no capture)")


if __name__ == "__main__":
    main()
