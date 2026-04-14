import uuid as _uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, TypeDecorator, types
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.database import Base


class GUID(TypeDecorator):
    """
    Platform-independent UUID type.
    Stores as TEXT on SQLite, native UUID on PostgreSQL.
    """
    impl = types.String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return _uuid.UUID(str(value))


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[_uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=_uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    # query shape: { "q": str, "types": list[str], "source": str }
    query: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
