"""
Логика интервалов повторений по методу Эббингауза
"""
from datetime import datetime, timedelta, time
from typing import Tuple, Optional
import pytz
from zoneinfo import ZoneInfo


def calculate_next_repetition(
    created_at: datetime,
    current_stage: int,
    timezone_name: str,
    last_success_at: Optional[datetime] = None
) -> Tuple[datetime, int]:
    """
    Вычислить следующее время повторения и стадию на основе метода Эббингауза

    Стадии повторений:
    - 0: Сразу (момент создания)
    - 1: Через 20 минут
    - 2: Сегодня в 20:00
    - 3: Через 1 день в 07:00
    - 4: Через 3 дня в 07:00
    - 5: Через 7 дней в 07:00
    - 6: Через 14 дней в 07:00
    - 7: Через 30 дней в 07:00
    - 8+: Месячная фаза (раз в 30 дней в 07:00)

    Args:
        created_at: Время первого создания материала
        current_stage: Текущая стадия (0-8+)
        timezone_name: Название часового пояса (например, "Asia/Yekaterinburg")
        last_success_at: Время последнего успешного повторения (для месячной фазы)

    Returns:
        Кортеж (next_due_at, next_stage) - время следующего повторения и следующая стадия
    """
    # Получаем часовой пояс
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        # Fallback на pytz если zoneinfo не работает
        tz = pytz.timezone(timezone_name)

    # Локализуем created_at если необходимо
    if created_at.tzinfo is None:
        if isinstance(tz, ZoneInfo):
            created_at = created_at.replace(tzinfo=tz)
        else:
            created_at = tz.localize(created_at)
    else:
        created_at = created_at.astimezone(tz)

    next_stage = current_stage + 1

    # Стадия 0 → 1: Через 20 минут
    if current_stage == 0:
        next_due_at = created_at + timedelta(minutes=20)
        return (next_due_at, 1)

    # Стадия 1 → 2: Сегодня в 20:00
    elif current_stage == 1:
        next_due_at = created_at.replace(hour=20, minute=0, second=0, microsecond=0)
        # Если 20:00 уже прошло, переносим на следующий день
        if next_due_at <= created_at:
            next_due_at = next_due_at + timedelta(days=1)
        return (next_due_at, 2)

    # Стадия 2 → 3: Через 1 день в 07:00
    elif current_stage == 2:
        next_date = created_at.date() + timedelta(days=1)
        next_due_at = datetime.combine(next_date, time(7, 0))
        if isinstance(tz, ZoneInfo):
            next_due_at = next_due_at.replace(tzinfo=tz)
        else:
            next_due_at = tz.localize(next_due_at)
        return (next_due_at, 3)

    # Стадия 3 → 4: Через 3 дня в 07:00
    elif current_stage == 3:
        next_date = created_at.date() + timedelta(days=3)
        next_due_at = datetime.combine(next_date, time(7, 0))
        if isinstance(tz, ZoneInfo):
            next_due_at = next_due_at.replace(tzinfo=tz)
        else:
            next_due_at = tz.localize(next_due_at)
        return (next_due_at, 4)

    # Стадия 4 → 5: Через 7 дней в 07:00
    elif current_stage == 4:
        next_date = created_at.date() + timedelta(days=7)
        next_due_at = datetime.combine(next_date, time(7, 0))
        if isinstance(tz, ZoneInfo):
            next_due_at = next_due_at.replace(tzinfo=tz)
        else:
            next_due_at = tz.localize(next_due_at)
        return (next_due_at, 5)

    # Стадия 5 → 6: Через 14 дней в 07:00
    elif current_stage == 5:
        next_date = created_at.date() + timedelta(days=14)
        next_due_at = datetime.combine(next_date, time(7, 0))
        if isinstance(tz, ZoneInfo):
            next_due_at = next_due_at.replace(tzinfo=tz)
        else:
            next_due_at = tz.localize(next_due_at)
        return (next_due_at, 6)

    # Стадия 6 → 7: Через 30 дней в 07:00
    elif current_stage == 6:
        next_date = created_at.date() + timedelta(days=30)
        next_due_at = datetime.combine(next_date, time(7, 0))
        if isinstance(tz, ZoneInfo):
            next_due_at = next_due_at.replace(tzinfo=tz)
        else:
            next_due_at = tz.localize(next_due_at)
        return (next_due_at, 7)

    # Стадия 7 → 8+: Месячная фаза (раз в 30 дней в 07:00)
    else:  # current_stage >= 7
        # Для месячной фазы используем last_success_at если он предоставлен
        base_date = last_success_at if last_success_at else created_at

        # Локализуем base_date если необходимо
        if base_date.tzinfo is None:
            if isinstance(tz, ZoneInfo):
                base_date = base_date.replace(tzinfo=tz)
            else:
                base_date = tz.localize(base_date)
        else:
            base_date = base_date.astimezone(tz)

        next_date = base_date.date() + timedelta(days=30)
        next_due_at = datetime.combine(next_date, time(7, 0))
        if isinstance(tz, ZoneInfo):
            next_due_at = next_due_at.replace(tzinfo=tz)
        else:
            next_due_at = tz.localize(next_due_at)

        # Стадия остается 8 (не увеличивается бесконечно)
        return (next_due_at, 8)


