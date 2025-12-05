"""
Тесты для сервисов
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

from app.services.material_service import MaterialService
from app.services.schedule_service import ScheduleService
from app.services.notification_service import NotificationService
from app.services.user_service import UserService


class TestMaterialService:
    """Тесты для MaterialService"""
    
    @pytest.fixture
    def service(self):
        """Фикстура для создания MaterialService"""
        mock_db = AsyncMock()
        return MaterialService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_material(self, service):
        """Тест создания материала"""
        service.db.add = MagicMock()
        service.db.commit = AsyncMock()
        service.db.refresh = AsyncMock()
        service._update_user_statistics = AsyncMock()
        
        result = await service.create_material(123, "Test content")
        
        assert result.user_id == 123
        assert result.content == "Test content"
        assert result.is_active == True
        service.db.add.assert_called_once()
        service.db.commit.assert_called_once()
        service.db.refresh.assert_called_once()
        service._update_user_statistics.assert_called_once_with(123, materials_added=1)
    
    @pytest.mark.asyncio
    async def test_get_materials_count(self, service):
        """Тест получения количества материалов"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        service.db.execute = AsyncMock(return_value=mock_result)
        
        count = await service.get_materials_count(123)
        
        assert count == 5
        service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_material_success(self, service):
        """Тест успешной деактивации материала"""
        mock_material = MagicMock()
        mock_material.is_active = True
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_material
        service.db.execute = AsyncMock(return_value=mock_result)
        service.db.commit = AsyncMock()
        
        result = await service.deactivate_material(1, 123)
        
        assert result == True
        assert mock_material.is_active == False
        service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_material_not_found(self, service):
        """Тест деактивации несуществующего материала"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.deactivate_material(1, 123)
        
        assert result == False


class TestScheduleService:
    """Тесты для ScheduleService"""
    
    @pytest.fixture
    def service(self):
        """Фикстура для создания ScheduleService"""
        mock_db = AsyncMock()
        return ScheduleService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_full_schedule(self, service):
        """Тест создания полного расписания"""
        # Мокаем материал
        mock_material = MagicMock()
        service.material_service = AsyncMock()
        service.material_service.get_material = AsyncMock(return_value=mock_material)
        
        # Мокаем планировщик
        with patch('app.services.schedule_service.EbbinghausScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            mock_scheduler.create_schedule.return_value = [
                {
                    'material_id': 1,
                    'user_id': 123,
                    'scheduled_date': date.today(),
                    'repetition_type': 'immediate',
                    'interval_days': 0
                }
            ]
            
            service.db.add = MagicMock()
            service.db.commit = AsyncMock()
            service.db.refresh = AsyncMock()
            
            result = await service.create_full_schedule(1, 123, datetime.utcnow())
            
            assert len(result) == 1
            assert result[0].material_id == 1
            assert result[0].user_id == 123
            service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_repetition_success(self, service):
        """Тест успешного завершения повторения"""
        mock_schedule = MagicMock()
        mock_schedule.material_id = 1
        mock_schedule.is_completed = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_schedule
        service.db.execute = AsyncMock(return_value=mock_result)
        service.db.add = MagicMock()
        service.db.commit = AsyncMock()
        service.material_service = AsyncMock()
        service.material_service._update_user_statistics = AsyncMock()
        service._create_next_repetition = AsyncMock()
        
        result = await service.complete_repetition(1, 123, True)
        
        assert result == True
        assert mock_schedule.is_completed == True
        service.db.add.assert_called_once()
        service.db.commit.assert_called_once()
        service.material_service._update_user_statistics.assert_called_once_with(123, successful_repetitions=1)
    
    @pytest.mark.asyncio
    async def test_complete_repetition_not_found(self, service):
        """Тест завершения несуществующего повторения"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.complete_repetition(1, 123, True)
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_get_due_repetitions(self, service):
        """Тест получения просроченных повторений"""
        mock_repetitions = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_repetitions
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_due_repetitions(123, date.today())
        
        assert result == mock_repetitions
        service.db.execute.assert_called_once()


