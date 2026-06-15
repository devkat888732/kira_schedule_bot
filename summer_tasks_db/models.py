from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class StatusEnum(str, enum.Enum):
    todo = "todo"
    wip = "wip"
    done = "done"
    blocked = "blocked"

class PriorityEnum(str, enum.Enum):
    high = "high"
    mid = "mid"
    low = "low"

class ProjectStatusEnum(str, enum.Enum):
    active = "active"
    completed = "completed"
    archived = "archived"

class BugStatusEnum(str, enum.Enum):
    open = "open"
    fixed = "fixed"

class UpdateStatusEnum(str, enum.Enum):
    open = "open"
    done = "done"

# Связующая таблица для тегов задач
task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    status = Column(Enum(ProjectStatusEnum), default=ProjectStatusEnum.active)
    color = Column(String(20), default="#1D9E75")
    desc = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tasks = relationship("Task", back_populates="project")

class TaskType(Base):
    __tablename__ = "task_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), default="📝")
    color = Column(String(20), default="#1D9E75")
    checklist = Column(JSON, nullable=True)  # шаблон чеклиста
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tasks = relationship("Task", back_populates="type")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.todo)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.mid)
    deadline = Column(String(10), nullable=True)
    notes = Column(Text, nullable=True)
    checklist = Column(JSON, nullable=True)  # пользовательский чеклист
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    type_id = Column(Integer, ForeignKey('task_types.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    project = relationship("Project", back_populates="tasks")
    type = relationship("TaskType", back_populates="tasks")
    tags = relationship("Tag", secondary=task_tags, backref="tasks")

class Bug(Base):
    __tablename__ = "bugs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    desc = Column(Text, nullable=True)
    status = Column(Enum(BugStatusEnum), default=BugStatusEnum.open)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Update(Base):
    __tablename__ = "updates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    desc = Column(Text, nullable=True)
    status = Column(Enum(UpdateStatusEnum), default=UpdateStatusEnum.open)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())