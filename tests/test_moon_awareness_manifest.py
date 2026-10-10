from __future__ import annotations

import json
from pathlib import Path


def test_moon_awareness_manifest_is_metadata_only() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "moon.manifest.yaml").read_text(encoding="utf-8"))

    assert payload["moon_version"] == "0.1"
    assert payload["service_id"] == "hello-world-marketplace"
    assert payload["name"] == "Hello, World! Marketplace"
    assert payload["type"] == "commerce-marketplace"
    assert payload["owner"] == "Moon Commerce"
    assert payload["version"] == "0.0.1.dev0"
    assert payload["environment"] == "development"
    assert payload["repository"] == "open-trust-layer/marketplace"
    assert payload["documentation"] == "README.md"

    assert payload["capabilities"] == []
    assert payload["actions"] == []
    assert payload["dependencies"] == ["olp-protocol"]
    assert payload["health"] == {"kind": "workspace"}
    assert payload["events"] == {"publish": [], "subscribe": []}
    assert payload["knowledge_domains"] == [
        "marketplace-semantics",
        "economic-coordination",
        "olp-evidence-integration",
    ]

    assert "endpoints" not in payload
    assert "permissions" not in payload
    assert "identity" not in payload
