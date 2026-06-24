from __future__ import annotations

from collections import Counter, defaultdict

# 常见称谓别名 → 归一化键（用于合并同一人物）
_ALIAS_GROUPS: list[frozenset[str]] = [
    frozenset({"妈妈", "妈", "老妈", "母亲", "我妈", "妈咪"}),
    frozenset({"爸爸", "爸", "老爸", "父亲", "我爸", "爹"}),
    frozenset({"爷爷", "爷", "祖父", "我爷"}),
    frozenset({"奶奶", "祖母", "我奶"}),
    frozenset({"外公", "姥爷", "外祖父"}),
    frozenset({"外婆", "姥姥", "外祖母"}),
    frozenset({"老公", "丈夫", "先生", "爱人"}),
    frozenset({"老婆", "妻子", "媳妇", "爱人"}),
    frozenset({"朋友", "好友", "闺蜜", "哥们"}),
    frozenset({"同事", "工友", "同僚"}),
    frozenset({"老板", "领导", "上司", "主管"}),
    frozenset({"老师", "导师", "师父"}),
    frozenset({"自己", "我", "本人"}),
]

_NAME_TO_GROUP: dict[str, int] = {}
for idx, group in enumerate(_ALIAS_GROUPS):
    for name in group:
        _NAME_TO_GROUP[name] = idx


def _group_id(name: str) -> int | None:
    name = name.strip()
    if not name:
        return None
    if name in _NAME_TO_GROUP:
        return _NAME_TO_GROUP[name]
    for alias, gid in _NAME_TO_GROUP.items():
        if len(alias) >= 2 and (name.endswith(alias) or alias in name):
            return gid
    return None


def build_canonical_map(names: list[str]) -> dict[str, str]:
    """将原始称谓映射为合并后的规范名（取该组内提及次数最多者）。"""
    counts = Counter(names)
    group_members: dict[int, list[str]] = defaultdict(list)
    ungrouped: list[str] = []

    for name in counts:
        gid = _group_id(name)
        if gid is None:
            ungrouped.append(name)
        else:
            group_members[gid].append(name)

    canonical: dict[str, str] = {}
    for members in group_members.values():
        best = max(members, key=lambda m: counts[m])
        for m in members:
            canonical[m] = best
    for name in ungrouped:
        canonical[name] = name
    return canonical


def normalize_person_name(name: str, canonical_map: dict[str, str]) -> str:
    name = name.strip()
    if name in canonical_map:
        return canonical_map[name]
    gid = _group_id(name)
    if gid is not None:
        for alias, canonical in canonical_map.items():
            if _group_id(alias) == gid:
                return canonical
        return max(_ALIAS_GROUPS[gid], key=len)
    return name
