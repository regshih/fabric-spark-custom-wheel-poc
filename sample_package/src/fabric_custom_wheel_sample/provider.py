"""Tiny deterministic API used to demonstrate wheel distribution."""

from __future__ import annotations

import hashlib

_NAMESPACE = b"fabric-custom-wheel-sample-v1:"


def transform(value: object | None) -> str | None:
    """Return a stable SAMPLE marker for *value*, preserving nulls.

    SHA-256 is used only to make repeatable opaque-looking test values. This is
    deliberately not a security, encryption, or privacy primitive.
    """
    if value is None:
        return None
    digest = hashlib.sha256(_NAMESPACE + str(value).encode("utf-8")).hexdigest()
    return f"SAMPLE_{digest[:32]}"


def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "provider": "SAMPLE",
        "package": "fabric-custom-wheel-sample",
        "warning": "Infrastructure test only; not a security control.",
    }


class SampleTransformer:
    """Serializable example class suitable for construction on Spark workers."""

    name = "sample"

    def transform(self, value: object | None) -> str | None:
        return transform(value)
