"""
Утилиты для работы с часовыми поясами
"""
from datetime import datetime, time
from typing import Optional
import pytz

from app.config import settings


def get_user_timezone(timezone_name: Optional[str] = None) -> pytz.BaseTzInfo:
    """
    Получить часовой пояс пользователя
    
    Args:
        timezone_name: Название часового пояса
        
    Returns:
        Объект часового пояса
    """
    tz_name = timezone_name or settings.default_timezone
    try:
        return pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        # Возвращаем часовой пояс по умолчанию при ошибке
        return pytz.timezone(settings.default_timezone)


def localize_datetime(dt: datetime, timezone_name: Optional[str] = None) -> datetime:
    """
    Локализовать datetime в часовой пояс пользователя
    
    Args:
        dt: Datetime объект
        timezone_name: Название часового пояса
        
    Returns:
        Локализованный datetime
    """
    tz = get_user_timezone(timezone_name)
    
    if dt.tzinfo is None:
        return tz.localize(dt)
    else:
        return dt.astimezone(tz)


def get_today_in_timezone(timezone_name: Optional[str] = None) -> datetime:
    """
    Получить сегодняшнюю дату в часовом поясе пользователя
    
    Args:
        timezone_name: Название часового пояса
        
    Returns:
        Сегодняшняя дата в часовом поясе пользователя
    """
    tz = get_user_timezone(timezone_name)
    return datetime.now(tz)


def get_notification_time_today(
    notification_time: time,
    timezone_name: Optional[str] = None
) -> datetime:
    """
    Получить время уведомления на сегодня в часовом поясе пользователя
    
    Args:
        notification_time: Время уведомления
        timezone_name: Название часового пояса
        
    Returns:
        Datetime уведомления на сегодня
    """
    tz = get_user_timezone(timezone_name)
    today = datetime.now(tz).date()
    
    return tz.localize(datetime.combine(today, notification_time))


def is_valid_timezone(timezone_name: str) -> bool:
    """
    Проверить, валиден ли часовой пояс
    
    Args:
        timezone_name: Название часового пояса
        
    Returns:
        True если часовой пояс валиден
    """
    try:
        pytz.timezone(timezone_name)
        return True
    except pytz.UnknownTimeZoneError:
        return False
