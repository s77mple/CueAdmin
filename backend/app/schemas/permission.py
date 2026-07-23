"""权限 Schema"""

from pydantic import BaseModel


class PermissionCreate(BaseModel):
    code: str
    name: str
    resource: str
    action: str
    description: str | None = None


class PermissionUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    resource: str | None = None
    action: str | None = None
    description: str | None = None
