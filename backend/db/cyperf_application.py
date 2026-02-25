"""ORM model for Cyperf Applications."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CyperfApplication(Base):
    """Cyperf Application record.

    Represents applications fetched from Cyperf Controller via
    ApplicationResourcesApi.get_resources_apps().

    Attributes:
        id: Unique application ID from Cyperf (VARCHAR(36), primary key)
        name: Application name
        description: Application description
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "cyperf_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<CyperfApplication(id={self.id!r}, name={self.name!r})>"
