from sqlalchemy import String, BigInteger, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departments.id", ondelete="SET NULL"), default=None
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)

    children = relationship(
        "Department", back_populates="parent", foreign_keys=[parent_id],
        order_by="Department.sort_order",
    )
    parent = relationship(
        "Department", back_populates="children", remote_side="Department.id",
    )
    users = relationship("User", back_populates="department")
