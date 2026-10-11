"""Tests for the canonical cursor role table."""

from __future__ import annotations

from pathlib import Path

import pytest

from ani2xcur import roles
from ani2xcur.config.inf import load_inf


@pytest.mark.parametrize("fixture_name", ["miku_dir", "zutomayo_dir"])
def test_every_sample_key_maps(request, fixture_name: str) -> None:
    root: Path = request.getfixturevalue(fixture_name)
    inf = load_inf(next(root.rglob("*.inf")))
    for key in inf.cursor_entries():
        assert roles.resolve(key) is not None, f"unmapped key: {key!r}"


@pytest.mark.parametrize(
    ("key", "canonical"),
    [
        ("pointer", "pointer"),
        ("arrow", "pointer"),
        ("working", "work"),
        ("work", "work"),
        ("precision", "cross"),
        ("hand", "handwriting"),
        ("handwrt", "handwriting"),
        ("unavailable", "unavailable"),
        ("unavailiable", "unavailable"),
        ("vert", "vert"),
        ("horz", "horz"),
        ("dgn1", "dgn1"),
        ("dgn2", "dgn2"),
        ("alternate", "alternate"),
        ("link", "link"),
        ("pin", "pin"),
        ("person", "person"),
    ],
)
def test_resolve_mappings(key: str, canonical: str) -> None:
    role = roles.resolve(key)
    assert role is not None
    assert role.canonical == canonical


def test_resolve_is_case_insensitive_and_unknown_is_none() -> None:
    assert roles.resolve("POINTER") is roles.resolve("pointer")
    assert roles.resolve("definitely-not-a-role") is None


def test_roles_are_well_formed() -> None:
    all_roles = roles.load_roles()
    assert all_roles
    for role in all_roles:
        assert role.canonical in role.keys
        assert role.x11, f"{role.canonical} has no X11 aliases"


def test_keys_are_unique_across_roles() -> None:
    seen: dict[str, str] = {}
    for role in roles.load_roles():
        for key in {role.canonical, *role.keys}:
            key = key.lower()
            assert key not in seen, f"key {key!r} in {role.canonical} and {seen[key]}"
            seen[key] = role.canonical


def test_x11_names_are_unique_across_roles() -> None:
    seen: dict[str, str] = {}
    for role in roles.load_roles():
        for name in role.x11:
            assert name not in seen, f"{name!r} in {role.canonical} and {seen[name]}"
            seen[name] = role.canonical


def test_sanitize_name() -> None:
    assert roles.sanitize_name("Hello World/../x") == "Hello-World-..-x"
    assert roles.sanitize_name("  ") == "unnamed"
