from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "custom_components/flight_tracker/manifest.json"
CARD_PATH = REPO_ROOT / "custom_components/flight_tracker/frontend/flight-tracker-card.js"
README_PATH = REPO_ROOT / "README.md"


def test_manifest_readme_and_card_versions_are_aligned() -> None:
    manifest_version = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]
    card_source = CARD_PATH.read_text(encoding="utf-8")
    readme_source = README_PATH.read_text(encoding="utf-8")

    card_match = re.search(r'const CARD_VERSION = "([^"]+)";', card_source)
    readme_match = re.search(r"/flight_tracker_static/flight-tracker-card\.js\?v=([0-9.]+)", readme_source)

    assert card_match is not None
    assert readme_match is not None
    assert card_match.group(1) == manifest_version
    assert readme_match.group(1) == manifest_version
