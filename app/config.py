"""
Конфигурация приложения для Telegram-бота по методу Эббингауза
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Telegram Bot
    bot_token: str
    webhook_url: Optional[str] = None
    
    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/ebbinghaus_db"
    
    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    
    # Timezone and notifications
    default_timezone: str = "Asia/Yekaterinburg"
    notification_time: str = "07:00"
    
    # API Keys (опционально для внешних сервисов)
    redis_url: Optional[str] = None
    
    # Security (для продакшна)
    secret_key: Optional[str] = None
    allowed_hosts: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "/app/logs/bot.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()
