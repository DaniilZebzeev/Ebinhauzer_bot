"""
Сервис для работы с пользователями
"""
from datetime import datetime, time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import User, UserStatistics
from app.utils.timezone_utils import is_valid_timezone


class UserService:
    """Сервис для управления пользователями"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> User:
        """
        Получить пользователя или создать нового
        
        Args:
            user_id: Telegram ID пользователя
            username: Username пользователя
            first_name: Имя пользователя
            
        Returns:
            Объект пользователя
        """
        # Проверяем, существует ли пользователь
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            # Создаем нового пользователя
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                created_at=datetime.utcnow(),
                is_active=True
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        else:
            # Обновляем данные существующего пользователя
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            await self.db.commit()
        
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Получить пользователя по ID
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Объект пользователя или None
        """
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user_settings(
        self,
        user_id: int,
        timezone: Optional[str] = None,
        notification_time: Optional[time] = None
    ) -> bool:
        """
        Обновить настройки пользователя
        
        Args:
            user_id: Telegram ID пользователя
            timezone: Часовой пояс
            notification_time: Время уведомлений
            
        Returns:
            True если обновление прошло успешно
        """
        user = await self.get_user(user_id)
        if not user:
            return False
        
        # Валидация часового пояса
        if timezone and not is_valid_timezone(timezone):
            return False
        
        # Обновляем настройки
        if timezone:
            user.timezone = timezone
        if notification_time:
            user.notification_time = notification_time
        
        await self.db.commit()
        return True
    
    async def deactivate_user(self, user_id: int) -> bool:
        """
        Деактивировать пользователя
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            True если деактивация прошла успешно
        """
        user = await self.get_user(user_id)
        if not user:
            return False
        
        user.is_active = False
        await self.db.commit()
        return True
    
    async def activate_user(self, user_id: int) -> bool:
        """
        Активировать пользователя
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            True если активация прошла успешно
        """
        user = await self.get_user(user_id)
        if not user:
            return False
        
        user.is_active = True
        await self.db.commit()
        return True
    
    async def get_user_with_stats(self, user_id: int) -> Optional[User]:
        """
        Получить пользователя со статистикой
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Объект пользователя со статистикой
        """
        stmt = (
            select(User)
            .options(selectinload(User.user_statistics))
            .where(User.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_users(self) -> list[User]:
        """
        Получить всех активных пользователей
        
        Returns:
            Список активных пользователей
        """
        stmt = select(User).where(User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().all()
