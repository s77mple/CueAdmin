"""模型汇总 — 导入此模块即可访问所有模型。

用法：
  from app.models import User, Role, Permission, Menu, Department, Post
  from app.models.associations import user_roles, user_posts, role_permissions, role_menus

Base 类不在这里导出 — 从 app.core.storage 导入。
"""

from app.models.department import Department as Department
from app.models.menu import Menu as Menu
from app.models.permission import Permission as Permission
from app.models.post import Post as Post
from app.models.role import Role as Role
from app.models.user import User as User
