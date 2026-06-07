from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tutor_profile: Mapped["TutorProfile | None"] = relationship(back_populates="user", uselist=False)
    searches: Mapped[list["StudentSearch"]] = relationship(back_populates="user")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="student",
        foreign_keys="Application.student_id",
    )


class TutorProfile(Base):
    __tablename__ = "tutor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    place_of_study: Mapped[str] = mapped_column(String(255), nullable=False)
    price_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price_max: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="tutor_profile")
    applications: Mapped[list["Application"]] = relationship(back_populates="tutor")


class StudentSearch(Base):
    __tablename__ = "student_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    exam_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(String(512), nullable=False)
    current_level: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="searches")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutor_profiles.id"), nullable=False)
    exam_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(String(512), nullable=False)
    current_level: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_text: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="new", server_default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped["User"] = relationship(back_populates="applications", foreign_keys=[student_id])
    tutor: Mapped["TutorProfile"] = relationship(back_populates="applications")
