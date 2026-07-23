"""菜单 Schema"""

from pydantic import BaseModel


class MenuCreate(BaseModel):
    code: str
    name: str
    icon: str | None = None
    path: str | None = None
    parent_id: int | None = None
    sort_order: int = 0


class MenuUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    path: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