def calculate_failed_repetition(
    failed_at: datetime,
    current_stage: int,
    timezone_name: str
) -> Tuple[datetime, int]:
    """
    Вычислить следующее время повторения при неудачном повторении

    При неудаче:
    - Стадия откатывается на 1 (но не ниже 0)
    - Следующее повторение переносится на завтра в 07:00

    Args:
        failed_at: Время когда произошла неудача
        current_stage: Текущая стадия
        timezone_name: Название часового пояса

    Returns:
        Кортеж (next_due_at, next_stage)
    """
    # Получаем часовой пояс
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = pytz.timezone(timezone_name)

    # Локализуем failed_at если необходимо
    if failed_at.tzinfo is None:
        if isinstance(tz, ZoneInfo):
            failed_at = failed_at.replace(tzinfo=tz)
        else:
            failed_at = tz.localize(failed_at)
    else:
        failed_at = failed_at.astimezone(tz)

    # Откатываем стадию на 1, но не ниже 0
    new_stage = max(0, current_stage - 1)

    # Следующее повторение - завтра в 07:00
    tomorrow_date = failed_at.date() + timedelta(days=1)
    next_due_at = datetime.combine(tomorrow_date, time(7, 0))

    if isinstance(tz, ZoneInfo):
        next_due_at = next_due_at.replace(tzinfo=tz)
    else:
        next_due_at = tz.localize(next_due_at)

    return (next_due_at, new_stage)


def get_stage_name(stage: int) -> str:
    """
    Получить название стадии

    Args:
        stage: Номер стадии

    Returns:
        Название стадии
    """
    stage_names = {
        0: 'immediate',
        1: 'short_term',
        2: 'evening',
        3: 'day_1',
        4: 'day_3',
        5: 'day_7',
        6: 'day_14',
        7: 'day_30',
        8: 'monthly'
    }

    if stage >= 8:
        return 'monthly'

    return stage_names.get(stage, 'unknown')


def get_stage_description(stage: int) -> str:
    """
    Получить описание стадии

    Args:
        stage: Номер стадии

    Returns:
        Описание стадии
    """
    descriptions = {
        0: 'Сразу',
        1: 'Через 20 минут',
        2: 'Вечером в 20:00',
        3: 'Завтра в 07:00',
        4: 'Через 3 дня в 07:00',
        5: 'Через 7 дней в 07:00',
        6: 'Через 14 дней в 07:00',
        7: 'Через 30 дней в 07:00',
        8: 'Раз в месяц в 07:00'
    }

    if stage >= 8:
        return 'Раз в месяц в 07:00'

    return descriptions.get(stage, 'Неизвестная стадия')


# Оставляем старый класс для обратной совместимости
class EbbinghausScheduler:
    """
    Планировщик повторений по методу Эббингауза (legacy)

    УСТАРЕЛО: Используйте функции calculate_next_repetition() и calculate_failed_repetition()
    вместо этого класса для новой логики на основе стадий.
    """

    # Интервалы повторений согласно кривой забывания
    INTERVALS = {
        'immediate': 0,      # сразу после изучения
        'short_term': 0,     # через 20-30 минут
        'evening': 0,        # вечером того же дня
        'day_1': 1,          # Д+1 день
        'day_3': 3,          # Д+3 дня
        'day_7': 7,          # Д+7 дней
        'day_14': 14,        # Д+14 дней
        'day_30': 30         # Д+30 дней
    }

    def __init__(self, timezone_name: str = None):
        """
        Инициализация планировщика

        Args:
            timezone_name: Название часового пояса (по умолчанию из настроек)
        """
        from app.config import settings
        self.timezone_name = timezone_name or settings.default_timezone
        try:
            self.timezone = ZoneInfo(self.timezone_name)
        except Exception:
            self.timezone = pytz.timezone(self.timezone_name)

    def calculate_success_rate(self, total_repetitions: int, successful_repetitions: int) -> float:
        """
        Рассчитать процент успешности повторений

        Args:
            total_repetitions: Общее количество повторений
            successful_repetitions: Количество успешных повторений

        Returns:
            Процент успешности (0.0 - 1.0)
        """
        if total_repetitions == 0:
            return 0.0

        return successful_repetitions / total_repetitions
