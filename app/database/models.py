import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    original_title: Mapped[str] = mapped_column(String(512), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(16), nullable=True)

    translation: Mapped[str] = mapped_column(Text, nullable=True)
    title_ru: Mapped[str] = mapped_column(String(512), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    trend_reason: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    viral_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mentions_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)

    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} score={self.viral_score} source={self.source}>"
