from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.utils import markdown as md
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from db.base import async_session
from db.models import Task, TaskStatus, User, ReminderType
import logging

logger = logging.getLogger(__name__)


# ── Безопасная отправка (FIX Rel-5) ──────────────────────────────────────────

async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    """Различает recoverable и unrecoverable ошибки Telegram."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except TelegramForbiddenError:
        pass  # пользователь заблокировал бота — нормально
    except TelegramRetryAfter as e:
        import asyncio
        await asyncio.sleep(e.retry_after)
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as ex:
            logger.error("Retry failed for %s: %s", chat_id, ex)
    except Exception as e:
        logger.error("Failed to notify %s: %s", chat_id, e)


# ── Напоминания по дедлайну (FIX Perf-4) ─────────────────────────────────────

async def notify_upcoming(bot: Bot, hours_before: int) -> None:
    """FIX Perf-4: фильтрация по дате в SQL, не в Python."""
    reminder_types = (
        [ReminderType.ONE_HOUR, ReminderType.BOTH] if hours_before == 1
        else [ReminderType.ONE_DAY, ReminderType.BOTH]
    )
    label = "через 1 час ⚡" if hours_before == 1 else "завтра 📅"
    now = datetime.utcnow()
    # FIX Perf-4: вычисляем целевую дату в SQL — не грузим все задачи в память
    target_date = (now + timedelta(hours=hours_before)).date()

    async with async_session() as session:
        result = await session.execute(
            select(Task, User)
            .join(User, Task.assignee_id == User.id)
            .where(Task.due_date == target_date)          # фильтр в БД
            .where(Task.status != TaskStatus.DONE)
            .where(Task.reminder.in_(reminder_types))
        )
        rows = result.all()

    for task, assignee in rows:
        title = md.html.quote(task.title)
        await _safe_send(
            bot, assignee.telegram_id,
            f"⏰ <b>Напоминание</b> — дедлайн {label}\n\n"
            f"📌 <b>{title}</b>\n"
            f"📅 {task.due_date.strftime('%d.%m.%Y')}\n"
            f"👉 /task_{task.id}"
        )


# ── Просроченные задачи ───────────────────────────────────────────────────────

async def notify_overdue(bot: Bot) -> None:
    today = date.today()
    async with async_session() as session:
        result = await session.execute(
            select(Task, User)
            .join(User, Task.assignee_id == User.id)
            .where(Task.due_date < today)
            .where(Task.status != TaskStatus.DONE)
        )
        rows = result.all()

    for task, assignee in rows:
        days_overdue = (today - task.due_date).days
        title = md.html.quote(task.title)
        await _safe_send(
            bot, assignee.telegram_id,
            f"🔴 <b>Просрочено на {days_overdue} дн.</b>\n\n"
            f"📌 <b>{title}</b>\n"
            f"📅 Дедлайн был: {task.due_date.strftime('%d.%m.%Y')}\n"
            f"👉 /task_{task.id}"
        )


# ── Еженедельный дайджест (FIX Perf-3: агрегирующие запросы) ─────────────────

async def weekly_digest(bot: Bot) -> None:
    """FIX Perf-3: один запрос на все данные вместо N+1."""
    today = date.today()
    week_ago = datetime.utcnow() - timedelta(days=7)

    async with async_session() as session:
        # Один запрос: все пользователи у которых есть задачи
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()

        # FIX Perf-3: агрегируем статистику одним запросом
        done_counts = dict(await session.execute(
            select(Task.assignee_id, func.count(Task.id))
            .where(Task.status == TaskStatus.DONE)
            .where(Task.completed_at >= week_ago)  # FIX: по дате завершения
            .group_by(Task.assignee_id)
        ))
        active_tasks_result = await session.execute(
            select(Task)
            .where(Task.status != TaskStatus.DONE)
            .where(Task.assignee_id.is_not(None))
        )
        all_active = active_tasks_result.scalars().all()

    # Группируем активные задачи по assignee в Python (данные уже в памяти)
    from collections import defaultdict
    active_by_user: dict = defaultdict(list)
    for t in all_active:
        active_by_user[t.assignee_id].append(t)

    for user in users:
        done_count = done_counts.get(user.id, 0)
        active = active_by_user.get(user.id, [])
        overdue = [t for t in active if t.due_date and t.due_date < today]
        on_track = [t for t in active if t not in overdue]

        if not done_count and not active:
            continue

        lines = [
            f"📊 <b>Еженедельный дайджест</b>",
            f"<i>{today.strftime('%d.%m.%Y')}</i>\n",
            f"✅ <b>Выполнено за неделю:</b> {done_count}",
        ]
        if on_track:
            lines.append(f"\n🔄 <b>Активных:</b> {len(on_track)}")
            for t in on_track[:5]:
                due = f" — до {t.due_date.strftime('%d.%m')}" if t.due_date else ""
                lines.append(f"  · {md.html.quote(t.title)}{due}")
            if len(on_track) > 5:
                lines.append(f"  <i>…и ещё {len(on_track) - 5}</i>")

        if overdue:
            lines.append(f"\n🔴 <b>Просрочено:</b> {len(overdue)}")
            for t in overdue[:3]:
                days = (today - t.due_date).days
                lines.append(f"  · {md.html.quote(t.title)} (−{days} дн.)")

        await _safe_send(bot, user.telegram_id, "\n".join(lines))


# ── Регистрация джобов (FIX Rel-2) ───────────────────────────────────────────

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    common = dict(
        replace_existing=True,
        misfire_grace_time=300,  # FIX Rel-2: 5 мин grace period
        coalesce=True,           # не запускать пропущенные итерации
        max_instances=1,         # не запускать параллельно
    )

    scheduler.add_job(
        notify_upcoming, CronTrigger(minute="*/10"),
        kwargs={"bot": bot, "hours_before": 1},
        id="notify_1h", **common,
    )
    scheduler.add_job(
        notify_upcoming, CronTrigger(minute="*/30"),
        kwargs={"bot": bot, "hours_before": 24},
        id="notify_24h", **common,
    )
    scheduler.add_job(
        notify_overdue, CronTrigger(hour=9, minute=0),
        kwargs={"bot": bot},
        id="notify_overdue", **common,
    )
    scheduler.add_job(
        weekly_digest, CronTrigger(day_of_week="mon", hour=8, minute=0),
        kwargs={"bot": bot},
        id="weekly_digest", **common,
    )
    return scheduler
