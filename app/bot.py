"""
Telegram bot для обучения по методу Эббингауза
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.user_service import UserService
from app.services.material_service import MaterialService
from app.services.schedule_service import ScheduleService
from app.services.notification_service import NotificationService

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class EbbinghausBot:
    """Основной класс Telegram бота"""
    
    def __init__(self):
        self.application = Application.builder().token(settings.bot_token).build()
        self._setup_handlers()
        self._setup_commands()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("schedule", self.schedule_command))
        self.application.add_handler(CommandHandler("repetitions", self.schedule_command))  # Алиас
        
        # Inline кнопки
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Текстовые сообщения
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    def _setup_commands(self):
        """Настройка команд бота для отображения в меню"""
        self.commands = [
            BotCommand("start", "🚀 Начать работу с ботом"),
            BotCommand("help", "❓ Справка по командам"),
            BotCommand("stats", "📊 Статистика повторений"),
            BotCommand("schedule", "📅 Расписание повторений"),
            BotCommand("repetitions", "🔄 Мои повторения (алиас для schedule)")
        ]
    
    async def register_commands(self):
        """Зарегистрировать команды в Telegram"""
        try:
            await self.application.bot.set_my_commands(self.commands)
            logger.info("Команды бота успешно зарегистрированы")
        except Exception as e:
            logger.error(f"Ошибка регистрации команд: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        async with AsyncSessionLocal() as db:
            user_service = UserService(db)
            
            # Создаем или получаем пользователя
            db_user = await user_service.get_or_create_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            # Проверяем, ознакомился ли пользователь ранее
            if db_user.is_acknowledged:
                # Пользователь уже ознакомлен - показываем краткое приветствие
                welcome_back_text = f"""
Привет снова, {user.first_name or 'друг'}! 👋

🎯 Готов продолжить изучение по методу Эббингауза?

📋 Доступные команды:
• Отправь текст - добавить новый материал
• /schedule - мои повторения
• /stats - статистика обучения  
• /help - справка

📚 Просто отправь мне текст того, что изучил, и я создам расписание повторений!
                """
                await update.message.reply_text(welcome_back_text)
                return
        
        # Первое знакомство - показываем полную инструкцию
        welcome_text = """
Привет! 👋 Я помогу тебе выучить материал по методу Эббингауза.

📈 Кривая забывания Эббингауза показывает, что мы забываем:
• 50% информации через 20 минут
• 70% через день  
• 90% через неделю

Но если повторять материал в определенные интервалы, информация закрепится в долговременной памяти навсегда!

🔬 Интервалы повторений:
📝 Сразу → ⏰ 20-30 мин → 🌆 Вечером → 📅 +1 день → 📅 +3 дня → 📅 +7 дней → 📅 +14 дней → 📅 +30 дней

