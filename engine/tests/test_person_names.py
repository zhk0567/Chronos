from __future__ import annotations

from utils.person_names import build_canonical_map, normalize_person_name


def test_merge_family_aliases():
    names = ["妈", "妈妈", "妈妈", "老爸"]
    cmap = build_canonical_map(names)
    assert normalize_person_name("妈", cmap) == "妈妈"
    assert normalize_person_name("老妈", cmap) == "妈妈"
    assert normalize_person_name("老爸", cmap) == "老爸"
