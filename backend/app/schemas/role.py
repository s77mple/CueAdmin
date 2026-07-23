"""角色 Schema"""

from pydantic import BaseModel


class RoleCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    permission_codes: list[str] = []   # 权限 code 列表（如 "user:list"），非 ID
    menu_ids: list[int] = []           # 菜单 ID 列表


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_codes: list[str] | None = None
    menu_ids: list[int] | None = None