💡 Каждое утро в 07:00 я буду напоминать тебе о повторениях!
        """
        
        keyboard = [[InlineKeyboardButton("Ознакомлен ✅", callback_data="acknowledged")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🔧 Доступные команды:

/start - Начать работу с ботом
/help - Показать эту справку
/schedule - Мои повторения (расписание)
/stats - Статистика обучения

📝 Как использовать:
1. Отправь мне текст с вопросами/темами, которые изучил
2. Я создам расписание повторений по методу Эббингауза
3. Получай напоминания: через 25 мин, вечером, утром в 07:00
4. Отмечай результат повторений кнопками ✅/❌
5. Используй /schedule чтобы посмотреть все свои повторения

🎯 Цель: закрепить знания в долговременной памяти!

🔬 Интервалы: сразу → 25 мин → вечером → +1 день → +3 дня → +7 дней → +14 дней → +30 дней
        """
        
        await update.message.reply_text(help_text)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        user_id = update.effective_user.id
        
        async with AsyncSessionLocal() as db:
            user_service = UserService(db)
            material_service = MaterialService(db)
            notification_service = NotificationService(db)
            
            # Получаем статистику
            user = await user_service.get_user_with_stats(user_id)
            if not user:
                await update.message.reply_text("❌ Пользователь не найден. Используй /start")
                return
            
            materials_count = await material_service.get_materials_count(user_id)
            notification_stats = await notification_service.get_notification_statistics(user_id)
            
            # Считаем общую статистику
            total_success = sum(stat.successful_repetitions for stat in user.user_statistics)
            total_failed = sum(stat.failed_repetitions for stat in user.user_statistics)
            total_materials = sum(stat.total_materials_added for stat in user.user_statistics)
            
            success_rate = 0
            if total_success + total_failed > 0:
                success_rate = (total_success / (total_success + total_failed)) * 100
        
        stats_text = f"""
📊 Твоя статистика обучения:

📚 Материалы:
• Всего добавлено: {total_materials}
• Активных: {materials_count}

🎯 Повторения:
• Успешных: {total_success} ✅
• Неудачных: {total_failed} ❌
• Процент успеха: {success_rate:.1f}%

📅 Расписание:
• На сегодня: {notification_stats['today_count']}
• Просрочено: {notification_stats['overdue_count']}
• На неделю: {notification_stats['upcoming_count']}

👤 Аккаунт создан: {user.created_at.strftime('%d.%m.%Y')}
        """
        
        await update.message.reply_text(stats_text)
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /schedule (мои повторения)"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested schedule")
        
        try:
            async with AsyncSessionLocal() as db:
                schedule_service = ScheduleService(db)
                material_service = MaterialService(db)
                
                # Получаем расписание на 35 дней (покрывает все интервалы Эббингауза)
                upcoming = await schedule_service.get_user_schedule(user_id, days_ahead=35, include_completed=False)
                overdue = await schedule_service.get_overdue_repetitions(user_id)
                today_repetitions = [r for r in upcoming if r.scheduled_date == datetime.now().date()]
                
                if not upcoming and not overdue:
                    await update.message.reply_text(
                        "📅 У тебя пока нет запланированных повторений.\n\n"
                        "📚 Добавь новый материал, отправив мне текст того, что изучил!\n\n"
                        "💡 Я создам расписание повторений по методу Эббингауза."
                    )
                    return
                
                schedule_parts = ["📅 **МОИ ПОВТОРЕНИЯ**"]
                
                # Сегодняшние повторения
                if today_repetitions:
                    schedule_parts.append(f"\n🔥 **СЕГОДНЯ** ({len(today_repetitions)}):")
                    for item in today_repetitions:
                        type_emoji = self._get_repetition_emoji(item.repetition_type)
                        # Проверяем, что материал загружен
                        if hasattr(item, 'material') and item.material:
                            content_short = item.material.content[:100] + "..." if len(item.material.content) > 100 else item.material.content
                        else:
                            content_short = f"Материал #{item.material_id}"
                        schedule_parts.append(f"{type_emoji} {content_short}")
                
                # Просроченные повторения
                if overdue:
                    schedule_parts.append(f"\n⚠️ **ПРОСРОЧЕНО** ({len(overdue)}):")
                    for item in overdue[:5]:  # Показываем только первые 5
                        days_overdue = (datetime.now().date() - item.scheduled_date).days
                        # Проверяем, что материал загружен
                        if hasattr(item, 'material') and item.material:
                            content_short = item.material.content[:80] + "..." if len(item.material.content) > 80 else item.material.content
                        else:
                            content_short = f"Материал #{item.material_id}"
                        schedule_parts.append(f"❌ {item.scheduled_date.strftime('%d.%m')} ({days_overdue}д назад) - {content_short}")
                
                # Ближайшие повторения по дням
                if upcoming:
                    schedule_parts.append(f"\n📋 **БЛИЖАЙШИЕ** ({len(upcoming)}):")
                    current_date = None
                    shown_count = 0
                    
                    for item in upcoming:
                        if shown_count >= 50:  # Увеличенный лимит для показа всех интервалов
                            break
                                
                        if item.scheduled_date == datetime.now().date():
                            continue  # Уже показали в разделе "сегодня"
                        
                        if item.scheduled_date != current_date:
                            current_date = item.scheduled_date
                            # Определяем день недели
                            weekday = current_date.strftime('%A')
                            weekday_ru = {
                                'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 
                                'Thursday': 'Чт', 'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'
                            }
                            day_name = weekday_ru.get(weekday, weekday)
                            schedule_parts.append(f"\n📆 {current_date.strftime('%d.%m')} ({day_name}):")
                        
                        type_emoji = self._get_repetition_emoji(item.repetition_type)
                        # Проверяем, что материал загружен
                        if hasattr(item, 'material') and item.material:
                            content_short = item.material.content[:60] + "..." if len(item.material.content) > 60 else item.material.content
                        else:
                            content_short = f"Материал #{item.material_id}"
                        schedule_parts.append(f"  {type_emoji} {content_short}")
                        shown_count += 1
                
                    schedule_parts.append(f"\n💡 Используй /stats для просмотра статистики")
                
                # Отправляем сообщение с проверкой длины
                await self._send_long_message(update, schedule_parts)
            
        except Exception as e:
            logger.error(f"Error in schedule_command for user {user_id}: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка при получении расписания.\n\n"
                "Попробуй позже или обратись к администратору."
            )
    
    def _get_repetition_emoji(self, repetition_type: str) -> str:
        """Получить эмодзи для типа повторения"""
        emoji_map = {
            'immediate': '📝',
            'short_term': '⏰', 
            'evening': '🌆',
            'day_1': '📅',
            'day_3': '📆',
            'day_7': '🗓️',
            'day_14': '📋',
            'day_30': '📊'
        }
        return emoji_map.get(repetition_type, '📚')
    
    async def _send_long_message(self, update: Update, message_parts: List[str]):
        """
        Отправить длинное сообщение, разбивая на части если необходимо
        
        Args:
            update: Update объект
            message_parts: Список строк сообщения
        """
        TELEGRAM_MAX_LENGTH = 4096
        
        full_message = "\n".join(message_parts)
        
        # Если сообщение помещается - отправляем как есть
        if len(full_message) <= TELEGRAM_MAX_LENGTH:
            await update.message.reply_text(full_message)
            return
        
        # Если сообщение слишком длинное - разбиваем на части
        current_message = ""
        messages_to_send = []
        
        for part in message_parts:
            # Проверяем, поместится ли следующая часть
            if len(current_message) + len(part) + 1 <= TELEGRAM_MAX_LENGTH:
                if current_message:
                    current_message += "\n"
                current_message += part
            else:
                # Текущее сообщение готово к отправке
                if current_message:
                    messages_to_send.append(current_message)
                
                # Если одна часть слишком длинная - обрезаем её
                if len(part) > TELEGRAM_MAX_LENGTH:
                    part = part[:TELEGRAM_MAX_LENGTH - 50] + "... (обрезано)"
                
                current_message = part
        
        # Добавляем последнюю часть
        if current_message:
            messages_to_send.append(current_message)
        
        # Отправляем все части
        for i, message in enumerate(messages_to_send):
            if i > 0:
                # Добавляем номер части для многочастных сообщений
                message = f"📄 Часть {i+1}:\n\n{message}"
            await update.message.reply_text(message)
            
            # Небольшая задержка между сообщениями
            if i < len(messages_to_send) - 1:
                await asyncio.sleep(0.5)
    
    def _parse_questions(self, content: str) -> List[str]:
        """
        Парсит текст по знаку "?" для разделения на логические блоки
        
        Args:
            content: Исходный текст
            
        Returns:
            Список вопросов/блоков
        """
        import re
        
        # Сначала пробуем разделить по строкам, где каждая строка заканчивается на "?"
        lines = content.strip().split('\n')
        
        questions = []
        for line in lines:
            line = line.strip()
            if line and len(line) >= 5:
                # Если строка заканчивается на "?" - это готовый вопрос
                if line.endswith('?'):
                    questions.append(line)
                else:
                    # Если не заканчивается на "?" но содержит вопросительные слова
                    question_words = ['что', 'как', 'где', 'когда', 'почему', 'зачем', 'какой', 'какая', 'какое', 'какие', 'кто', 'куда', 'откуда', 'есть', 'чтобы']
                    if any(word in line.lower() for word in question_words):
                        questions.append(line + '?')
                    else:
                        questions.append(line)
        
        # Если получилось несколько вопросов из строк, возвращаем их
        if len(questions) > 1:
            return questions
        
        # Если не получилось разделить по строкам, пробуем по знаку "?"
        # Используем более простое разделение
        parts = re.split(r'\?', content)
        
        questions = []
        for i, part in enumerate(parts):
            part = part.strip()
            if part and len(part) >= 5:
                # Добавляем "?" обратно ко всем частям кроме последней
                if i < len(parts) - 1:  # Не последняя часть
                    questions.append(part + '?')
                else:  # Последняя часть
                    # Проверяем, нужно ли добавить "?"
                    question_words = ['что', 'как', 'где', 'когда', 'почему', 'зачем', 'какой', 'какая', 'какое', 'какие', 'кто', 'куда', 'откуда', 'есть', 'чтобы']
                    if any(word in part.lower() for word in question_words):
                        questions.append(part + '?')
                    elif part:  # Если есть текст, добавляем как есть
                        questions.append(part)
        
        # Если получился только один блок или нет вопросов, возвращаем исходный контент
        if len(questions) <= 1:
            return [content.strip()]
        
        return questions
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        try:
            if data == "acknowledged":
                await self._handle_acknowledgment(query)
            elif data.startswith("complete_"):
                await self._handle_repetition_completion(query, user_id, data)
            elif data.startswith("reminder_"):
                await self._handle_reminder_response(query, user_id, data)
            else:
                logger.warning(f"Unknown callback data: {data}")
                await query.edit_message_text("❌ Неизвестная команда")
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке команды")
    
    async def _handle_acknowledgment(self, query):
        """Обработка нажатия кнопки 'Ознакомлен'"""
        user_id = query.from_user.id
        
        # Сохраняем состояние ознакомления в БД
        async with AsyncSessionLocal() as db:
            user_service = UserService(db)
            user = await user_service.get_user(user_id)
            if user:
                user.is_acknowledged = True
                await db.commit()
        
        await query.edit_message_text(
            "Отлично! 🎉\n\n"
            "Теперь давай начнем! Какие вопросы или темы ты сегодня изучил?\n\n"
            "📚 Просто отправь мне текст с материалом, и я создам расписание повторений.\n\n"
            "💡 Используй команду /schedule чтобы посмотреть свои повторения."
        )
    
    async def _handle_repetition_completion(self, query, user_id: int, callback_data: str):
        """Обработка отметки о выполнении повторения"""
        # Парсим callback_data: complete_{schedule_id}_{result} или complete_all_{result}
        parts = callback_data.split("_")
        
        async with AsyncSessionLocal() as db:
            schedule_service = ScheduleService(db)
            
            if parts[1] == "all":
                # Отмечаем все повторения на сегодня
                result = parts[2] == "success"
                due_repetitions = await schedule_service.get_due_repetitions(user_id=user_id)
                
                completed_count = 0
                for repetition in due_repetitions:
                    success = await schedule_service.complete_repetition(
                        repetition.id, user_id, result
                    )
                    if success:
                        completed_count += 1
                
                result_text = "✅ Отлично!" if result else "❌ Ничего страшного!"
                await query.edit_message_text(
                    f"{result_text}\n\n"
                    f"Отмечено повторений: {completed_count}\n\n"
                    "🎯 Помни: регулярность важнее идеального результата!\n"
                    "Увидимся завтра! 💪"
                )
            else:
                # Отмечаем конкретное повторение
                try:
                    schedule_id = int(parts[1])
                    result = parts[2] == "success"
                    
                    success = await schedule_service.complete_repetition(
                        schedule_id, user_id, result
                    )

                    if success:
                        if result:
                            result_text = "✅ Повторение отмечено как успешное!"
                            message = f"{result_text}\n\nОтлично! Продолжай в том же духе! 💪"
                        else:
                            result_text = "❌ Повторение отмечено как неудачное."
                            message = f"{result_text}\n\nНичего страшного: попробуй повторять материал почаще, чтобы успевать по расписанию Эббингауза 💪"

                        await query.edit_message_text(message)
                    else:
                        await query.edit_message_text("❌ Ошибка при обработке повторения")
                        
                except (ValueError, IndexError):
                    await query.edit_message_text("❌ Некорректный формат данных")
    
    async def _handle_reminder_response(self, query, user_id: int, callback_data: str):
        """Обработка ответа на напоминание о повторении"""
        # Парсим callback_data: reminder_{success/failed}_{type}
        parts = callback_data.split("_")
        
        if len(parts) < 3:
            await query.edit_message_text("❌ Некорректный формат данных")
            return
        
        result = parts[1] == "success"
        reminder_type = parts[2]
        
        # Сохраняем результат в БД
        async with AsyncSessionLocal() as db:
            schedule_service = ScheduleService(db)
            
            # Находим соответствующее повторение на сегодня
            from datetime import date
            today_repetitions = await schedule_service.get_due_repetitions(
                user_id=user_id,
                target_date=date.today()
            )
            
            # Ищем повторение с нужным типом
            for repetition in today_repetitions:
                if repetition.repetition_type == reminder_type:
                    # Отмечаем повторение как выполненное
                    await schedule_service.complete_repetition(
                        repetition.id, user_id, result
                    )
                    break
        
        # Названия типов напоминаний
        type_names = {
            'short_term': '⏰ 20-минутное повторение',
            'evening': '🌆 Вечернее повторение'
        }
        
        type_display = type_names.get(reminder_type, 'Повторение')
        result_text = "✅ Отлично!" if result else "❌ Ничего страшного!"
        
        response_message = f"{result_text}\n\n"
        
        if result:
            response_message += f"Ты успешно выполнил {type_display.lower()}! 💪\n\n"
            if reminder_type == 'short_term':
                response_message += "🌆 Не забудь повторить материал вечером!"
            elif reminder_type == 'evening':
                response_message += "📅 Увидимся завтра утром в 07:00!"
        else:
            response_message += f"Ты пропустил {type_display.lower()}.\n\n"
            response_message += "💡 Помни: регулярность важнее идеального результата!\n"
            response_message += "Попробуй повторить материал позже."
        
        await query.edit_message_text(response_message)
    
    async def _send_immediate_reminders(self, material, user_id: int, db_session):
        """Отправка немедленных напоминаний для сегодняшнего дня"""
        try:
            from app.services.schedule_service import ScheduleService
            
            schedule_service = ScheduleService(db_session)
            
            # Получаем повторения на сегодня
            today_repetitions = await schedule_service.get_due_repetitions(
                user_id=user_id,
                target_date=datetime.utcnow().date()
            )
            
            # Фильтруем только immediate, short_term, evening
            immediate_repetitions = [
                r for r in today_repetitions 
                if r.repetition_type in ['immediate', 'short_term', 'evening'] 
                and r.material_id == material.id
            ]
            
            if immediate_repetitions:
                # Планируем напоминания на сегодня
                for repetition in immediate_repetitions:
                    if repetition.repetition_type == 'short_term':
                        # Напоминание через 25 минут
                        reminder_time = datetime.utcnow() + timedelta(minutes=25)
                        asyncio.create_task(
                            self._schedule_delayed_reminder(user_id, material.content, reminder_time, "short_term")
                        )
                    elif repetition.repetition_type == 'evening':
                        # Напоминание вечером в 20:00 по часовому поясу пользователя
                        from app.utils.timezone_utils import get_user_timezone
                        
                        user_tz = get_user_timezone("Asia/Yekaterinburg")
                        now_local = datetime.now(user_tz)
                        evening_time = now_local.replace(hour=20, minute=0, second=0, microsecond=0)
                        
                        if evening_time > now_local:
                            # Конвертируем в UTC для планировщика
                            evening_utc = evening_time.astimezone(pytz.UTC).replace(tzinfo=None)
                            asyncio.create_task(
                                self._schedule_delayed_reminder(user_id, material.content, evening_utc, "evening")
                            )
                        else:
                            # Если 20:00 уже прошло, планируем на завтра
                            tomorrow_evening = (now_local + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
                            evening_utc = tomorrow_evening.astimezone(pytz.UTC).replace(tzinfo=None)
                            asyncio.create_task(
                                self._schedule_delayed_reminder(user_id, material.content, evening_utc, "evening")
                            )
                            
        except Exception as e:
            logger.error(f"Error sending immediate reminders: {e}")
    
    async def _schedule_delayed_reminder(self, user_id: int, content: str, reminder_time: datetime, reminder_type: str):
        """Запланировать отложенное напоминание"""
        try:
            # Ждем до времени напоминания
            delay = (reminder_time - datetime.utcnow()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
                
                # Отправляем напоминание
                type_names = {
                    'short_term': '⏰ Время повторить материал! (20-30 мин прошло)',
                    'evening': '🌆 Вечернее повторение материала!'
                }
                
                message = f"""
{type_names.get(reminder_type, '📚 Время повторения!')}

📝 Материал: {content[:100]}{'...' if len(content) > 100 else ''}

Повтори материал и отметь результат:
                """
                
                keyboard = [
                    [
                        InlineKeyboardButton("Повторил ✅", callback_data=f"reminder_success_{reminder_type}"),
                        InlineKeyboardButton("Не повторил ❌", callback_data=f"reminder_failed_{reminder_type}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in delayed reminder: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений (добавление материала)"""
        user_id = update.effective_user.id
        content = update.message.text.strip()
        
        if len(content) < 5:
            await update.message.reply_text(
                "📝 Текст слишком короткий. Добавь больше деталей о том, что изучил."
            )
            return
        
        if len(content) > 2000:
            await update.message.reply_text(
                "📝 Текст слишком длинный. Разбей на более короткие фрагменты."
            )
            return
        
        async with AsyncSessionLocal() as db:
            material_service = MaterialService(db)
            schedule_service = ScheduleService(db)
            
            try:
                # Парсим материал по знаку "?" для разделения на логические блоки
                questions = self._parse_questions(content)
                
                if len(questions) > 1:
                    # Создаем материалы для каждого вопроса
                    created_materials = []
                    total_schedules = 0
                    
                    for i, question in enumerate(questions, 1):
                        material = await material_service.create_material(user_id, question)
                        created_materials.append(material)
                        
                        # Создаем расписание повторений для каждого вопроса
                        schedule = await schedule_service.create_full_schedule(
                            material.id, user_id, datetime.utcnow()
                        )
                        total_schedules += len(schedule)
                        
                        # Отправляем немедленное уведомление о повторении
                        await self._send_immediate_reminders(material, user_id, db)
                    
                    # Подтверждение создания с полным списком вопросов
                    questions_list = "\n".join([f"{i}. {q}" 
                                               for i, q in enumerate(questions, 1)])
                    
                    await update.message.reply_text(
                        f"✅ Материал разделен на {len(questions)} вопросов!\n\n"
                        f"📚 Список вопросов:\n{questions_list}\n\n"
                        f"📅 Создано повторений: {total_schedules}\n\n"
                        f"🎯 Начинаем укреплять память! Повтори каждый вопрос:\n\n"
                        f"📝 **СЕЙЧАС** - прочти еще раз\n"
                        f"⏰ Через 20-30 минут\n"
                        f"🌆 Вечером сегодня\n"
                        f"📅 Завтра утром в 07:00"
                    )
                else:
                    # Один блок - обрабатываем как обычно
                    material = await material_service.create_material(user_id, content)
                    
                    # Создаем расписание повторений
                    schedule = await schedule_service.create_full_schedule(
                        material.id, user_id, datetime.utcnow()
                    )
                    
                    # Подтверждение создания
                    await update.message.reply_text(
                        f"✅ Материал добавлен!\n\n"
                        f"📚 Содержимое: {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
                        f"📅 Создано повторений: {len(schedule)}\n\n"
                        f"🎯 Начинаем укреплять память! Повтори этот материал:\n\n"
                        f"📝 **СЕЙЧАС** - прочти еще раз\n"
                        f"⏰ Через 20-30 минут\n"
                        f"🌆 Вечером сегодня\n"
                        f"📅 Завтра утром в 07:00"
                    )
                    
                    # Отправляем немедленное уведомление о повторении
                    await self._send_immediate_reminders(material, user_id, db)
                
            except Exception as e:
                logger.error(f"Error creating material: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при добавлении материала. Попробуй позже."
                )


# Глобальный экземпляр бота
bot_instance = EbbinghausBot()


async def send_notification_to_user(
    user_id: int,
    message_text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None
):
    """
    Отправить уведомление пользователю
    
    Args:
        user_id: ID пользователя в Telegram
        message_text: Текст сообщения
        reply_markup: Inline клавиатура
    """
    try:
        await bot_instance.application.bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=reply_markup
        )
        logger.info(f"Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")


async def send_daily_notifications():
    """Отправить ежедневные уведомления всем пользователям"""
    async with AsyncSessionLocal() as db:
        notification_service = NotificationService(db)
        
        # Получаем пользователей с повторениями на сегодня
        users_data = await notification_service.get_users_for_notification()
        
        logger.info(f"Sending notifications to {len(users_data)} users")
        
        for user_data in users_data:
            user = user_data['user']
            repetitions = user_data['repetitions']
            
            try:
                # Формируем сообщение
                message_text = await notification_service.format_notification_message(
                    user, repetitions
                )
                
                # Создаем клавиатуру
                keyboard_data = await notification_service.create_notification_markup(repetitions)
                reply_markup = InlineKeyboardMarkup(keyboard_data) if keyboard_data else None
                
                # Отправляем уведомление
                await send_notification_to_user(user.user_id, message_text, reply_markup)
                
                # Отмечаем как отправленное
                repetition_ids = [r.id for r in repetitions]
                await notification_service.mark_notification_sent(user.user_id, repetition_ids)
                
            except Exception as e:
                logger.error(f"Failed to send notification to user {user.user_id}: {e}")
