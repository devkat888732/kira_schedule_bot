import asyncio
import logging
from datetime import timedelta
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import ErrorEvent
from config import settings
from handlers import start, projects, tasks, my_tasks, search, filters, export, invite, cancel
from middlewares.auth import AuthMiddleware
from scheduler.notifications import setup_scheduler
from db.base import engine, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Снижаем уровень aiogram чтобы не логировать тела сообщений (токены в deep link)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # FIX P9/S11: TTL для FSM состояний + не логируем токены
    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        state_ttl=timedelta(hours=24),
        data_ttl=timedelta(hours=24),
    )
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # ── Глобальный error handler (Rel-1) ──────────────────────────────────────
    @dp.error()
    async def error_handler(event: ErrorEvent) -> None:
        logger.exception("Unhandled error: %s", event.exception)
        try:
            if event.update.message:
                await event.update.message.answer(
                    "⚠️ Произошла ошибка. Попробуй снова или нажми /start."
                )
            elif event.update.callback_query:
                await event.update.callback_query.answer(
                    "⚠️ Ошибка. Попробуй снова.", show_alert=True
                )
        except Exception:
            pass

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # /cancel — глобально, РАНЬШЕ всех FSM-роутеров
    dp.include_router(cancel.router)

    # FIX P9: invite.router ПЕРВЫМ — перехватывает CommandStart(deep_link=True)
    # до того как start.router обработает CommandStart()
    dp.include_router(invite.router)
    dp.include_router(start.router)
    dp.include_router(projects.router)
    dp.include_router(tasks.router)
    dp.include_router(my_tasks.router)
    dp.include_router(search.router)
    dp.include_router(filters.router)
    dp.include_router(export.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Bot started")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
