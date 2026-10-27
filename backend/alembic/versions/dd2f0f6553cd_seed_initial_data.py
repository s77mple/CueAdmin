"""seed initial data

Revision ID: dd2f0f6553cd
Revises: 1b8e4f5a9c2d7
Create Date: 2026-10-27 09:41:55.624810

把原先 seed.py 的种子数据搬进迁移：`alembic upgrade head` 一条命令即可
完成建表 + 初始化数据，不再需要单独跑 seed.py。

写入全部幂等（ON DUPLICATE KEY UPDATE / INSERT IGNORE），
已经跑过 seed.py 的开发库升级上来不会产生重复数据。
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import insert as mysql_insert

revision: str = "dd2f0f6553cd"
down_revision: str | None = "1b8e4f5a9c2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ============================================================
# 种子数据定义（与旧 seed.py 保持一致）
# ============================================================

# (code, name, resource, action)
PERMISSIONS = [
    ("user:list", "用户列表", "user", "list"),
    ("user:create", "创建用户", "user", "create"),
    ("user:update", "编辑用户", "user", "update"),
    ("user:delete", "删除用户", "user", "delete"),
    ("role:list", "角色列表", "role", "list"),
    ("role:create", "创建角色", "role", "create"),
    ("role:update", "编辑角色", "role", "update"),
    ("role:delete", "删除角色", "role", "delete"),
    ("menu:list", "菜单列表", "menu", "list"),
    ("menu:create", "创建菜单", "menu", "create"),
    ("menu:update", "编辑菜单", "menu", "update"),
    ("menu:delete", "删除菜单", "menu", "delete"),
    ("permission:list", "查看权限", "permission", "list"),
    ("permission:create", "创建权限", "permission", "create"),
    ("permission:update", "更新权限", "permission", "update"),
    ("permission:delete", "删除权限", "permission", "delete"),
    ("department:list", "查看部门", "department", "list"),
    ("department:create", "创建部门", "department", "create"),
    ("department:update", "更新部门", "department", "update"),
    ("department:delete", "删除部门", "department", "delete"),
    ("post:list", "岗位列表", "post", "list"),
    ("post:create", "创建岗位", "post", "create"),
    ("post:update", "编辑岗位", "post", "update"),
    ("post:delete", "删除岗位", "post", "delete"),
]

# (code, name, icon, path, component, parent_code, sort_order)
MENUS = [
    ("users", "用户管理", "fa-solid:users", "/users", None, None, 2),
    ("users_index", "用户列表", None, "/users/index", "system/users/index", "users", 1),
    ("roles", "角色管理", "fa-solid:user-tag", "/roles", None, None, 3),
    ("roles_index", "角色列表", None, "/roles/index", "system/roles/index", "roles", 1),
    ("menus", "菜单管理", "fa-solid:bars", "/menus", None, None, 4),
    ("menus_index", "菜单列表", None, "/menus/index", "system/menus/index", "menus", 1),
    ("permissions", "权限管理", "fa-solid:lock", "/permissions", None, None, 5),
    ("permissions_index", "权限列表", None, "/permissions/index", "system/permissions/index", "permissions", 1),
    ("departments", "部门管理", "fa-solid:building", "/departments", None, None, 6),
    ("departments_index", "部门列表", None, "/departments/index", "system/departments/index", "departments", 1),
    ("posts", "岗位管理", "fa-solid:briefcase", "/posts", None, None, 7),
    ("posts_index", "岗位列表", None, "/posts/index", "system/posts/index", "posts", 1),
    ("error-codes", "错误码字典", "fa-solid:book", "/error-codes", None, None, 8),
    ("error-codes_index", "错误码列表", None, "/error-codes/index", "system/error-codes/index", "error-codes", 1),
]

# (code, name, sort_order, description)
DEPARTMENTS = [
    ("ceo", "总经理室", 1, "公司最高决策部门"),
    ("tech", "技术部", 2, "负责产品研发与技术支撑"),
    ("market", "市场部", 3, "负责市场推广与销售"),
    ("finance", "财务部", 4, "负责财务管理与审计"),
]

# (code, name, sort_order, description)
POSTS = [
    ("ceo", "董事长", 1, "公司战略决策与整体经营管理"),
    ("se", "项目经理", 2, "负责项目规划、进度与交付"),
    ("hr", "人力资源", 3, "负责招聘、培训与员工关系"),
    ("user", "普通员工", 4, "普通员工岗位"),
]

# admin123 的 bcrypt 哈希。写成常量而不是调用 app.core.security：
# 迁移脚本要独立于业务代码，密码策略变化不应让历史迁移失效。
ADMIN_PASSWORD_HASH = "$2b$12$WR0A0C517zq7U7Qug.uYsek/Fzts53Yu14lRvkbqWOvN0WPv4OlES"

ROLE_CODE = "admin"
USERNAME = "admin"
DEPARTMENT_CODE = "ceo"
POST_CODE = "ceo"


# ============================================================
# 最小表定义 —— 不 import app.models（模型会随时间变化，迁移必须冻结在当时）
# ============================================================

permissions = sa.table(
    "permissions",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
)
menus = sa.table(
    "menus",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("icon", sa.String),
    sa.column("path", sa.String),
    sa.column("component", sa.String),
    sa.column("parent_id", sa.BigInteger),
    sa.column("sort_order", sa.Integer),
)
roles = sa.table(
    "roles",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("is_system", sa.Boolean),
)
departments = sa.table(
    "departments",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("description", sa.Text),
)
posts = sa.table(
    "posts",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("description", sa.String),
)
users = sa.table(
    "users",
    sa.column("id", sa.BigInteger),
    sa.column("username", sa.String),
    sa.column("password_hash", sa.String),
    sa.column("display_name", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("department_id", sa.BigInteger),
)
role_permissions = sa.table(
    "role_permissions",
    sa.column("role_id", sa.BigInteger),
    sa.column("permission_id", sa.BigInteger),
)
role_menus = sa.table(
    "role_menus",
    sa.column("role_id", sa.BigInteger),
    sa.column("menu_id", sa.BigInteger),
)
user_roles = sa.table(
    "user_roles",
    sa.column("user_id", sa.BigInteger),
    sa.column("role_id", sa.BigInteger),
)
user_posts = sa.table(
    "user_posts",
    sa.column("user_id", sa.BigInteger),
    sa.column("post_id", sa.BigInteger),
)


def _upsert(table: sa.TableClause, rows: list[dict], update_columns: Sequence[str]) -> None:
    """按唯一键插入；已存在则只更新指定列（保持重复执行结果一致）。"""
    stmt = mysql_insert(table).values(rows)
    op.execute(
        stmt.on_duplicate_key_update(
            **{name: stmt.inserted[name] for name in update_columns}
        )
    )


def _link(
    table: sa.TableClause,
    columns: Sequence[str],
    select_stmt: sa.Select,
) -> None:
    """插入多对多关联；联合主键冲突时忽略。"""
    op.execute(
        sa.insert(table)
        .prefix_with("IGNORE")
        .from_select(list(columns), select_stmt)
    )


def upgrade() -> None:
    # ---- 权限 ----
    _upsert(
        permissions,
        [
            {"code": code, "name": name, "resource": resource, "action": action}
            for code, name, resource, action in PERMISSIONS
        ],
        ["name", "resource", "action"],
    )

    # ---- 菜单（parent_id 分两遍回填：父菜单可能尚未插入）----
    _upsert(
        menus,
        [
            {
                "code": code,
                "name": name,
                "icon": icon,
                "path": path,
                "component": component,
                "parent_id": None,
                "sort_order": sort_order,
            }
            for code, name, icon, path, component, _parent_code, sort_order in MENUS
        ],
        ["name", "icon", "path", "component", "sort_order"],
    )
    for code, _name, _icon, _path, _component, parent_code, _sort_order in MENUS:
        if not parent_code:
            continue
        # MySQL 不允许在 UPDATE 的子查询里引用同一张表，这里用自连接
        op.execute(
            sa.text(
                "UPDATE menus AS child "
                "JOIN menus AS parent ON parent.code = :parent_code "
                "SET child.parent_id = parent.id "
                "WHERE child.code = :code"
            ).bindparams(parent_code=parent_code, code=code)
        )

    # ---- 角色 ----
    _upsert(
        roles,
        [
            {
                "code": ROLE_CODE,
                "name": "管理员",
                "description": "系统管理员",
                "is_system": True,
            }
        ],
        ["name", "description", "is_system"],
    )

    # ---- 角色 ↔ 权限 / 菜单 ----
    _link(
        role_permissions,
        ["role_id", "permission_id"],
        sa.select(roles.c.id, permissions.c.id)
        .select_from(
            # 显式 join，避免 SQLAlchemy 对「两表笛卡尔积」发警告
            roles.join(
                permissions,
                permissions.c.code.in_([p[0] for p in PERMISSIONS]),
            )
        )
        .where(roles.c.code == ROLE_CODE),
    )
    _link(
        role_menus,
        ["role_id", "menu_id"],
        sa.select(roles.c.id, menus.c.id)
        .select_from(
            roles.join(menus, menus.c.code.in_([m[0] for m in MENUS]))
        )
        .where(roles.c.code == ROLE_CODE),
    )

    # ---- 部门 ----
    _upsert(
        departments,
        [
            {
                "code": code,
                "name": name,
                "sort_order": sort_order,
                "description": description,
            }
            for code, name, sort_order, description in DEPARTMENTS
        ],
        ["name", "sort_order", "description"],
    )

    # ---- 岗位 ----
    _upsert(
        posts,
        [
            {
                "code": code,
                "name": name,
                "sort_order": sort_order,
                "description": description,
            }
            for code, name, sort_order, description in POSTS
        ],
        ["name", "sort_order", "description"],
    )

    # ---- 管理员用户（已存在则不覆盖密码）----
    op.execute(
        mysql_insert(users)
        .prefix_with("IGNORE")
        .values(
            username=USERNAME,
            password_hash=ADMIN_PASSWORD_HASH,
            display_name="管理员",
            is_active=True,
        )
    )

    # 已存在但没部门的 admin → 补上；已有部门的不覆盖
    op.execute(
        sa.text(
            "UPDATE users AS u "
            "JOIN departments AS d ON d.code = :department_code "
            "SET u.department_id = d.id "
            "WHERE u.username = :username AND u.department_id IS NULL"
        ).bindparams(department_code=DEPARTMENT_CODE, username=USERNAME)
    )

    # ---- 用户 ↔ 角色 / 岗位 ----
    _link(
        user_roles,
        ["user_id", "role_id"],
        sa.select(users.c.id, roles.c.id)
        .select_from(users.join(roles, roles.c.code == ROLE_CODE))
        .where(users.c.username == USERNAME),
    )
    _link(
        user_posts,
        ["user_id", "post_id"],
        sa.select(users.c.id, posts.c.id)
        .select_from(users.join(posts, posts.c.code == POST_CODE))
        .where(users.c.username == USERNAME),
    )


def downgrade() -> None:
    # 种子数据是系统运行的前提（权限/菜单/admin 角色），回退迁移不删除数据，
    # 否则 downgrade 会连带清空业务数据。只回退版本标记。
    pass
