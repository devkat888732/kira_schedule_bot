import secrets
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import (
    User, Project, ProjectMember, ProjectInvite,
    TaskList, Task, TaskStatus, TaskPriority,
    MemberRole, ReminderType,
)


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self, telegram_id: int, username: str | None, full_name: str
    ) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        else:
            # FIX: обновляем username/full_name если изменились
            if user.username != username or user.full_name != full_name:
                user.username = username
                user.full_name = full_name
                await self.session.commit()
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username.lstrip("@").lower())
        )
        return result.scalar_one_or_none()


class ProjectRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_projects(self, user_id: int) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return result.scalars().all()

    async def get_owned_projects(self, user_id: int) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .where(ProjectMember.role == MemberRole.OWNER)
        )
        return result.scalars().all()

    async def create_project(self, name: str, owner_id: int) -> Project:
        project = Project(name=name, owner_id=owner_id)
        self.session.add(project)
        await self.session.flush()
        member = ProjectMember(project_id=project.id, user_id=owner_id, role=MemberRole.OWNER)
        self.session.add(member)
        default_list = TaskList(name="Основные задачи", project_id=project.id)
        self.session.add(default_list)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: int) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()


class TaskRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self,
        title: str,
        description: str | None,
        project_id: int,
        creator_id: int,
        assignee_id: int | None = None,
        priority: str = "normal",
        due_date=None,
        reminder: str = "none",
    ) -> Task:
        # FIX Rel-4: scalar_one_or_none + явная проверка
        list_result = await self.session.execute(
            select(TaskList).where(TaskList.project_id == project_id).limit(1)
        )
        task_list = list_result.scalar_one_or_none()
        if not task_list:
            raise ValueError(f"Project {project_id} has no task lists")

        task = Task(
            title=title,
            description=description,
            list_id=task_list.id,
            creator_id=creator_id,
            assignee_id=assignee_id or creator_id,
            priority=TaskPriority(priority),
            due_date=due_date,
            reminder=ReminderType(reminder),
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_task(self, task_id: int) -> Task | None:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_user_tasks(self, user_id: int) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.assignee_id == user_id)
            .order_by(Task.status, Task.due_date.asc().nullslast())
        )
        return result.scalars().all()

    async def get_project_tasks(self, project_id: int) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .join(TaskList, Task.list_id == TaskList.id)
            .where(TaskList.project_id == project_id)
            .order_by(Task.status, Task.priority.desc())
        )
        return result.scalars().all()

    async def get_filtered(self, project_id: int, filters: dict) -> list[Task]:
        conditions = [TaskList.project_id == project_id]
        if "status" in filters:
            conditions.append(Task.status == TaskStatus(filters["status"]))
        if "priority" in filters:
            conditions.append(Task.priority == TaskPriority(filters["priority"]))
        if "assignee_id" in filters:
            conditions.append(Task.assignee_id == filters["assignee_id"])
        result = await self.session.execute(
            select(Task)
            .join(TaskList, Task.list_id == TaskList.id)
            .where(and_(*conditions))
            .order_by(Task.priority.desc(), Task.due_date.asc().nullslast())
        )
        return result.scalars().all()

    async def delete_task(self, task_id: int) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        await self.session.delete(task)
        await self.session.commit()
        return True


class MemberRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_members(self, project_id: int) -> list[tuple]:
        result = await self.session.execute(
            select(ProjectMember, User)
            .join(User, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.role)
        )
        return result.all()

    async def add_by_username(
        self, project_id: int, username: str, role: MemberRole
    ) -> tuple[User | None, str]:
        username = username.lstrip("@").lower()
        user_result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None, (
                f"Пользователь @{username} не найден.\n"
                "Он должен сначала написать боту /start."
            )
        existing = await self.session.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .where(ProjectMember.user_id == user.id)
        )
        if existing.scalar_one_or_none():
            return None, f"@{username} уже участник проекта."
        member = ProjectMember(project_id=project_id, user_id=user.id, role=role)
        self.session.add(member)
        await self.session.commit()
        return user, ""


class InviteRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_invite(
        self, project_id: int, creator_id: int, role: MemberRole = MemberRole.MEMBER
    ) -> ProjectInvite:
        # FIX S7: инвалидируем предыдущие активные инвайты для этого проекта и роли
        await self.session.execute(
            update(ProjectInvite)
            .where(ProjectInvite.project_id == project_id)
            .where(ProjectInvite.created_by == creator_id)
            .where(ProjectInvite.is_used == False)
            .values(is_used=True)
        )
        token = secrets.token_urlsafe(16)
        invite = ProjectInvite(
            project_id=project_id,
            token=token,
            role=role,
            created_by=creator_id,
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )
        self.session.add(invite)
        await self.session.commit()
        await self.session.refresh(invite)
        return invite

    async def accept_invite(
        self, token: str, user_id: int
    ) -> tuple[Project | None, str]:
        result = await self.session.execute(
            select(ProjectInvite)
            .where(ProjectInvite.token == token)
            .where(ProjectInvite.is_used == False)
            .where(ProjectInvite.expires_at > datetime.utcnow())
        )
        invite = result.scalar_one_or_none()
        if not invite:
            return None, "Ссылка недействительна или истекла."
        existing = await self.session.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == invite.project_id)
            .where(ProjectMember.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            return None, "Ты уже участник этого проекта."
        member = ProjectMember(
            project_id=invite.project_id,
            user_id=user_id,
            role=invite.role,
        )
        invite.is_used = True
        self.session.add(member)
        await self.session.commit()
        project_result = await self.session.execute(
            select(Project).where(Project.id == invite.project_id)
        )
        return project_result.scalar_one(), ""
