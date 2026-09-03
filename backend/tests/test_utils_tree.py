"""app/utils/tree.py 纯函数单元测试 — 无 IO，普通同步测试。

覆盖 collect_subtree_ids（用户列表 dept_id 含子孙筛选用的子树收 id）。
运行：cd backend && pytest tests/test_utils_tree.py
"""

from app.utils.tree import collect_subtree_ids


def _depts(rows):
    """rows: [(id, parent_id), ...] → 与 ORM Department 形状一致的 dict 列表。"""
    return [{"id": i, "parent_id": p} for i, p in rows]


def _collect(items, root_id):
    return collect_subtree_ids(
        items,
        root_id=root_id,
        get_id=lambda d: d["id"],
        get_parent_id=lambda d: d["parent_id"],
    )


def test_subtree_collects_self_and_all_descendants():
    items = _depts([(1, None), (2, 1), (3, 1), (4, 2), (5, None)])
    assert _collect(items, 1) == {1, 2, 3, 4}


def test_subtree_leaf_returns_only_self():
    items = _depts([(1, None), (2, 1), (3, 1)])
    assert _collect(items, 2) == {2}


def test_subtree_unknown_root_is_singleton():
    """root 不存在 → 返回 {root_id}，IN 查不到行 = 空结果（与若依行为一致）。"""
    items = _depts([(1, None)])
    assert _collect(items, 999) == {999}


def test_subtree_empty_items_returns_root_singleton():
    assert _collect([], 1) == {1}


def test_subtree_handles_cycle_without_infinite_loop():
    """脏数据成环（1 的父是 2、2 的父是 1）— visited 去重兜底不卡死。"""
    items = _depts([(1, 2), (2, 1)])
    assert _collect(items, 1) == {1, 2}
