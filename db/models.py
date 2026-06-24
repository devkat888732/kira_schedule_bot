from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    BigInteger, String, Text, DateTime, Date,
    ForeignKey, Enum, Boolean, Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.base import Base


class MemberRole(str, PyEnum):
    OWNER = "owner"
    MEMBER = "member"
    OBSERVER = "observer"


class TaskStatus(str, PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class TaskPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ReminderType(str, PyEnum):
    NONE = "none"
    ONE_HOUR = "1h"
    ONE_DAY = "24h"
    BOTH = "both"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="user", cascade="all, delete"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
    memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete"
    )
    lists: Mapped[list["TaskList"]] = relationship(
        back_populates="project", cascade="all, delete"
    )
    invites: Mapped[list["ProjectInvite"]] = relationship(
        back_populates="project", cascade="all, delete"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        # FIX Perf-1: индексы для горячих запросов
        Index("ix_project_members_user_id", "user_id"),
        Index("ix_project_members_project_id", "project_id"),
    )

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole), default=MemberRole.MEMBER)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class ProjectInvite(Base):
    __tablename__ = "project_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole), default=MemberRole.MEMBER)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped["Project"] = relationship(back_populates="invites")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class TaskList(Base):
    __tablename__ = "task_lists"
    __table_args__ = (
        # FIX Perf-1: индекс для get_project_tasks
        Index("ix_task_lists_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))

    project: Mapped["Project"] = relationship(back_populates="lists")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="task_list", cascade="all, delete"
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        # FIX Perf-1: индексы для горячих запросов и scheduler
        Index("ix_tasks_assignee_id", "assignee_id"),
        Index("ix_tasks_list_id", "list_id"),
        Index("ix_tasks_due_date_status", "due_date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.NORMAL)
    reminder: Mapped[ReminderType] = mapped_column(Enum(ReminderType), default=ReminderType.NONE)
    list_id: Mapped[int] = mapped_column(ForeignKey("task_lists.id"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task_list: Mapped["TaskList"] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])


NEXT_STATUS = {
    TaskStatus.TODO: TaskStatus.IN_PROGRESS,
    TaskStatus.IN_PROGRESS: TaskStatus.REVIEW,
    TaskStatus.REVIEW: TaskStatus.DONE,
    TaskStatus.DONE: TaskStatus.TODO,
}
