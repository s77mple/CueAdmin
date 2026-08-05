"""菜单 Schema"""

from pydantic import BaseModel, Field


class MenuCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    icon: str | None = Field(None, max_length=50)
    path: str | None = Field(None, max_length=100)
    component: str | None = Field(None, max_length=200)
    parent_id: int | None = None
    sort_order: int = 0


class MenuUpdate(BaseModel):
    """全量更新（PUT）—— 所有字段必传，可空字段传 null"""
    name: str = Field(..., min_length=1, max_length=50, description="菜单名称")
    icon: str | None = Field(..., max_length=50, description="图标，无则传 null")
    path: str | None = Field(..., max_length=100, description="路由路径，无则传 null")
    component: str | None = Field(..., max_length=200, description="组件路径，无则传 null")
    parent_id: int | None = Field(..., description="父菜单 ID，顶级菜单传 null")
    sort_order: int = Field(..., description="排序号")


class MenuPatch(BaseModel):
    """部分更新（PATCH）—— 仅传需要修改的字段"""
    name: str | None = Field(None, min_length=1, max_length=50)
    icon: str | None = Field(None, max_length=50)
    path: str | None = Field(None, max_length=100)
    component: str | None = Field(None, max_length=200)
    parent_id: int | None = None
    sort_order: int | None = None


class MenuItem(BaseModel):
    id: int
    code: str
    name: str
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    parent_id: int | None = None
    sort_order: int


class MenuListResponse(BaseModel):
    items: list[MenuItem]
    total: int


class MenuBrief(BaseModel):
    id: int
    code: str
    name: str
    parent_id: int | None = None

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
from app.schemas.response import ApiResponse


class MenuListApiResponse(ApiResponse[MenuListResponse]):
    pass


class MenuBriefResponse(ApiResponse[MenuBrief]):
    pass
