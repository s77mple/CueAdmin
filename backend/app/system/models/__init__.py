"""模型汇总 — 导入此模块即可访问所有模型。

用法：
  from app.system.models import User, Role, Permission, Menu, Department
  from app.system.models.associations import user_roles, role_permissions, role_menus

Base 类不在这里导出 — 从 app.core.storage 导入。
"""

from app.core.storage import TimestampMixin
from app.system.models.associations import user_roles, role_permissions, role_menus
from app.system.models.user import User
from app.system.models.role import Role
from app.system.models.permission import Permission
from app.system.models.menu import Menu
from app.system.models.department import Department
