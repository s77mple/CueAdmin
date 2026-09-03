"""
岗位管理 API — 薄控制器，业务逻辑全部委托给 PostService。

岗位与角色同构（都是挂用户的 M2M 维度），但不参与权限判断，
因此不需要注入 Redis（改岗位不用清任何用户的权限缓存）。
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Security

from app.core.dependencies import SessionDep, get_current_user
from app.system.models import User
from app.core.response import ApiResponse, PageData
from app.system.schemas.post import PostCreate, PostUpdate, PostItem, PostBrief
from app.system.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["岗位管理"])


class PostScope:
    LIST   = "post:list"
    CREATE = "post:create"
    UPDATE = "post:update"
    DELETE = "post:delete"


# GET /posts — 岗位列表

@router.get("", response_model=ApiResponse[PageData[PostItem]], summary="岗位列表")
async def list_posts(
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PostScope.LIST])],
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数，最大 100")] = 100,
) -> ApiResponse[PageData[PostItem]]:
    result = await PostService(session).list_posts(page, page_size)
    return ApiResponse.ok(data=result)


# GET /posts/{post_id} — 岗位详情（单查回显）

@router.get("/{post_id}", response_model=ApiResponse[PostItem], summary="岗位详情")
async def get_post(
    post_id: Annotated[int, Path(description="岗位 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PostScope.LIST])],
) -> ApiResponse[PostItem]:
    post = await PostService(session).get_post(post_id)
    return ApiResponse.ok(data=post)


# POST /posts — 创建岗位

@router.post("", response_model=ApiResponse[PostBrief], status_code=201, summary="创建岗位")
async def create_post(
    body: PostCreate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PostScope.CREATE])],
) -> ApiResponse[PostBrief]:
    post = await PostService(session).create_post(body)
    return ApiResponse.ok(data=post, message="创建成功")


# PUT /posts/{post_id} — 全量更新

@router.put("/{post_id}", response_model=ApiResponse[PostBrief], summary="全量更新岗位")
async def update_post(
    post_id: Annotated[int, Path(description="岗位 ID")],
    body: PostUpdate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PostScope.UPDATE])],
) -> ApiResponse[PostBrief]:
    post = await PostService(session).update_post(post_id, body)
    return ApiResponse.ok(data=post, message="更新成功")


# DELETE /posts/{post_id} — 删除岗位

@router.delete("/{post_id}", response_model=ApiResponse, summary="删除岗位")
async def delete_post(
    post_id: Annotated[int, Path(description="岗位 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PostScope.DELETE])],
) -> ApiResponse:
    message = await PostService(session).delete_post(post_id)
    return ApiResponse.ok(message=message)
