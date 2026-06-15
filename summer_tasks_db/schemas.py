from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models import StatusEnum, PriorityEnum, ProjectStatusEnum, BugStatusEnum, UpdateStatusEnum

# --- Tag ---
class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class TagOut(TagBase):
    id: int
    created_at: datetime

# --- Project ---
class ProjectBase(BaseModel):
    name: str
    status: ProjectStatusEnum = ProjectStatusEnum.active
    color: str = "#1D9E75"
    desc: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ProjectStatusEnum] = None
    color: Optional[str] = None
    desc: Optional[str] = None

class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

# --- TaskType ---
class ChecklistItem(BaseModel):
    id: int
    text: str
    done: bool = False

class TaskTypeBase(BaseModel):
    name: str
    icon: str = "📝"
    color: str = "#1D9E75"
    checklist: Optional[List[ChecklistItem]] = None

class TaskTypeCreate(TaskTypeBase):
    pass

class TaskTypeUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    checklist: Optional[List[ChecklistItem]] = None

class TaskTypeOut(TaskTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

# --- Task ---
class TaskChecklistItem(BaseModel):
    id: int
    text: str
    done: bool = False

class TaskBase(BaseModel):
    title: str
    status: StatusEnum = StatusEnum.todo
    priority: PriorityEnum = PriorityEnum.mid
    deadline: Optional[str] = None
    notes: Optional[str] = None
    checklist: Optional[List[TaskChecklistItem]] = None
    project_id: Optional[int] = None
    type_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[StatusEnum] = None
    priority: Optional[PriorityEnum] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None
    checklist: Optional[List[TaskChecklistItem]] = None
    project_id: Optional[int] = None
    type_id: Optional[int] = None

class TaskOut(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagOut] = []

# --- Bug ---
class BugBase(BaseModel):
    title: str
    desc: Optional[str] = None
    status: BugStatusEnum = BugStatusEnum.open

class BugCreate(BugBase):
    pass

class BugUpdate(BaseModel):
    title: Optional[str] = None
    desc: Optional[str] = None
    status: Optional[BugStatusEnum] = None

class BugOut(BugBase):
    id: int
    created_at: datetime
    updated_at: datetime

# --- Update ---
class UpdateBase(BaseModel):
    title: str
    desc: Optional[str] = None
    status: UpdateStatusEnum = UpdateStatusEnum.open

class UpdateCreate(UpdateBase):
    pass

class UpdateUpdate(BaseModel):
    title: Optional[str] = None
    desc: Optional[str] = None
    status: Optional[UpdateStatusEnum] = None

class UpdateOut(UpdateBase):
    id: int
    created_at: datetime
    updated_at: datetime