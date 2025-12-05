"""
Планировщик задач для отправки уведомлений
"""
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.config import settings
from app.bot import send_daily_notifications

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Планировщик уведомлений с использованием APScheduler"""
    
    def __init__(self):
        # Настройка планировщика
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.default_timezone
        )
        
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Настройка периодических задач"""
        
        # Ежедневные уведомления в 07:00 по Екатеринбургу
        notification_time = settings.notification_time.split(':')
        hour = int(notification_time[0])
        minute = int(notification_time[1]) if len(notification_time) > 1 else 0
        
        self.scheduler.add_job(
            send_daily_notifications,
            CronTrigger(hour=hour, minute=minute, timezone=settings.default_timezone),
            id='daily_notifications',
            name='Ежедневные уведомления о повторениях',
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily notifications at {hour:02d}:{minute:02d} {settings.default_timezone}")
        
        # Дополнительная проверка просроченных уведомлений каждые 4 часа
        self.scheduler.add_job(
            self._check_overdue_notifications,
            CronTrigger(hour='*/4', timezone=settings.default_timezone),
            id='check_overdue',
            name='Проверка просроченных уведомлений',
            replace_existing=True
        )
        
        # Очистка старых данных раз в неделю в 02:00 понедельника
        self.scheduler.add_job(
            self._cleanup_old_data,
            CronTrigger(day_of_week=0, hour=2, minute=0, timezone=settings.default_timezone),
            id='weekly_cleanup',
            name='Еженедельная очистка данных',
            replace_existing=True
        )
    
    async def start(self):
        """Запустить планировщик"""
        try:
            self.scheduler.start()
            logger.info("Notification scheduler started successfully")
            
            # Показываем информацию о запланированных задачах
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                logger.info(f"Scheduled job: {job.name} - {job.next_run_time}")
                
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Остановить планировщик"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Notification scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def _check_overdue_notifications(self):
        """Проверка и отправка просроченных уведомлений"""
        logger.info("Checking for overdue notifications...")
        
        # Эту функцию можно расширить для отправки напоминаний
        # о просроченных повторениях
        pass
    
    async def _cleanup_old_data(self):
        """Очистка старых данных"""
        logger.info("Starting weekly data cleanup...")
        
        # Здесь можно добавить логику очистки:
        # - Удаление старых завершенных повторений (старше 3 месяцев)
        # - Очистка логов
        # - Архивирование данных
        pass
    
    def add_user_specific_job(self, user_id: int, job_func, trigger, job_id: str):
        """
        Добавить персональную задачу для пользователя
        
        Args:
            user_id: ID пользователя
            job_func: Функция для выполнения
            trigger: Триггер APScheduler
            job_id: Уникальный ID задачи
        """
        try:
            self.scheduler.add_job(
                job_func,
                trigger,
                id=f"user_{user_id}_{job_id}",
                replace_existing=True
            )
            logger.info(f"Added custom job for user {user_id}: {job_id}")
        except Exception as e:
            logger.error(f"Failed to add job for user {user_id}: {e}")
    
    def remove_user_jobs(self, user_id: int):
        """
        Удалить все задачи пользователя
        
        Args:
            user_id: ID пользователя
        """
        try:
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                if job.id.startswith(f"user_{user_id}_"):
                    self.scheduler.remove_job(job.id)
                    logger.info(f"Removed job {job.id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to remove jobs for user {user_id}: {e}")
    
    def get_scheduler_status(self) -> dict:
        """
        Получить статус планировщика
        
        Returns:
            Словарь с информацией о планировщике
        """
        try:
            jobs = self.scheduler.get_jobs()
            return {
                'is_running': self.scheduler.running,
                'jobs_count': len(jobs),
                'jobs': [
                    {
                        'id': job.id,
                        'name': job.name,
                        'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    for job in jobs
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get scheduler status: {e}")
            return {'error': str(e)}


# Глобальный экземпляр планировщика
notification_scheduler = NotificationScheduler()


async def start_scheduler():
    """Запустить планировщик (используется в main.py)"""
    await notification_scheduler.start()


async def stop_scheduler():
    """Остановить планировщик (используется в main.py)"""
    await notification_scheduler.stop()
