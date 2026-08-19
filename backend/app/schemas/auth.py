"""认证相关 Schema — 登录/登出的请求和响应数据结构。

Schema 层的作用：
  - 定义 API 接受/返回什么字段、类型、校验规则
  - Pydantic 自动校验 + 自动生成 OpenAPI 文档
  - 不涉及数据库操作（那是 Model 的职责）

登录流程的数据形状：
  请求 → LoginRequest { username, password }
  响应 → ApiResponse<LoginResponse> {
           data: { access_token, user, permissions, roles }
         }

注意：登录响应不含 menus —— 动态路由/菜单统一走 GET /api/v1/routes（me.py）。
"""

from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.role import RoleBrief
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """登录请求 — 前端登录表单提交的数据。"""
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=1, max_length=128, description="密码")]
    client: Annotated[str | None, Field(max_length=50, description="客户端标识（预留，暂时不用）")] = None


class LoginResponse(BaseModel):
    """登录响应 — 前端拿到后分发到各处。

    access_token → localStorage（后续请求自动带在 Authorization header）
    user        → pinia user store（显示头像、用户名等）
    permissions → pinia permission store（v-perms 指令判断按钮显隐）
    roles       → pinia role store

    不含 menus：动态路由/菜单由 GET /api/v1/routes 提供（me.py），登录不再重复下发。
    """
    access_token: str
    user: UserRead
    permissions: list[str]
    roles: Annotated[list[RoleBrief], Field(default_factory=list)]

    model_config = {"from_attributes": True}
