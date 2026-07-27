"""菜单 Schema"""

from pydantic import BaseModel, Field


class MenuCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    icon: str | None = Field(None, max_length=50)
    path: str | None = Field(None, max_length=100)
    parent_id: int | None = None
    sort_order: int = 0


class MenuUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    path: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class MenuItem(BaseModel):
    id: int
    code: str
    name: str
    icon: str | None = None
    path: str | None = None
    parent_id: int | None = None
    sort_order: int


class MenuListResponse(BaseModel):
    items: list[MenuItem]
    total: int


class MenuBrief(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
from app.schemas.response import ApiResponse


class MenuListApiResponse(ApiResponse[MenuListResponse]):
    pass


class MenuBriefResponse(ApiResponse[MenuBrief]):
    pass
