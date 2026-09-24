"""Repository 层 — 数据访问收口，供 Service 调用。"""

from app.repositories.base import BaseRepository
from app.repositories.department import DepartmentRepository
from app.repositories.menu import MenuRepository
from app.repositories.permission import PermissionRepository
from app.repositories.post import PostRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "RoleRepository",
    "DepartmentRepository",
    "MenuRepository",
    "PermissionRepository",
    "PostRepository",
]
