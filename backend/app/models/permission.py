from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import role_permissions
from app.models.base import TimestampMixin


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(200))

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
