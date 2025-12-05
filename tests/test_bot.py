"""
Тесты для бота
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.bot import EbbinghausBot


class TestEbbinghausBot:
    """Тесты для основного функционала бота"""
    
    @pytest.fixture
    def bot(self):
        """Фикстура для создания экземпляра бота"""
        return EbbinghausBot()
    
    @pytest.fixture
    def mock_update(self):
        """Фикстура для создания mock Update"""
        update = MagicMock()
        user = MagicMock()
        user.id = 123
        user.first_name = "Test"
        
        message = MagicMock()
        message.text = "Test message"
        message.reply_text = AsyncMock()
        
        update.effective_user = user
        update.message = message
        update.callback_query = None
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Фикстура для создания mock Context"""
        return MagicMock()
    
    def test_parse_questions_single_question(self, bot):
        """Тест парсинга одного вопроса"""
        content = "Как работает память в Python?"
        result = bot._parse_questions(content)
        assert result == ["Как работает память в Python?"]
    
    def test_parse_questions_multiple_questions(self, bot):
        """Тест парсинга нескольких вопросов"""
        content = "Как работает память в Python? Как она очищается? Что такое garbage collection?"
        result = bot._parse_questions(content)
        expected = [
            "Как работает память в Python?",
            "Как она очищается?", 
            "Что такое garbage collection?"
        ]
        assert result == expected
    
    def test_parse_questions_real_example(self, bot):
        """Тест парсинга реального примера от пользователя"""
        content = """Есть ли опыт с параллельностью и асинхронностью?
Асинхронность в Python?
Опиши процесс асинхронного работы программы?
Блокирующие функции в асинхронщине?
Когда надо использовать асинхронность?
Как определить нужна ли нам async или нет?
Чтобы программа быстрее выполнилась, что лучше использовать асинхронность или что-то другое?"""
        
        result = bot._parse_questions(content)
        
        # Должно получиться 7 отдельных вопросов
        assert len(result) == 7
        assert "Есть ли опыт с параллельностью и асинхронностью?" in result
        assert "Асинхронность в Python?" in result
        
        # Проверяем что длинный вопрос НЕ обрезается
        long_question = "Чтобы программа быстрее выполнилась, что лучше использовать асинхронность или что-то другое?"
        assert long_question in result
        
        # Проверяем что НИ ОДИН вопрос не содержит "..."
        for question in result:
            assert "..." not in question, f"Вопрос обрезан: {question}"
    
    def test_parse_questions_with_statements(self, bot):
        """Тест парсинга с утверждениями"""
        content = "Python использует подсчет ссылок. Что такое циклические ссылки? GC их удаляет."
        result = bot._parse_questions(content)
        # Должно остаться только утверждения в одном блоке, так как вопрос только один
        assert len(result) >= 1
        assert "Что такое циклические ссылки?" in str(result)
    
    def test_parse_questions_empty_content(self, bot):
        """Тест парсинга пустого контента"""
        content = "?"
        result = bot._parse_questions(content)
        assert result == ["?"]
    
    def test_parse_questions_no_question_marks(self, bot):
        """Тест парсинга без вопросительных знаков"""
        content = "Python - отличный язык программирования"
        result = bot._parse_questions(content)
        assert result == ["Python - отличный язык программирования"]
    
    def test_get_repetition_emoji(self, bot):
        """Тест получения эмодзи для типов повторений"""
        assert bot._get_repetition_emoji('immediate') == '📝'
        assert bot._get_repetition_emoji('short_term') == '⏰'
        assert bot._get_repetition_emoji('evening') == '🌆'
        assert bot._get_repetition_emoji('day_1') == '📅'
        assert bot._get_repetition_emoji('day_3') == '📆'
        assert bot._get_repetition_emoji('day_7') == '🗓️'
        assert bot._get_repetition_emoji('day_14') == '📋'
        assert bot._get_repetition_emoji('day_30') == '📊'
        assert bot._get_repetition_emoji('unknown') == '📚'
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, bot, mock_update, mock_context):
        """Тест команды /start для нового пользователя"""
        mock_update.message.reply_text = AsyncMock()
        
        with patch('app.bot.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('app.bot.UserService') as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                
                # Новый пользователь - не ознакомлен
                mock_user = MagicMock()
                mock_user.is_acknowledged = False
                mock_service.get_or_create_user.return_value = mock_user
                
                await bot.start_command(mock_update, mock_context)
                
                # Проверяем что было отправлено приветствие с кнопкой
                mock_update.message.reply_text.assert_called_once()
                args = mock_update.message.reply_text.call_args
                assert "Привет!" in args[0][0]
                assert args[1]['reply_markup'] is not None
    
    @pytest.mark.asyncio
    async def test_start_command_returning_user(self, bot, mock_update, mock_context):
        """Тест команды /start для возвращающегося пользователя"""
        mock_update.message.reply_text = AsyncMock()
        
        with patch('app.bot.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('app.bot.UserService') as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                
                # Возвращающийся пользователь - уже ознакомлен
                mock_user = MagicMock()
                mock_user.is_acknowledged = True
                mock_service.get_or_create_user.return_value = mock_user
                
                await bot.start_command(mock_update, mock_context)
                
                # Проверяем что было отправлено краткое приветствие
                mock_update.message.reply_text.assert_called_once()
                args = mock_update.message.reply_text.call_args
                assert "Привет снова" in args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_message_short_content(self, bot, mock_update, mock_context):
        """Тест обработки слишком короткого сообщения"""
        mock_update.message.text = "Hi"
        mock_update.message.reply_text = AsyncMock()
        
        await bot.handle_message(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args
        assert "слишком короткий" in args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_message_long_content(self, bot, mock_update, mock_context):
        """Тест обработки слишком длинного сообщения"""
        mock_update.message.text = "x" * 2001
        mock_update.message.reply_text = AsyncMock()
        
        await bot.handle_message(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args
        assert "слишком длинный" in args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_message_single_material(self, bot, mock_update, mock_context):
        """Тест обработки одного материала"""
        mock_update.message.text = "Как работает память в Python"
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_user.id = 123
        
        with patch('app.bot.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('app.bot.MaterialService') as mock_material_service, \
                 patch('app.bot.ScheduleService') as mock_schedule_service, \
                 patch.object(bot, '_send_immediate_reminders') as mock_reminders:
                
                mock_mat_service = AsyncMock()
                mock_material_service.return_value = mock_mat_service
                mock_sched_service = AsyncMock()
                mock_schedule_service.return_value = mock_sched_service
                
                # Создание материала и расписания
                mock_material = MagicMock()
                mock_material.id = 1
                mock_mat_service.create_material.return_value = mock_material
                
                mock_schedule = [MagicMock(), MagicMock()]
                mock_sched_service.create_full_schedule.return_value = mock_schedule
                
                await bot.handle_message(mock_update, mock_context)
                
                # Проверяем что материал был создан
                mock_mat_service.create_material.assert_called_once_with(123, "Как работает память в Python")
                mock_sched_service.create_full_schedule.assert_called_once()
                mock_reminders.assert_called_once()
                mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_handle_message_multiple_questions(self, bot, mock_update, mock_context):
        """Тест обработки нескольких вопросов"""
        mock_update.message.text = "Как работает память в Python? Что такое GC?"
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_user.id = 123
        
        with patch('app.bot.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('app.bot.MaterialService') as mock_material_service, \
                 patch('app.bot.ScheduleService') as mock_schedule_service, \
                 patch.object(bot, '_send_immediate_reminders') as mock_reminders:
                
                mock_mat_service = AsyncMock()
                mock_material_service.return_value = mock_mat_service
                mock_sched_service = AsyncMock()
                mock_schedule_service.return_value = mock_sched_service
                
                # Создание материалов
                mock_material1 = MagicMock()
                mock_material1.id = 1
                mock_material2 = MagicMock()
                mock_material2.id = 2
                mock_mat_service.create_material.side_effect = [mock_material1, mock_material2]
                
                mock_schedule = [MagicMock(), MagicMock()]
                mock_sched_service.create_full_schedule.return_value = mock_schedule
                
                await bot.handle_message(mock_update, mock_context)
                
                # Проверяем что оба материала были созданы
                assert mock_mat_service.create_material.call_count == 2
                assert mock_sched_service.create_full_schedule.call_count == 2
                assert mock_reminders.call_count == 2
                
                # Проверяем что отправлено сообщение с списком вопросов
                mock_update.message.reply_text.assert_called_once()
                args = mock_update.message.reply_text.call_args
                assert "разделен на 2 вопросов" in args[0][0]
