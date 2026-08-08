"""模型汇总 — 导入此模块即可访问所有模型。

用法：
  from app.models import User, Role, Permission, Menu, Department
  from app.models.associations import user_roles, role_permissions, role_menus

Base 类不在这里导出 — 从 app.core.database 导入。
"""

from app.models.base import TimestampMixin
from app.models.associations import user_roles, role_permissions, role_menus
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.menu import Menu
from app.models.department import Department
