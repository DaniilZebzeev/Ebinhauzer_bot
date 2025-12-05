"""
FastAPI приложение для Telegram-бота по методу Эббингауза
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update

from app.config import settings
from app.database.connection import get_async_session
from app.services.user_service import UserService
from app.services.material_service import MaterialService
from app.services.schedule_service import ScheduleService
from app.services.notification_service import NotificationService
from app.bot import bot_instance
from app.scheduler import start_scheduler, stop_scheduler, notification_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Starting Ebbinghaus Telegram Bot...")
    
    try:
        # Запускаем планировщик уведомлений
        await start_scheduler()
        
        # Инициализируем бота и запускаем polling
        await bot_instance.application.initialize()
        
        # Регистрируем команды бота
        await bot_instance.register_commands()
        
        # Удаляем webhook если был установлен
        await bot_instance.application.bot.delete_webhook()
        logger.info("Webhook deleted, starting polling mode")
        
        # Запускаем polling
        await bot_instance.application.start()
        await bot_instance.application.updater.start_polling()
        logger.info("Bot polling started successfully")
        
        logger.info("Application started successfully!")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    try:
        await stop_scheduler()
        await bot_instance.application.updater.stop()
        await bot_instance.application.stop()
        await bot_instance.application.shutdown()
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Создание FastAPI приложения
app = FastAPI(
    title="Ebbinghaus Learning Bot",
    description="Telegram bot for learning using Ebbinghaus forgetting curve method",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Ebbinghaus Learning Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        # Проверяем состояние планировщика
        scheduler_status = notification_scheduler.get_scheduler_status()
        
        return {
            "status": "healthy",
            "scheduler": scheduler_status,
            "bot_token_configured": bool(settings.bot_token),
            "database_configured": bool(settings.database_url)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@app.post("/webhook")
async def webhook(request: Request):
    """Webhook для получения обновлений от Telegram"""
    try:
        # Получаем JSON данные
        json_data = await request.json()
        
        # Создаем объект Update
        update = Update.de_json(json_data, bot_instance.application.bot)
        
        if update:
            # Обрабатываем обновление
            await bot_instance.application.process_update(update)
            return {"status": "ok"}
        else:
            logger.warning("Received invalid update")
            return {"status": "invalid_update"}
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


@app.get("/api/users/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Получить статистику пользователя"""
    try:
        user_service = UserService(db)
        material_service = MaterialService(db)
        notification_service = NotificationService(db)
        
        # Получаем пользователя
        user = await user_service.get_user_with_stats(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Собираем статистику
        materials_count = await material_service.get_materials_count(user_id)
        notification_stats = await notification_service.get_notification_statistics(user_id)
        
        # Считаем общую статистику
        total_success = sum(stat.successful_repetitions for stat in user.user_statistics)
        total_failed = sum(stat.failed_repetitions for stat in user.user_statistics)
        total_materials = sum(stat.total_materials_added for stat in user.user_statistics)
        
        success_rate = 0
        if total_success + total_failed > 0:
            success_rate = (total_success / (total_success + total_failed)) * 100
        
        return {
            "user_id": user_id,
            "username": user.username,
            "first_name": user.first_name,
            "created_at": user.created_at.isoformat(),
            "is_active": user.is_active,
            "timezone": user.timezone,
            "statistics": {
                "total_materials": total_materials,
                "active_materials": materials_count,
                "successful_repetitions": total_success,
                "failed_repetitions": total_failed,
                "success_rate": round(success_rate, 1),
                "upcoming_repetitions": notification_stats['upcoming_count'],
                "overdue_repetitions": notification_stats['overdue_count'],
                "today_repetitions": notification_stats['today_count']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/users/{user_id}/materials")
async def get_user_materials(
    user_id: int,
    limit: Optional[int] = 10,
    active_only: bool = True,
    db: AsyncSession = Depends(get_async_session)
):
    """Получить материалы пользователя"""
    try:
        material_service = MaterialService(db)
        
        materials = await material_service.get_user_materials(
            user_id=user_id,
            active_only=active_only,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "materials": [
                {
                    "id": material.id,
                    "content": material.content,
                    "created_at": material.created_at.isoformat(),
                    "is_active": material.is_active
                }
                for material in materials
            ],
            "count": len(materials)
        }
        
    except Exception as e:
        logger.error(f"Error getting user materials: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/users/{user_id}/schedule")
async def get_user_schedule(
    user_id: int,
    days_ahead: int = 7,
    include_completed: bool = False,
    db: AsyncSession = Depends(get_async_session)
):
    """Получить расписание пользователя"""
    try:
        schedule_service = ScheduleService(db)
        
        schedule = await schedule_service.get_user_schedule(
            user_id=user_id,
            days_ahead=days_ahead,
            include_completed=include_completed
        )
        
        return {
            "user_id": user_id,
            "schedule": [
                {
                    "id": item.id,
                    "material_id": item.material_id,
                    "material_content": item.material.content if item.material else None,
                    "scheduled_date": item.scheduled_date.isoformat(),
                    "repetition_type": item.repetition_type,
                    "interval_days": item.interval_days,
                    "is_completed": item.is_completed,
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None
                }
                for item in schedule
            ],
            "count": len(schedule)
        }
        
    except Exception as e:
        logger.error(f"Error getting user schedule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Получить статус планировщика"""
    try:
        return notification_scheduler.get_scheduler_status()
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/users/{user_id}/materials/{material_id}/debug-schedule")
async def debug_material_schedule(
    user_id: int,
    material_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Получить детальную информацию о расписании материала для отладки

    Возвращает:
    - Информацию о материале
    - Текущую стадию
    - Следующее запланированное повторение
    - Историю всех повторений
    """
    try:
        schedule_service = ScheduleService(db)

        # Получаем полную информацию о расписании
        schedule_info = await schedule_service.get_material_schedule_with_history(
            user_id, material_id
        )

        if not schedule_info:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Material not found or access denied",
                    "user_id": user_id,
                    "material_id": material_id
                }
            )

        return schedule_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting debug schedule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/test/notification/{user_id}")
async def send_test_notification(
    user_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Отправить тестовое уведомление пользователю"""
    try:
        notification_service = NotificationService(db)

        # Получаем повторения пользователя на сегодня
        users_data = await notification_service.get_users_for_notification()
        user_data = next((data for data in users_data if data['user'].user_id == user_id), None)

        if not user_data:
            raise HTTPException(status_code=404, detail="No repetitions found for user")

        # Отправляем тестовое уведомление
        from app.bot import send_notification_to_user
        from telegram import InlineKeyboardMarkup

        message_text = await notification_service.format_notification_message(
            user_data['user'], user_data['repetitions']
        )

        keyboard_data = await notification_service.create_notification_markup(user_data['repetitions'])
        reply_markup = InlineKeyboardMarkup(keyboard_data) if keyboard_data else None

        await send_notification_to_user(user_id, message_text, reply_markup)

        return {
            "status": "sent",
            "user_id": user_id,
            "repetitions_count": len(user_data['repetitions'])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
