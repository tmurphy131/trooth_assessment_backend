"""Capture T[root]H Armory screenshots for the onlyblv.com user guide.

    python3 scripts/site/guide_capture/capture_armory.py

Runs two flutter drive passes in the Armory repo on an iOS simulator (light appearance):
  1. the app's own store screenshot test (home, topic, search, share, saved, dark, help)
  2. armory_guide_screens_test.dart from this folder (verse options, personalize, settings),
     copied in for the run and removed afterwards.
No accounts or network needed. Output: ~/.cache/onlyblv/guide-shots/armory (GUIDE_SHOTS_DIR).
Env: ARMORY_REPO (default ../trooth_armory_app next to this repo), SIM_NAME (default "iPhone 17 Pro").
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from capture import find_simulator, prepare_simulator  # noqa: E402

BACKEND = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ARMORY = os.environ.get("ARMORY_REPO", os.path.join(os.path.dirname(BACKEND), "trooth_armory_app"))
OUT = os.path.expanduser(os.environ.get("GUIDE_SHOTS_DIR", "~/.cache/onlyblv/guide-shots/armory"))
TEST_NAME = "armory_guide_screens_test.dart"


def drive(sim, target):
    subprocess.run(["flutter", "drive", "--driver=test_driver/screenshot_driver.dart", f"--target={target}",
                    "-d", sim, "--flavor", "dev"], cwd=ARMORY, check=True, env={**os.environ, "SCREENSHOT_DIR": OUT})


def main():
    os.makedirs(OUT, exist_ok=True)
    sim = os.environ.get("SIM_UDID") or find_simulator(os.environ.get("SIM_NAME", "iPhone 17 Pro"))
    prepare_simulator(sim)
    subprocess.run(["xcrun", "simctl", "ui", sim, "appearance", "light"], capture_output=True)
    test_path = os.path.join(ARMORY, "integration_test", TEST_NAME)
    shutil.copy(os.path.join(HERE, TEST_NAME), test_path)
    try:
        drive(sim, "integration_test/screenshots_test.dart")
        drive(sim, f"integration_test/{TEST_NAME}")
    finally:
        os.remove(test_path)
        subprocess.run(["xcrun", "simctl", "status_bar", sim, "clear"], capture_output=True)
    print(f"Screenshots in {OUT}")


if __name__ == "__main__":
    main()
