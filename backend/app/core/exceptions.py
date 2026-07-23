"""自定义异常类。统一 HTTP 异常的类型和中文错误信息。"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str | int):
        names = {"User": "用户", "Role": "角色", "Permission": "权限", "Menu": "菜单"}
        label = names.get(resource, resource)
        super().__init__(
            detail=f"{label}不存在: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ForbiddenException(AppException):
    def __init__(self, required_permission: str):
        super().__init__(
            detail=f"权限不足，需要: {required_permission}",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "未授权"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ValidationException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ConflictException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)
