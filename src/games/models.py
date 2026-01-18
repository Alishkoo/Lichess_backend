from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    perf_type: Mapped[str] = mapped_column(String(50), nullable=False)
    time_control: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    opponent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    opponent_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    user_color: Mapped[str] = mapped_column(String(10), nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    termination: Mapped[str] = mapped_column(String(50), nullable=False)
    
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    user: Mapped["User"] = relationship("User", back_populates="games")

    __table_args__ = (
        Index("idx_games_user_created", "user_id", "created_at"),
        Index("idx_games_user_perf", "user_id", "perf_type"),
    )
