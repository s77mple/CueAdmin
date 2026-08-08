"""
种子数据脚本：创建权限、角色、菜单、管理员账号。
运行前确保数据库存在: CREATE DATABASE cueadmin CHARACTER SET utf8mb4;
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models import User, Role, Permission, Menu, Department
from app.core.security import _hash_password_sync

# 种子脚本用同步引擎 — 不需要异步，避免 async 模式下 relationship.set 的 greenlet 陷阱
_sync_url = settings.database_url.replace("+aiomysql", "+pymysql", 1).replace("@localhost:", "@127.0.0.1:")
_sync_engine = create_engine(_sync_url, echo=False)
SyncSession = sessionmaker(_sync_engine, autoflush=False)


# ====== 权限定义 ======
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
]

ROLE_PERMS = {
    "admin": [p[0] for p in PERMISSIONS],
}

# 菜单格式: (code, name, icon, path, component, parent_code, sort_order)
# - parent_code 用 code 引用父菜单，种子脚本自动解析为 parent_id
# - component 仅叶子节点需要（如 system/users/index），父级为 None
# 注意：首页 /welcome 由前端 home.ts 静态路由提供，不需要后端菜单
MENUS = [
    # 用户管理（两级）
    ("users", "用户管理", "fa-solid:users", "/users", None, None, 2),
    ("users_index", "用户列表", None, "/users/index", "system/users/index", "users", 1),

    # 角色管理（两级）
    ("roles", "角色管理", "fa-solid:user-tag", "/roles", None, None, 3),
    ("roles_index", "角色列表", None, "/roles/index", "system/roles/index", "roles", 1),

    # 菜单管理（两级）
    ("menus", "菜单管理", "fa-solid:bars", "/menus", None, None, 4),
    ("menus_index", "菜单列表", None, "/menus/index", "system/menus/index", "menus", 1),

    # 权限管理（两级）
    ("permissions", "权限管理", "fa-solid:lock", "/permissions", None, None, 5),
    ("permissions_index", "权限列表", None, "/permissions/index", "system/permissions/index", "permissions", 1),

    # 部门管理（两级）
    ("departments", "部门管理", "fa-solid:building", "/departments", None, None, 6),
    ("departments_index", "部门列表", None, "/departments/index", "system/departments/index", "departments", 1),
]

ROLE_MENUS = {
    "admin": ["users", "users_index", "roles", "roles_index",
              "menus", "menus_index", "permissions", "permissions_index",
              "departments", "departments_index"],
}

# ====== 初始部门数据 ======
DEPARTMENTS = [
    ("ceo", "总经理室", None, 1, "公司最高决策部门"),
    ("tech", "技术部", None, 2, "负责产品研发与技术支撑"),
    ("market", "市场部", None, 3, "负责市场推广与销售"),
    ("finance", "财务部", None, 4, "负责财务管理与审计"),
]


def seed(db: Session):
    print("=== 开始种子数据初始化 ===")

    # 1. 权限
    print("\n[1/5] 创建权限...")
    perm_map: dict[str, Permission] = {}
    for code, name, resource, action in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(code=code, name=name, resource=resource, action=action)
            db.add(perm)
        perm_map[code] = perm
    db.flush()
    print(f"  -> 共 {len(perm_map)} 项权限")

    # 2. 菜单
    print("\n[2/5] 创建菜单...")
    menu_map: dict[str, Menu] = {}
    # 第一遍：创建所有菜单（parent_id 先留空）
    for code, name, icon, path, component, _parent_code, sort_order in MENUS:
        menu = db.query(Menu).filter(Menu.code == code).first()
        if not menu:
            menu = Menu(
                code=code, name=name, icon=icon,
                path=path, component=component,
                parent_id=None, sort_order=sort_order,
            )
            db.add(menu)
        else:
            menu.icon = icon
            menu.name = name
            menu.path = path
            menu.component = component
            menu.sort_order = sort_order
        menu_map[code] = menu
    db.flush()
    # 第二遍：根据 parent_code 回填 parent_id
    for code, name, icon, path, component, parent_code, sort_order in MENUS:
        if parent_code and parent_code in menu_map:
            menu_map[code].parent_id = menu_map[parent_code].id
    db.flush()
    print(f"  -> 共 {len(menu_map)} 个菜单")

    # 3. 角色
    print("\n[3/6] 创建角色...")
    roles: dict[str, Role] = {}
    for code, name, desc, is_sys in [
        ("admin", "管理员", "系统管理员", True),
    ]:
        role = db.query(Role).filter(Role.code == code).first()
        if not role:
            role = Role(code=code, name=name, description=desc, is_system=is_sys)
            db.add(role)
        roles[code] = role
    db.flush()

    # 4. 关联
    print("\n[4/6] 关联角色权限和菜单...")
    for role_code, perm_codes in ROLE_PERMS.items():
        role = roles[role_code]
        perms = [perm_map[c] for c in perm_codes if c in perm_map]
        role.permissions = perms
        print(f"  -> {role.name}: {len(perms)} 项权限")
    for role_code, menu_codes in ROLE_MENUS.items():
        role = roles[role_code]
        menus = [menu_map[c] for c in menu_codes if c in menu_map]
        role.menus = menus
        print(f"  -> {role.name}: {len(menus)} 个菜单")
    db.flush()

    # 5. 初始部门
    print("\n[5/6] 创建初始部门...")
    dept_map: dict[str, Department] = {}
    for code, name, parent_code, sort_order, desc in DEPARTMENTS:
        dept = db.query(Department).filter(Department.code == code).first()
        if not dept:
            dept = Department(
                code=code, name=name, parent_id=None,
                sort_order=sort_order, description=desc,
            )
            db.add(dept)
        dept_map[code] = dept
    db.flush()
    print(f"  -> 共 {len(dept_map)} 个部门")

    # 6. 管理员
    print("\n[6/6] 创建管理员...")
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            password_hash=_hash_password_sync("admin123"),
            display_name="管理员",
        )
        db.add(user)
    user.roles = [roles["admin"]]
    if dept_map.get("ceo"):
        user.department_id = dept_map["ceo"].id
    db.flush()

    db.commit()

    print("\n=== 种子数据初始化完成 ===")
    print("""
默认账号: admin / admin123
角色: 管理员(admin)
""")


if __name__ == "__main__":
    Base.metadata.create_all(bind=_sync_engine)
    db = SyncSession()
    try:
        seed(db)
    finally:
        db.close()
