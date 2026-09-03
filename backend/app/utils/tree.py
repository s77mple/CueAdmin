"""通用工具 — 扁平(parent_id)列表 → 树。纯函数，无 IO/ORM 依赖。

由部门树（GET /departments/tree）使用；若以后菜单等也要树，直接复用。
"""

from typing import Callable, TypeVar

T = TypeVar("T")


def nest_by_parent(
    items: list[T],
    *,
    get_id: Callable[[T], int],
    get_parent_id: Callable[[T], int | None],
    children_of: Callable[[T], list[T]],
) -> list[T]:
    """把已按 (sort_order, id) 排序的扁平节点原地挂成树，返回顶级节点列表。

    - 遍历顺序即同级顺序：输入全局有序，子节点按出现顺序挂进父的 children
    - 父缺失的节点（孤儿/脏数据）按顶级处理，graceful，不抛错
    """
    by_id: dict[int, T] = {get_id(node): node for node in items}
    roots: list[T] = []
    for node in items:
        pid = get_parent_id(node)
        parent = by_id.get(pid) if pid is not None else None
        if parent is None:
            roots.append(node)
        else:
            children_of(parent).append(node)
    return roots


def collect_subtree_ids(
    items: list[T],
    *,
    root_id: int,
    get_id: Callable[[T], int],
    get_parent_id: Callable[[T], int | None],
) -> set[int]:
    """返回以 root_id 为根的子树全部节点 id 集合（含 root 自身）。

    学 RuoYi 列表 deptId 筛选的「匹配该部门 + 全部子孙部门」（若依靠 ancestors
    列 + find_in_set）；这里部门量小，全量建父子映射后 BFS 收集即可，不必加列。
    - root 不存在 → 返回 {root_id}（IN 查不到行 = 空结果，与若依空结果一致）
    - 数据成环时靠 visited 兜底，不死循环
    """
    children_of: dict[int, list[T]] = {}
    for node in items:
        pid = get_parent_id(node)
        if pid is not None:
            children_of.setdefault(pid, []).append(node)

    result = {root_id}
    stack = [root_id]
    while stack:
        pid = stack.pop()
        for child in children_of.get(pid, []):
            cid = get_id(child)
            if cid not in result:  # visited 去重，防脏数据成环
                result.add(cid)
                stack.append(cid)
    return result
