"""
种子数据脚本：创建权限、角色、菜单、管理员账号。
运行前确保数据库存在: CREATE DATABASE cueadmin CHARACTER SET utf8mb4;
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_engine, AsyncSessionLocal, Base
from app.models import User, Role, Permission, Menu
from app.core.security import _hash_password_sync

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
]

ROLE_PERMS = {
    "admin": [p[0] for p in PERMISSIONS],
}

# ====== 菜单定义 ======
MENUS = [
    # (code, name, icon, path, parent_id, sort_order)
    ("dashboard",    "仪表盘",   "Odometer",  "/dashboard",    None, 1),
    ("users",        "用户管理", "UserFilled","/users",        None, 2),
    ("roles",        "角色管理", "Avatar",    "/roles",        None, 3),
    ("menus",        "菜单管理", "Menu",      "/menus",        None, 4),
    ("permissions",  "权限管理", "Lock",      "/permissions",  None, 5),
]

ROLE_MENUS = {
    "admin": ["dashboard", "users", "roles", "menus", "permissions"],
}


async def seed(db: AsyncSession):
    print("=== 开始种子数据初始化 ===")

    # 1. 权限
    print("\n[1/5] 创建权限...")
    perm_map: dict[str, Permission] = {}
    for code, name, resource, action in PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalars().first()
        if not perm:
            perm = Permission(code=code, name=name, resource=resource, action=action)
            db.add(perm)
        perm_map[code] = perm
    await db.flush()
    print(f"  -> 共 {len(perm_map)} 项权限")

    # 2. 菜单
    print("\n[2/5] 创建菜单...")
    menu_map: dict[str, Menu] = {}
    for code, name, icon, path, parent_id, sort_order in MENUS:
        result = await db.execute(select(Menu).where(Menu.code == code))
        menu = result.scalars().first()
        if not menu:
            menu = Menu(code=code, name=name, icon=icon,
                        path=path, parent_id=parent_id, sort_order=sort_order)
            db.add(menu)
        else:
            menu.icon = icon
            menu.sort_order = sort_order
        menu_map[code] = menu
    await db.flush()
    print(f"  -> 共 {len(menu_map)} 个菜单")

    # 3. 角色
    print("\n[3/5] 创建角色...")
    roles: dict[str, Role] = {}
    for code, name, desc, is_sys in [
        ("admin", "管理员", "系统管理员", True),
    ]:
        result = await db.execute(select(Role).where(Role.code == code))
        role = result.scalars().first()
        if not role:
            role = Role(code=code, name=name, description=desc, is_system=is_sys)
            db.add(role)
        roles[code] = role
    await db.flush()

    # 4. 关联
    print("\n[4/5] 关联角色权限和菜单...")
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
    await db.flush()

    # 5. 管理员
    print("\n[5/5] 创建管理员...")
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalars().first()
    if not user:
        user = User(
            username="admin",
            password_hash=_hash_password_sync("admin123"),
            display_name="管理员",
        )
        db.add(user)
    user.roles = [roles["admin"]]
    await db.flush()

    await db.commit()
    print("\n=== 种子数据初始化完成 ===")
    print("""
默认账号: admin / admin123
角色: 管理员(admin)
""")


async def main():
    # DDL 操作底层仍是同步的，通过 run_sync 在异步引擎上执行
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
