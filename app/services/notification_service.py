"""
Сервис для отправки уведомлений
"""
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, RepetitionSchedule
from app.services.schedule_service import ScheduleService
from app.services.user_service import UserService


class NotificationService:
    """Сервис для управления уведомлениями"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.schedule_service = ScheduleService(db_session)
        self.user_service = UserService(db_session)
    
    async def get_users_for_notification(self, target_date: Optional[date] = None) -> List[dict]:
        """
        Получить пользователей, которым нужно отправить уведомления

        Args:
            target_date: Целевая дата (по умолчанию сегодня)

        Returns:
            Список словарей с данными пользователей и их повторениями
        """
        if target_date is None:
            target_date = date.today()

        # Автоматически отмечаем просроченные внутридневные повторения как пропущенные
        await self.schedule_service.auto_complete_expired_intraday_repetitions()

        # Получаем все повторения на сегодня
        due_repetitions = await self.schedule_service.get_due_repetitions(target_date=target_date)
        
        # Группируем по пользователям
        users_data = {}
        for repetition in due_repetitions:
            user_id = repetition.user_id
            
            if user_id not in users_data:
                # Получаем данные пользователя
                user = await self.user_service.get_user(user_id)
                if not user or not user.is_active:
                    continue
                
                users_data[user_id] = {
                    'user': user,
                    'repetitions': []
                }
            
            users_data[user_id]['repetitions'].append(repetition)
        
        return list(users_data.values())
    
    async def format_notification_message(
        self,
        user: User,
        repetitions: List[RepetitionSchedule]
    ) -> str:
        """
        Сформировать текст уведомления для пользователя
        
        Args:
            user: Объект пользователя
            repetitions: Список повторений
            
        Returns:
            Текст уведомления
        """
        if not repetitions:
            return ""
        
        user_name = user.first_name or "Друг"
        total_count = len(repetitions)
        
        # Группируем по типам повторений для красивого отображения
        type_names = {
            'immediate': '📝 Сразу',
            'short_term': '⏰ Через 20-30 мин',
            'evening': '🌆 Вечером',
            'day_1': '📅 День +1',
            'day_3': '📆 День +3',
            'day_7': '🗓️ Неделя',
            'day_14': '📋 2 недели',
            'day_30': '📊 Месяц'
        }
        
        message_parts = [
            f"Доброе утро, {user_name}! ☀️",
            "",
            f"⏰ Время повторить материал! У тебя {total_count} повторений на сегодня:",
            ""
        ]
        
        # Добавляем каждое повторение
        for i, repetition in enumerate(repetitions, 1):
            type_display = type_names.get(repetition.repetition_type, repetition.repetition_type)
            content_preview = self._truncate_content(repetition.material.content, 50)
            
            message_parts.append(f"{i}. {type_display}")
            message_parts.append(f"   📖 {content_preview}")
            message_parts.append("")
        
        message_parts.extend([
            "🎯 Нажми кнопки ниже, чтобы отметить результат повторения.",
            "",
            "💡 Помни: регулярное повторение - ключ к долговременной памяти!"
        ])
        
        return "\n".join(message_parts)
    
    async def create_notification_markup(
        self,
        repetitions: List[RepetitionSchedule]
    ) -> List[List[dict]]:
        """
        Создать inline клавиатуру для уведомления
        
        Args:
            repetitions: Список повторений
            
        Returns:
            Разметка inline клавиатуры
        """
        if not repetitions:
            return []
        
        # Если повторений много, делаем общие кнопки
        if len(repetitions) > 3:
            return [
                [
                    {"text": "Повторил всё ✅", "callback_data": f"complete_all_success"},
                    {"text": "Не повторил ❌", "callback_data": f"complete_all_failed"}
                ]
            ]
        
        # Для малого количества - кнопки для каждого повторения
        keyboard = []
        for repetition in repetitions:
            content_short = self._truncate_content(repetition.material.content, 20)
            keyboard.append([
                {
                    "text": f"✅ {content_short}",
                    "callback_data": f"complete_{repetition.id}_success"
                },
                {
                    "text": f"❌ {content_short}",
                    "callback_data": f"complete_{repetition.id}_failed"
                }
            ])
        
        return keyboard
    
    async def get_notification_statistics(self, user_id: int) -> dict:
        """
        Получить статистику уведомлений пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        # Получаем расписание на неделю вперед
        upcoming_schedule = await self.schedule_service.get_user_schedule(user_id, days_ahead=7)
        
        # Считаем просроченные
        overdue = await self.schedule_service.get_overdue_repetitions(user_id)
        
        # Сегодняшние повторения
        today_repetitions = await self.schedule_service.get_due_repetitions(
            user_id=user_id,
            target_date=date.today()
        )
        
        return {
            'upcoming_count': len(upcoming_schedule),
            'overdue_count': len(overdue),
            'today_count': len(today_repetitions),
            'total_pending': len([r for r in upcoming_schedule if not r.is_completed])
        }
    
    def _truncate_content(self, content: str, max_length: int) -> str:
        """
        Обрезать содержимое до указанной длины
        
        Args:
            content: Исходный текст
            max_length: Максимальная длина
            
        Returns:
            Обрезанный текст
        """
        if len(content) <= max_length:
            return content
        
        return content[:max_length-3] + "..."
    
    async def mark_notification_sent(self, user_id: int, repetition_ids: List[int]) -> None:
        """
        Отметить, что уведомление было отправлено
        (Можно расширить для трекинга отправленных уведомлений)
        
        Args:
            user_id: ID пользователя
            repetition_ids: Список ID повторений
        """
        # В базовой версии просто логируем
        # В будущем можно добавить таблицу sent_notifications
        pass