class TestNotificationService:
    """Тесты для NotificationService"""
    
    @pytest.fixture
    def service(self):
        """Фикстура для создания NotificationService"""
        mock_db = AsyncMock()
        return NotificationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_format_notification_message(self, service):
        """Тест форматирования сообщения уведомления"""
        mock_user = MagicMock()
        mock_user.first_name = "Тест"
        
        mock_material = MagicMock()
        mock_material.content = "Как работает память?"
        
        mock_repetition = MagicMock()
        mock_repetition.repetition_type = "day_1"
        mock_repetition.material = mock_material
        
        repetitions = [mock_repetition]
        
        result = await service.format_notification_message(mock_user, repetitions)
        
        assert "Доброе утро, Тест!" in result
        assert "1 повторений на сегодня" in result
        assert "📅 День +1" in result
        assert "Как работает память?" in result
    
    @pytest.mark.asyncio
    async def test_create_notification_markup_single(self, service):
        """Тест создания клавиатуры для одного повторения"""
        mock_material = MagicMock()
        mock_material.content = "Тест"
        
        mock_repetition = MagicMock()
        mock_repetition.id = 1
        mock_repetition.material = mock_material
        
        result = await service.create_notification_markup([mock_repetition])
        
        assert len(result) == 1  # Одна строка кнопок
        assert len(result[0]) == 2  # Две кнопки в строке (успех/неудача)
        assert result[0][0]['callback_data'] == 'complete_1_success'
        assert result[0][1]['callback_data'] == 'complete_1_failed'
    
    @pytest.mark.asyncio
    async def test_create_notification_markup_many(self, service):
        """Тест создания клавиатуры для многих повторений"""
        mock_material = MagicMock()
        mock_material.content = "Тест"
        
        repetitions = []
        for i in range(5):  # Больше 3 повторений
            mock_repetition = MagicMock()
            mock_repetition.id = i
            mock_repetition.material = mock_material
            repetitions.append(mock_repetition)
        
        result = await service.create_notification_markup(repetitions)
        
        assert len(result) == 1  # Одна строка кнопок
        assert len(result[0]) == 2  # Две кнопки (общие)
        assert result[0][0]['callback_data'] == 'complete_all_success'
        assert result[0][1]['callback_data'] == 'complete_all_failed'
    
    def test_truncate_content_short(self, service):
        """Тест обрезания короткого контента"""
        content = "Короткий текст"
        result = service._truncate_content(content, 50)
        assert result == "Короткий текст"
    
    def test_truncate_content_long(self, service):
        """Тест обрезания длинного контента"""
        content = "Очень длинный текст который нужно обрезать"
        result = service._truncate_content(content, 20)
        assert result == "Очень длинный тек..."
        assert len(result) == 20
    
    @pytest.mark.asyncio
    async def test_get_users_for_notification(self, service):
        """Тест получения пользователей для уведомлений"""
        # Мокаем сервисы
        service.schedule_service = AsyncMock()
        service.user_service = AsyncMock()
        
        # Мокаем повторения
        mock_repetition1 = MagicMock()
        mock_repetition1.user_id = 123
        mock_repetition2 = MagicMock()
        mock_repetition2.user_id = 123
        mock_repetition3 = MagicMock()
        mock_repetition3.user_id = 456
        
        service.schedule_service.get_due_repetitions.return_value = [
            mock_repetition1, mock_repetition2, mock_repetition3
        ]
        
        # Мокаем пользователей
        mock_user1 = MagicMock()
        mock_user1.is_active = True
        mock_user2 = MagicMock()
        mock_user2.is_active = True
        
        service.user_service.get_user.side_effect = [mock_user1, mock_user2]
        
        result = await service.get_users_for_notification()
        
        assert len(result) == 2  # Два пользователя
        assert result[0]['user'] == mock_user1
        assert len(result[0]['repetitions']) == 2  # У первого пользователя 2 повторения
        assert result[1]['user'] == mock_user2
        assert len(result[1]['repetitions']) == 1  # У второго пользователя 1 повторение


class TestUserService:
    """Тесты для UserService"""
    
    @pytest.fixture
    def service(self):
        """Фикстура для создания UserService"""
        mock_db = AsyncMock()
        return UserService(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, service):
        """Тест получения существующего пользователя"""
        mock_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_or_create_user(123, "test", "Test")
        
        assert result == mock_user
        service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio  
    async def test_get_or_create_user_new(self, service):
        """Тест создания нового пользователя"""
        # Первый вызов - пользователь не найден
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None
    
        # Второй вызов - пользователь создан
        mock_user = MagicMock()
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_user

        service.db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        service.db.add = MagicMock()
        service.db.commit = AsyncMock()

        result = await service.get_or_create_user(123, "test", "Test")

        # Проверяем что пользователь был создан и добавлен
        service.db.add.assert_called_once()
        service.db.commit.assert_called_once()
        assert service.db.execute.call_count >= 1
