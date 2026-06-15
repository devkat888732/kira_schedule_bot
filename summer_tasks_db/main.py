from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from dotenv import load_dotenv
import os

from database import get_db, Base, engine
import models, schemas

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SAS Tasks API", docs_url="/api/docs", redoc_url=None)

# CORS
allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin, "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== TAGS ==========
@app.get("/api/tags", response_model=List[schemas.TagOut])
def get_tags(db: Session = Depends(get_db)):
    return db.query(models.Tag).order_by(models.Tag.name).all()

@app.post("/api/tags", response_model=schemas.TagOut, status_code=201)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Tag).filter(models.Tag.name == tag.name).first()
    if existing:
        return existing
    db_tag = models.Tag(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag

# ========== PROJECTS ==========
@app.get("/api/projects", response_model=List[schemas.ProjectOut])
def get_projects(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Project)
    if status:
        query = query.filter(models.Project.status == status)
    return query.order_by(models.Project.created_at.desc()).all()

@app.post("/api/projects", response_model=schemas.ProjectOut, status_code=201)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.patch("/api/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: int, project: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in project.model_dump(exclude_unset=True).items():
        setattr(db_project, field, value)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(db_project)
    db.commit()

@app.get("/api/projects/{project_id}/tasks", response_model=List[schemas.TaskOut])
def get_project_tasks(project_id: int, db: Session = Depends(get_db)):
    tasks = db.query(models.Task).filter(models.Task.project_id == project_id).all()
    return tasks

# ========== TASK TYPES ==========
@app.get("/api/types", response_model=List[schemas.TaskTypeOut])
def get_types(db: Session = Depends(get_db)):
    return db.query(models.TaskType).order_by(models.TaskType.name).all()

@app.post("/api/types", response_model=schemas.TaskTypeOut, status_code=201)
def create_type(task_type: schemas.TaskTypeCreate, db: Session = Depends(get_db)):
    db_type = models.TaskType(**task_type.model_dump())
    db.add(db_type)
    db.commit()
    db.refresh(db_type)
    return db_type

@app.patch("/api/types/{type_id}", response_model=schemas.TaskTypeOut)
def update_type(type_id: int, task_type: schemas.TaskTypeUpdate, db: Session = Depends(get_db)):
    db_type = db.query(models.TaskType).filter(models.TaskType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Task type not found")
    for field, value in task_type.model_dump(exclude_unset=True).items():
        setattr(db_type, field, value)
    db.commit()
    db.refresh(db_type)
    return db_type

@app.delete("/api/types/{type_id}", status_code=204)
def delete_type(type_id: int, db: Session = Depends(get_db)):
    db_type = db.query(models.TaskType).filter(models.TaskType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Task type not found")
    db.delete(db_type)
    db.commit()

# ========== TASKS ==========
@app.get("/api/tasks", response_model=List[schemas.TaskOut])
def get_tasks(
    status:   Optional[str] = None,
    priority: Optional[str] = None,
    project_id: Optional[int] = None,
    type_id:   Optional[int] = None,
    tag:       Optional[str] = None,
    q:         Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Task)
    if status and status != "all":
        query = query.filter(models.Task.status == status)
    if priority and priority != "all":
        query = query.filter(models.Task.priority == priority)
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if type_id:
        query = query.filter(models.Task.type_id == type_id)
    if tag:
        query = query.join(models.Task.tags).filter(models.Tag.name == tag)
    if q:
        query = query.filter(
            models.Task.title.ilike(f"%{q}%") |
            models.Task.notes.ilike(f"%{q}%")
        )
    return query.order_by(models.Task.created_at.desc()).all()

@app.post("/api/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.patch("/api/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in task.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()

@app.post("/api/tasks/{task_id}/tags", response_model=schemas.TaskOut)
def add_tag_to_task(task_id: int, tag: schemas.TagCreate, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_tag = db.query(models.Tag).filter(models.Tag.name == tag.name).first()
    if not db_tag:
        db_tag = models.Tag(name=tag.name)
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
    if db_tag not in db_task.tags:
        db_task.tags.append(db_tag)
        db.commit()
        db.refresh(db_task)
    return db_task

@app.delete("/api/tasks/{task_id}/tags/{tag_id}", status_code=204)
def remove_tag_from_task(task_id: int, tag_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if db_tag in db_task.tags:
        db_task.tags.remove(db_tag)
        db.commit()

# ========== BUGS ==========
@app.get("/api/bugs", response_model=List[schemas.BugOut])
def get_bugs(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Bug)
    if status:
        query = query.filter(models.Bug.status == status)
    return query.order_by(models.Bug.created_at.desc()).all()

@app.post("/api/bugs", response_model=schemas.BugOut, status_code=201)
def create_bug(bug: schemas.BugCreate, db: Session = Depends(get_db)):
    db_bug = models.Bug(**bug.model_dump())
    db.add(db_bug)
    db.commit()
    db.refresh(db_bug)
    return db_bug

@app.patch("/api/bugs/{bug_id}", response_model=schemas.BugOut)
def update_bug(bug_id: int, bug: schemas.BugUpdate, db: Session = Depends(get_db)):
    db_bug = db.query(models.Bug).filter(models.Bug.id == bug_id).first()
    if not db_bug:
        raise HTTPException(status_code=404, detail="Bug not found")
    for field, value in bug.model_dump(exclude_unset=True).items():
        setattr(db_bug, field, value)
    db.commit()
    db.refresh(db_bug)
    return db_bug

@app.delete("/api/bugs/{bug_id}", status_code=204)
def delete_bug(bug_id: int, db: Session = Depends(get_db)):
    db_bug = db.query(models.Bug).filter(models.Bug.id == bug_id).first()
    if not db_bug:
        raise HTTPException(status_code=404, detail="Bug not found")
    db.delete(db_bug)
    db.commit()

# ========== UPDATES ==========
@app.get("/api/updates", response_model=List[schemas.UpdateOut])
def get_updates(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Update)
    if status:
        query = query.filter(models.Update.status == status)
    return query.order_by(models.Update.created_at.desc()).all()

@app.post("/api/updates", response_model=schemas.UpdateOut, status_code=201)
def create_update(update: schemas.UpdateCreate, db: Session = Depends(get_db)):
    db_update = models.Update(**update.model_dump())
    db.add(db_update)
    db.commit()
    db.refresh(db_update)
    return db_update

@app.patch("/api/updates/{update_id}", response_model=schemas.UpdateOut)
def update_update(update_id: int, update: schemas.UpdateUpdate, db: Session = Depends(get_db)):
    db_update = db.query(models.Update).filter(models.Update.id == update_id).first()
    if not db_update:
        raise HTTPException(status_code=404, detail="Update not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(db_update, field, value)
    db.commit()
    db.refresh(db_update)
    return db_update

@app.delete("/api/updates/{update_id}", status_code=204)
def delete_update(update_id: int, db: Session = Depends(get_db)):
    db_update = db.query(models.Update).filter(models.Update.id == update_id).first()
    if not db_update:
        raise HTTPException(status_code=404, detail="Update not found")
    db.delete(db_update)
    db.commit()

# ========== STATS ==========
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(models.Task).count()
    todo = db.query(models.Task).filter(models.Task.status == "todo").count()
    wip = db.query(models.Task).filter(models.Task.status == "wip").count()
    done = db.query(models.Task).filter(models.Task.status == "done").count()
    blocked = db.query(models.Task).filter(models.Task.status == "blocked").count()
    high = db.query(models.Task).filter(models.Task.priority == "high").count()
    mid = db.query(models.Task).filter(models.Task.priority == "mid").count()
    low = db.query(models.Task).filter(models.Task.priority == "low").count()
    projects_total = db.query(models.Project).count()
    projects_active = db.query(models.Project).filter(models.Project.status == "active").count()
    bugs_total = db.query(models.Bug).count()
    updates_total = db.query(models.Update).count()
    return dict(
        total=total, todo=todo, wip=wip, done=done, blocked=blocked,
        high=high, mid=mid, low=low,
        projects_total=projects_total, projects_active=projects_active,
        bugs_total=bugs_total, updates_total=updates_total
    )

# static files (фронт)
import os
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")