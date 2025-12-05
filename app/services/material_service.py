"""
Сервис для работы с учебными материалами
"""
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.database.models import StudyMaterial, User, UserStatistics


class MaterialService:
    """Сервис для управления учебными материалами"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_material(
        self,
        user_id: int,
        content: str
    ) -> StudyMaterial:
        """
        Создать новый учебный материал
        
        Args:
            user_id: ID пользователя
            content: Содержимое материала
            
        Returns:
            Созданный материал
        """
        material = StudyMaterial(
            user_id=user_id,
            content=content.strip(),
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        
        # Обновляем статистику пользователя
        await self._update_user_statistics(user_id, materials_added=1)
        
        return material
    
    async def get_material(self, material_id: int) -> Optional[StudyMaterial]:
        """
        Получить материал по ID
        
        Args:
            material_id: ID материала
            
        Returns:
            Объект материала или None
        """
        stmt = select(StudyMaterial).where(StudyMaterial.id == material_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_materials(
        self,
        user_id: int,
        active_only: bool = True,
        limit: Optional[int] = None
    ) -> List[StudyMaterial]:
        """
        Получить материалы пользователя
        
        Args:
            user_id: ID пользователя
            active_only: Только активные материалы
            limit: Лимит количества материалов
            
        Returns:
            Список материалов
        """
        stmt = select(StudyMaterial).where(StudyMaterial.user_id == user_id)
        
        if active_only:
            stmt = stmt.where(StudyMaterial.is_active == True)
        
        stmt = stmt.order_by(StudyMaterial.created_at.desc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_material_with_schedule(self, material_id: int) -> Optional[StudyMaterial]:
        """
        Получить материал с расписанием повторений
        
        Args:
            material_id: ID материала
            
        Returns:
            Материал с расписанием
        """
        stmt = (
            select(StudyMaterial)
            .options(selectinload(StudyMaterial.repetition_schedules))
            .where(StudyMaterial.id == material_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def deactivate_material(self, material_id: int, user_id: int) -> bool:
        """
        Деактивировать материал
        
        Args:
            material_id: ID материала
            user_id: ID пользователя (для проверки владения)
            
        Returns:
            True если деактивация прошла успешно
        """
        stmt = select(StudyMaterial).where(
            and_(
                StudyMaterial.id == material_id,
                StudyMaterial.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        material = result.scalar_one_or_none()
        
        if not material:
            return False
        
        material.is_active = False
        await self.db.commit()
        return True
    
    async def search_materials(
        self,
        user_id: int,
        search_text: str,
        limit: int = 10
    ) -> List[StudyMaterial]:
        """
        Поиск материалов по тексту
        
        Args:
            user_id: ID пользователя
            search_text: Текст для поиска
            limit: Лимит результатов
            
        Returns:
            Список найденных материалов
        """
        stmt = (
            select(StudyMaterial)
            .where(
                and_(
                    StudyMaterial.user_id == user_id,
                    StudyMaterial.is_active == True,
                    StudyMaterial.content.ilike(f"%{search_text}%")
                )
            )
            .order_by(StudyMaterial.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_materials_count(self, user_id: int, active_only: bool = True) -> int:
        """
        Получить количество материалов пользователя
        
        Args:
            user_id: ID пользователя
            active_only: Только активные материалы
            
        Returns:
            Количество материалов
        """
        stmt = select(func.count(StudyMaterial.id)).where(StudyMaterial.user_id == user_id)
        
        if active_only:
            stmt = stmt.where(StudyMaterial.is_active == True)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _update_user_statistics(
        self,
        user_id: int,
        materials_added: int = 0,
        successful_repetitions: int = 0,
        failed_repetitions: int = 0
    ) -> None:
        """
        Обновить статистику пользователя
        
        Args:
            user_id: ID пользователя
            materials_added: Количество добавленных материалов
            successful_repetitions: Количество успешных повторений
            failed_repetitions: Количество неудачных повторений
        """
        today = date.today()
        
        # Ищем существующую запись статистики на сегодня
        stmt = select(UserStatistics).where(
            and_(
                UserStatistics.user_id == user_id,
                UserStatistics.date == today
            )
        )
        result = await self.db.execute(stmt)
        stats = result.scalar_one_or_none()
        
        if stats is None:
            # Создаем новую запись статистики
            stats = UserStatistics(
                user_id=user_id,
                date=today,
                total_materials_added=materials_added,
                successful_repetitions=successful_repetitions,
                failed_repetitions=failed_repetitions,
                updated_at=datetime.utcnow()
            )
            self.db.add(stats)
        else:
            # Обновляем существующую запись
            stats.total_materials_added += materials_added
            stats.successful_repetitions += successful_repetitions
            stats.failed_repetitions += failed_repetitions
            stats.updated_at = datetime.utcnow()
        
        await self.db.commit()
