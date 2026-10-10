"""Capture T[root]H Discipleship screenshots for the onlyblv.com user guides.

    python3 scripts/site/guide_capture/capture.py a                      # stage a (fresh seed)
    python3 scripts/site/guide_capture/capture.py b TIER=premium         # stage b, premium accounts
    python3 scripts/site/guide_capture/capture.py b ONLY=mentor_gifts    # just one step

Copies guide_capture_test.dart into the Flutter repo's integration_test/, runs it on an iOS
simulator against DEV, and takes a simulator screenshot every time the test prints
CAPTURE:<name>. The test file is always removed afterwards and the iOS build config is reset
(`flutter test` repoints ios/Flutter/Generated.xcconfig).

Env: TROOTH_APP_REPO (default ../trooth_assessment next to this repo), SIM_NAME (default
"iPhone 17 Pro"), GUIDE_SHOTS_DIR (default ~/.cache/onlyblv/guide-shots/discipleship).
Accounts come from ~/.config/onlyblv/test_accounts.env (see seed/create_accounts.py).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
APP_REPO = os.environ.get("TROOTH_APP_REPO", os.path.join(os.path.dirname(BACKEND), "trooth_assessment"))
SIM_NAME = os.environ.get("SIM_NAME", "iPhone 17 Pro")
OUT = os.path.expanduser(os.environ.get("GUIDE_SHOTS_DIR", "~/.cache/onlyblv/guide-shots/discipleship"))
TEST_NAME = "guide_capture_test.dart"


def find_simulator(name):
    devices = json.loads(subprocess.run(["xcrun", "simctl", "list", "devices", "available", "-j"],
                                        capture_output=True, text=True, check=True).stdout)["devices"]
    matches = [d for runtime in sorted(devices, reverse=True) for d in devices[runtime] if d["name"] == name]
    if not matches:
        sys.exit(f"No available simulator named {name!r} (set SIM_NAME)")
    booted = [d for d in matches if d["state"] == "Booted"]  # reuse a warm one; first builds are slow
    return (booted or matches)[0]["udid"]


def prepare_simulator(sim):
    subprocess.run(["xcrun", "simctl", "boot", sim], capture_output=True)
    subprocess.run(["xcrun", "simctl", "status_bar", sim, "override", "--time", "9:41", "--batteryState", "charged",
                    "--batteryLevel", "100", "--cellularBars", "4", "--wifiBars", "3"], capture_output=True)


def load_accounts():
    env = {}
    with open(os.path.expanduser("~/.config/onlyblv/test_accounts.env")) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("a", "b"):
        sys.exit(__doc__)
    stage, extra = sys.argv[1], sys.argv[2:]
    os.makedirs(OUT, exist_ok=True)
    sim = find_simulator(SIM_NAME)
    prepare_simulator(sim)

    defines = [f"--dart-define={k}={v}" for k, v in load_accounts().items()]
    defines += [f"--dart-define=STAGE={stage}"] + [f"--dart-define={a}" for a in extra]
    test_path = os.path.join(APP_REPO, "integration_test", TEST_NAME)
    shutil.copy(os.path.join(HERE, TEST_NAME), test_path)
    failures = 0
    try:
        with open(os.path.join(OUT, f"stage_{stage}.log"), "w") as log:
            proc = subprocess.Popen(["flutter", "test", f"integration_test/{TEST_NAME}", "-d", sim, *defines],
                                    cwd=APP_REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                log.write(line)
                log.flush()
                if "CAPTURE:" in line:
                    name = line.split("CAPTURE:", 1)[1].strip()
                    subprocess.run(["xcrun", "simctl", "io", sim, "screenshot", os.path.join(OUT, f"{name}.png")],
                                   capture_output=True)
                    print("shot", name, flush=True)
                elif "SHOTFAIL" in line or "SHOTSTACK" in line:
                    failures += "SHOTFAIL" in line
                    print(line.strip()[:300], flush=True)
            proc.wait()
    finally:
        os.remove(test_path)
        subprocess.run(["flutter", "build", "ios", "--config-only"], cwd=APP_REPO, capture_output=True)
        subprocess.run(["xcrun", "simctl", "status_bar", sim, "clear"], capture_output=True)
    # The app logs a few debug-only framework assertions, so the test itself reports failure even
    # when every shot was taken; judge the run by SHOTFAIL lines instead.
    print(f"Screenshots in {OUT} ({failures} step(s) failed)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
