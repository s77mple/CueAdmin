"""Repository 层 — 数据访问收口，供 Service 调用。

每个实体一个 Repository，只做「查/存」数据访问，不 commit、不抛业务异常。
"""

from app.system.repositories.base import BaseRepository
from app.system.repositories.user import UserRepository
from app.system.repositories.role import RoleRepository
from app.system.repositories.department import DepartmentRepository
from app.system.repositories.menu import MenuRepository
from app.system.repositories.permission import PermissionRepository
from app.system.repositories.post import PostRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "RoleRepository",
    "DepartmentRepository",
    "MenuRepository",
    "PermissionRepository",
    "PostRepository",
]
