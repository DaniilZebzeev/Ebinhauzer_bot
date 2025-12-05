"""
Сервис для работы с расписанием повторений
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, func
from sqlalchemy.orm import selectinload
import logging

from app.database.models import RepetitionSchedule, RepetitionResult, StudyMaterial, User
from app.utils.ebbinghaus import (
    calculate_next_repetition,
    calculate_failed_repetition,
    get_stage_name
)
from app.services.material_service import MaterialService
from app.config import settings

logger = logging.getLogger(__name__)


class ScheduleService:
    """Сервис для управления расписанием повторений"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.material_service = MaterialService(db_session)

    async def create_initial_repetitions(
        self,
        material_id: int,
        user_id: int,
        material_created_at: datetime,
        user_timezone: str = None
    ) -> List[RepetitionSchedule]:
        """
        Создать начальные повторения для нового материала (только на сегодня)

        Создаются только первые 3 повторения:
        - Сразу (immediate, stage 0)
        - Через 20 минут (short_term, stage 1)
        - Вечером в 20:00 (evening, stage 2)

        Args:
            material_id: ID материала
            user_id: ID пользователя
            material_created_at: Время создания материала
            user_timezone: Часовой пояс пользователя

        Returns:
            Список созданных записей расписания
        """
        timezone = user_timezone or settings.default_timezone

        # Удаляем все незавершенные повторения для этого материала (защита от дублей)
        await self._delete_incomplete_repetitions(user_id, material_id)

        # Создаем три начальных повторения на сегодня
        schedule_items = []

        # Стадия 0: Сразу (immediate)
        next_due_at_0, next_stage_0 = calculate_next_repetition(
            material_created_at, 0, timezone
        )

        immediate = RepetitionSchedule(
            material_id=material_id,
            user_id=user_id,
            scheduled_date=material_created_at.date(),
            repetition_type='immediate',
            interval_days=0,
            current_stage=0,
            scheduled_datetime=material_created_at,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        schedule_items.append(immediate)

        # Стадия 1: Через 20 минут
        short_term = RepetitionSchedule(
            material_id=material_id,
            user_id=user_id,
            scheduled_date=next_due_at_0.date(),
            repetition_type='short_term',
            interval_days=0,
            current_stage=1,
            scheduled_datetime=next_due_at_0,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        schedule_items.append(short_term)

        # Стадия 2: Вечером в 20:00
        next_due_at_1, next_stage_1 = calculate_next_repetition(
            material_created_at, 1, timezone
        )

        evening = RepetitionSchedule(
            material_id=material_id,
            user_id=user_id,
            scheduled_date=next_due_at_1.date(),
            repetition_type='evening',
            interval_days=0,
            current_stage=2,
            scheduled_datetime=next_due_at_1,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        schedule_items.append(evening)

        # Добавляем в БД
        for item in schedule_items:
            self.db.add(item)

        await self.db.commit()

        # Обновляем объекты после коммита
        for item in schedule_items:
            await self.db.refresh(item)

        logger.info(f"Created {len(schedule_items)} initial repetitions for material {material_id}")

        return schedule_items

    async def create_full_schedule(
        self,
        material_id: int,
        user_id: int,
        start_datetime: Optional[datetime] = None
    ) -> List[RepetitionSchedule]:
        """
        Создать полное расписание повторений для материала

        Обертка для обратной совместимости. Создает только начальные повторения.

        Args:
            material_id: ID материала
            user_id: ID пользователя
            start_datetime: Время начала (по умолчанию сейчас)

        Returns:
            Список созданных записей расписания
        """
        if start_datetime is None:
            start_datetime = datetime.utcnow()

        # Получаем материал
        material = await self.material_service.get_material(material_id)
        if not material:
            raise ValueError(f"Material with id {material_id} not found")

        # Получаем пользователя для таймзоны
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        timezone = user.timezone if user else settings.default_timezone

        return await self.create_initial_repetitions(
            material_id, user_id, start_datetime, timezone
        )

    async def _delete_incomplete_repetitions(self, user_id: int, material_id: int):
        """
        Удалить все незавершенные повторения для материала

        Args:
            user_id: ID пользователя
            material_id: ID материала
        """
        stmt = delete(RepetitionSchedule).where(
            and_(
                RepetitionSchedule.user_id == user_id,
                RepetitionSchedule.material_id == material_id,
                RepetitionSchedule.is_completed == False
            )
        )
        await self.db.execute(stmt)

    async def get_due_repetitions(
        self,
        user_id: Optional[int] = None,
        target_date: Optional[date] = None
    ) -> List[RepetitionSchedule]:
        """
        Получить повторения, которые нужно выполнить

        Защита от дублей: группируем по material_id и берем только одну запись на материал

        Args:
            user_id: ID пользователя (None для всех пользователей)
            target_date: Целевая дата (по умолчанию сегодня)

        Returns:
            Список запланированных повторений БЕЗ дублей
        """
        if target_date is None:
            target_date = date.today()

        # Внутридневные повторения (immediate, short_term, evening) показываем только в день их создания
        # Долгосрочные повторения показываем на target_date и позже
        stmt = (
            select(RepetitionSchedule)
            .options(selectinload(RepetitionSchedule.material))
            .where(
                and_(
                    RepetitionSchedule.is_completed == False,
                    or_(
                        # Внутридневные повторения - только в точную дату
                        and_(
                            RepetitionSchedule.repetition_type.in_(['immediate', 'short_term', 'evening']),
                            RepetitionSchedule.scheduled_date == target_date
                        ),
                        # Долгосрочные повторения - на target_date или раньше
                        and_(
                            RepetitionSchedule.repetition_type.in_(['day_1', 'day_3', 'day_7', 'day_14', 'day_30', 'monthly']),
                            RepetitionSchedule.scheduled_date <= target_date
                        )
                    )
                )
            )
        )

        if user_id:
            stmt = stmt.where(RepetitionSchedule.user_id == user_id)

        stmt = stmt.order_by(
            RepetitionSchedule.scheduled_date,
            RepetitionSchedule.current_stage,
            RepetitionSchedule.created_at
        )

        result = await self.db.execute(stmt)
        all_repetitions = result.scalars().all()

        # Защита от дублей: оставляем только одну запись для каждого material_id
        unique_repetitions = []
        seen_materials = set()

        for rep in all_repetitions:
            if rep.material_id not in seen_materials:
                unique_repetitions.append(rep)
                seen_materials.add(rep.material_id)
            else:
                logger.warning(f"Duplicate repetition found for material {rep.material_id}, skipping")

        return unique_repetitions

    async def complete_repetition(
        self,
        schedule_id: int,
        user_id: int,
        was_successful: bool
    ) -> bool:
        """
        Отметить повторение как выполненное

        Args:
            schedule_id: ID записи расписания
            user_id: ID пользователя
            was_successful: Успешность повторения

        Returns:
            True если операция прошла успешно
        """
        # Получаем запись расписания
        stmt = (
            select(RepetitionSchedule)
            .options(selectinload(RepetitionSchedule.material))
            .where(
                and_(
                    RepetitionSchedule.id == schedule_id,
                    RepetitionSchedule.user_id == user_id,
                    RepetitionSchedule.is_completed == False
                )
            )
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found or already completed")
            return False

        # Отмечаем как выполненное
        schedule.is_completed = True
        schedule.completed_at = datetime.utcnow()

        # Создаем запись результата
        result_record = RepetitionResult(
            schedule_id=schedule_id,
            user_id=user_id,
            material_id=schedule.material_id,
            was_successful=was_successful,
            completed_at=datetime.utcnow()
        )
        self.db.add(result_record)

        # Обновляем статистику
        if was_successful:
            await self.material_service._update_user_statistics(user_id, successful_repetitions=1)
        else:
            await self.material_service._update_user_statistics(user_id, failed_repetitions=1)

        await self.db.commit()

        # Создаем следующее повторение если нужно
        if was_successful:
            await self._create_next_repetition_on_success(schedule)
        else:
            await self._create_next_repetition_on_failure(schedule)

        return True

    async def mark_failed(
        self,
        user_id: int,
        material_id: int,
        failed_at: Optional[datetime] = None
    ) -> bool:
        """
        Отметить повторение как неудачное (кнопка "Не повторил")

        При неудаче:
        - Стадия откатывается на 1 (но не ниже 0)
        - Следующее повторение переносится на завтра в 07:00

        Args:
            user_id: ID пользователя
            material_id: ID материала
            failed_at: Время неудачи (по умолчанию сейчас)

        Returns:
            True если операция прошла успешно
        """
        if failed_at is None:
            failed_at = datetime.utcnow()

        # Получаем материал
        material = await self.material_service.get_material(material_id)
        if not material:
            logger.error(f"Material {material_id} not found")
            return False

        # Получаем пользователя для таймзоны
        stmt_user = select(User).where(User.user_id == user_id)
        result_user = await self.db.execute(stmt_user)
        user = result_user.scalar_one_or_none()
        timezone = user.timezone if user else settings.default_timezone

        # Вычисляем новую стадию и время
        next_due_at, new_stage = calculate_failed_repetition(
            failed_at, material.current_stage, timezone
        )

        # Удаляем все незавершенные повторения
        await self._delete_incomplete_repetitions(user_id, material_id)

        # Создаем новое повторение на завтра
        new_schedule = RepetitionSchedule(
            material_id=material_id,
            user_id=user_id,
            scheduled_date=next_due_at.date(),
            repetition_type=get_stage_name(new_stage),
            interval_days=0,
            current_stage=new_stage,
            scheduled_datetime=next_due_at,
            is_completed=False,
            created_at=datetime.utcnow()
        )

        self.db.add(new_schedule)

        # Обновляем стадию материала
        material.current_stage = new_stage

        # Обновляем статистику
        await self.material_service._update_user_statistics(user_id, failed_repetitions=1)

        await self.db.commit()

        logger.info(f"Material {material_id} failed: stage {material.current_stage} → {new_stage}, next: {next_due_at}")

        return True

    async def _create_next_repetition_on_success(
        self,
        current_schedule: RepetitionSchedule
    ) -> Optional[RepetitionSchedule]:
        """
        Создать следующее повторение после успешного выполнения

        Args:
            current_schedule: Текущая запись расписания

        Returns:
            Новая запись расписания или None
        """
        # Получаем материал
        material = await self.material_service.get_material(current_schedule.material_id)
        if not material:
            logger.error(f"Material {current_schedule.material_id} not found")
            return None

        # Получаем пользователя для таймзоны
        stmt_user = select(User).where(User.user_id == current_schedule.user_id)
        result_user = await self.db.execute(stmt_user)
        user = result_user.scalar_one_or_none()
        timezone = user.timezone if user else settings.default_timezone

        # Обновляем стадию материала
        new_stage = current_schedule.current_stage + 1

        # Обновляем время последнего успешного повторения
        material.last_success_at = datetime.utcnow()
        material.current_stage = new_stage

        # Вычисляем следующее время повторения
        next_due_at, next_stage = calculate_next_repetition(
            material.created_at,
            current_schedule.current_stage,
            timezone,
            material.last_success_at
        )

        # Определяем тип повторения
        next_type = get_stage_name(next_stage)

        # Удаляем все незавершенные повторения (защита от дублей)
        await self._delete_incomplete_repetitions(current_schedule.user_id, current_schedule.material_id)

        # Создаем новую запись расписания
        next_schedule = RepetitionSchedule(
            material_id=current_schedule.material_id,
            user_id=current_schedule.user_id,
            scheduled_date=next_due_at.date(),
            repetition_type=next_type,
            interval_days=0,  # Будет рассчитано по стадии
            current_stage=next_stage,
            scheduled_datetime=next_due_at,
            is_completed=False,
            created_at=datetime.utcnow()
        )

        self.db.add(next_schedule)
        await self.db.commit()
        await self.db.refresh(next_schedule)

        logger.info(f"Created next repetition for material {current_schedule.material_id}: stage {next_stage}, date {next_due_at}")

        return next_schedule

    async def _create_next_repetition_on_failure(
        self,
        current_schedule: RepetitionSchedule
    ) -> Optional[RepetitionSchedule]:
        """
        Создать следующее повторение после неудачного выполнения

        Откатываем стадию на 1 и переносим на завтра в 07:00

        Args:
            current_schedule: Текущая запись расписания

        Returns:
            Новая запись расписания или None
        """
        return await self.mark_failed(
            current_schedule.user_id,
            current_schedule.material_id,
            current_schedule.completed_at
        )

    async def get_user_schedule(
        self,
        user_id: int,
        days_ahead: int = 7,
        include_completed: bool = False
    ) -> List[RepetitionSchedule]:
        """
        Получить расписание пользователя на несколько дней вперед

        Args:
            user_id: ID пользователя
            days_ahead: Количество дней вперед
            include_completed: Включать выполненные повторения

        Returns:
            Список записей расписания
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)

        stmt = (
            select(RepetitionSchedule)
            .options(selectinload(RepetitionSchedule.material))
            .where(
                and_(
                    RepetitionSchedule.user_id == user_id,
                    RepetitionSchedule.scheduled_date >= start_date,
                    RepetitionSchedule.scheduled_date <= end_date
                )
            )
        )

        if not include_completed:
            stmt = stmt.where(RepetitionSchedule.is_completed == False)

        stmt = stmt.order_by(RepetitionSchedule.scheduled_date, RepetitionSchedule.current_stage)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_material_schedule(self, material_id: int) -> List[RepetitionSchedule]:
        """
        Получить расписание для конкретного материала

        Args:
            material_id: ID материала

        Returns:
            Список записей расписания
        """
        stmt = (
            select(RepetitionSchedule)
            .where(RepetitionSchedule.material_id == material_id)
            .order_by(RepetitionSchedule.scheduled_date, RepetitionSchedule.current_stage)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_material_schedule_with_history(
        self,
        user_id: int,
        material_id: int
    ) -> dict:
        """
        Получить полную информацию о расписании материала с историей

        Используется для debug-эндпоинта

        Args:
            user_id: ID пользователя
            material_id: ID материала

        Returns:
            Словарь с информацией о материале и его расписании
        """
        # Получаем материал
        material = await self.material_service.get_material(material_id)
        if not material:
            return None

        # Проверяем владельца
        if material.user_id != user_id:
            return None

        # Получаем все записи расписания
        all_schedules = await self.get_material_schedule(material_id)

        # Получаем следующее запланированное повторение
        next_schedule = None
        for schedule in all_schedules:
            if not schedule.is_completed:
                next_schedule = schedule
                break

        # Получаем историю выполненных повторений
        history = []
        for schedule in all_schedules:
            if schedule.is_completed:
                # Получаем результат
                stmt = select(RepetitionResult).where(RepetitionResult.schedule_id == schedule.id)
                result = await self.db.execute(stmt)
                repetition_result = result.scalar_one_or_none()

                history.append({
                    'stage': schedule.current_stage,
                    'repetition_type': schedule.repetition_type,
                    'planned_at': schedule.scheduled_datetime.isoformat() if schedule.scheduled_datetime else None,
                    'done_at': schedule.completed_at.isoformat() if schedule.completed_at else None,
                    'result': 'success' if (repetition_result and repetition_result.was_successful) else 'failed'
                })

        return {
            'user_id': user_id,
            'material_id': material_id,
            'material_text': material.content,
            'created_at': material.created_at.isoformat() if material.created_at else None,
            'current_stage': material.current_stage,
            'next_due_at': next_schedule.scheduled_datetime.isoformat() if next_schedule and next_schedule.scheduled_datetime else None,
            'next_repetition_type': next_schedule.repetition_type if next_schedule else None,
            'timezone': settings.default_timezone,
            'history': history
        }

    async def get_overdue_repetitions(self, user_id: Optional[int] = None) -> List[RepetitionSchedule]:
        """
        Получить просроченные повторения

        Args:
            user_id: ID пользователя (None для всех)

        Returns:
            Список просроченных повторений
        """
        yesterday = date.today() - timedelta(days=1)

        # Только долгосрочные повторения могут быть просроченными
        stmt = (
            select(RepetitionSchedule)
            .options(selectinload(RepetitionSchedule.material))
            .where(
                and_(
                    RepetitionSchedule.scheduled_date <= yesterday,
                    RepetitionSchedule.is_completed == False,
                    RepetitionSchedule.repetition_type.in_(['day_1', 'day_3', 'day_7', 'day_14', 'day_30', 'monthly'])
                )
            )
        )

        if user_id:
            stmt = stmt.where(RepetitionSchedule.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def auto_complete_expired_intraday_repetitions(self) -> int:
        """
        Автоматически отмечать как пропущенные внутридневные повторения
        из прошлых дней (immediate, short_term, evening)

        Returns:
            Количество отмеченных как пропущенные повторений
        """
        # Находим незавершенные внутридневные повторения из прошлых дней
        stmt = (
            select(RepetitionSchedule)
            .where(
                and_(
                    RepetitionSchedule.scheduled_date < date.today(),
                    RepetitionSchedule.is_completed == False,
                    RepetitionSchedule.repetition_type.in_(['immediate', 'short_term', 'evening'])
                )
            )
        )

        result = await self.db.execute(stmt)
        expired_repetitions = result.scalars().all()

        count = 0
        for repetition in expired_repetitions:
            # Отмечаем как выполненное с неуспешным результатом
            repetition.is_completed = True
            repetition.completed_at = datetime.utcnow()

            # Создаем запись результата как неуспешного
            result_record = RepetitionResult(
                schedule_id=repetition.id,
                user_id=repetition.user_id,
                material_id=repetition.material_id,
                was_successful=False,
                completed_at=datetime.utcnow()
            )
            self.db.add(result_record)

            # Обновляем статистику пропущенных повторений
            await self.material_service._update_user_statistics(
                repetition.user_id,
                failed_repetitions=1
            )

            count += 1

        if count > 0:
            await self.db.commit()
            logger.info(f"Auto-completed {count} expired intraday repetitions")

        return count
