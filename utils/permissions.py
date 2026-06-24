from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import ProjectMember, MemberRole

ROLE_WEIGHT = {
    MemberRole.OBSERVER: 0,
    MemberRole.MEMBER: 1,
    MemberRole.OWNER: 2,
}


async def get_role(
    session: AsyncSession, user_id: int, project_id: int
) -> MemberRole | None:
    result = await session.execute(
        select(ProjectMember)
        .where(ProjectMember.user_id == user_id)
        .where(ProjectMember.project_id == project_id)
    )
    membership = result.scalar_one_or_none()
    return membership.role if membership else None


async def check_permission(
    session: AsyncSession,
    user_id: int,
    project_id: int,
    required: MemberRole,
) -> bool:
    role = await get_role(session, user_id, project_id)
    if role is None:
        return False
    return ROLE_WEIGHT[role] >= ROLE_WEIGHT[required]
