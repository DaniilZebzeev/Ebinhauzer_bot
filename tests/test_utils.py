"""
Тесты для утилит
"""
import pytest
from datetime import datetime, timedelta
import pytz
from zoneinfo import ZoneInfo

from app.utils.ebbinghaus import (
    calculate_next_repetition,
    calculate_failed_repetition,
    get_stage_name,
    get_stage_description,
    EbbinghausScheduler
)


class TestCalculateNextRepetition:
    """Тесты для функции calculate_next_repetition"""

    @pytest.fixture
    def test_timezone(self):
        """Фикстура для тестовой таймзоны"""
        return "Asia/Yekaterinburg"

    @pytest.fixture
    def created_at(self):
        """Фикстура для времени создания материала"""
        tz = ZoneInfo("Asia/Yekaterinburg")
        return datetime(2025, 1, 1, 10, 0, 0, tzinfo=tz)

    def test_stage_0_to_1(self, created_at, test_timezone):
        """Тест стадии 0 → 1: Через 20 минут"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 0, test_timezone
        )

        assert next_stage == 1
        expected = created_at + timedelta(minutes=20)
        assert next_due_at == expected

    def test_stage_1_to_2(self, created_at, test_timezone):
        """Тест стадии 1 → 2: Сегодня в 20:00"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 1, test_timezone
        )

        assert next_stage == 2
        assert next_due_at.hour == 20
        assert next_due_at.minute == 0
        assert next_due_at.date() == created_at.date()

    def test_stage_1_to_2_after_evening(self, test_timezone):
        """Тест стадии 1 → 2 когда уже после 20:00 (переносится на следующий день)"""
        tz = ZoneInfo(test_timezone)
        created_at = datetime(2025, 1, 1, 21, 0, 0, tzinfo=tz)

        next_due_at, next_stage = calculate_next_repetition(
            created_at, 1, test_timezone
        )

        assert next_stage == 2
        assert next_due_at.hour == 20
        assert next_due_at.minute == 0
        # Должно быть на следующий день
        assert next_due_at.date() == created_at.date() + timedelta(days=1)

    def test_stage_2_to_3(self, created_at, test_timezone):
        """Тест стадии 2 → 3: Через 1 день в 07:00"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 2, test_timezone
        )

        assert next_stage == 3
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = created_at.date() + timedelta(days=1)
        assert next_due_at.date() == expected_date

    def test_stage_3_to_4(self, created_at, test_timezone):
        """Тест стадии 3 → 4: Через 3 дня в 07:00"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 3, test_timezone
        )

        assert next_stage == 4
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = created_at.date() + timedelta(days=3)
        assert next_due_at.date() == expected_date

    def test_stage_4_to_5(self, created_at, test_timezone):
        """Тест стадии 4 → 5: Через 7 дней в 07:00"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 4, test_timezone
        )

        assert next_stage == 5
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = created_at.date() + timedelta(days=7)
        assert next_due_at.date() == expected_date

    def test_stage_5_to_6(self, created_at, test_timezone):
        """Тест стадии 5 → 6: Через 14 дней в 07:00"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 5, test_timezone
        )

        assert next_stage == 6
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = created_at.date() + timedelta(days=14)
        assert next_due_at.date() == expected_date

    def test_stage_6_to_7(self, created_at, test_timezone):
        """Тест стадии 6 → 7: Через 30 дней в 07:00"""
        next_due_at, next_stage = calculate_next_repetition(
            created_at, 6, test_timezone
        )

        assert next_stage == 7
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = created_at.date() + timedelta(days=30)
        assert next_due_at.date() == expected_date

    def test_stage_7_to_8_monthly_phase(self, created_at, test_timezone):
        """Тест стадии 7 → 8: Месячная фаза (раз в 30 дней)"""
        # Моделируем последнее успешное повторение
        tz = ZoneInfo(test_timezone)
        last_success_at = datetime(2025, 2, 1, 10, 0, 0, tzinfo=tz)

        next_due_at, next_stage = calculate_next_repetition(
            created_at, 7, test_timezone, last_success_at
        )

        assert next_stage == 8
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        # Должно быть через 30 дней от last_success_at
        expected_date = last_success_at.date() + timedelta(days=30)
        assert next_due_at.date() == expected_date

    def test_stage_8_monthly_phase_continues(self, created_at, test_timezone):
        """Тест стадии 8+: Месячная фаза продолжается (стадия не увеличивается)"""
        tz = ZoneInfo(test_timezone)
        last_success_at = datetime(2025, 3, 1, 10, 0, 0, tzinfo=tz)

        next_due_at, next_stage = calculate_next_repetition(
            created_at, 8, test_timezone, last_success_at
        )

        # Стадия остается 8
        assert next_stage == 8
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        # Через 30 дней от last_success_at
        expected_date = last_success_at.date() + timedelta(days=30)
        assert next_due_at.date() == expected_date

    def test_without_timezone_uses_naive_datetime(self):
        """Тест работы с naive datetime"""
        created_at = datetime(2025, 1, 1, 10, 0, 0)

        next_due_at, next_stage = calculate_next_repetition(
            created_at, 0, "Asia/Yekaterinburg"
        )

        assert next_stage == 1
        assert next_due_at is not None


class TestCalculateFailedRepetition:
    """Тесты для функции calculate_failed_repetition"""

    @pytest.fixture
    def test_timezone(self):
        return "Asia/Yekaterinburg"

    @pytest.fixture
    def failed_at(self):
        tz = ZoneInfo("Asia/Yekaterinburg")
        return datetime(2025, 1, 5, 15, 30, 0, tzinfo=tz)

    def test_failed_at_stage_0(self, failed_at, test_timezone):
        """Тест неудачи на стадии 0: стадия не уходит ниже 0"""
        next_due_at, new_stage = calculate_failed_repetition(
            failed_at, 0, test_timezone
        )

        assert new_stage == 0  # Не уходит ниже 0
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        # Следующий день
        expected_date = failed_at.date() + timedelta(days=1)
        assert next_due_at.date() == expected_date

    def test_failed_at_stage_3(self, failed_at, test_timezone):
        """Тест неудачи на стадии 3: откат на стадию 2"""
        next_due_at, new_stage = calculate_failed_repetition(
            failed_at, 3, test_timezone
        )

        assert new_stage == 2  # 3 - 1
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = failed_at.date() + timedelta(days=1)
        assert next_due_at.date() == expected_date

    def test_failed_at_stage_8_monthly(self, failed_at, test_timezone):
        """Тест неудачи на месячной фазе: откат на стадию 7"""
        next_due_at, new_stage = calculate_failed_repetition(
            failed_at, 8, test_timezone
        )

        assert new_stage == 7  # 8 - 1
        assert next_due_at.hour == 7
        assert next_due_at.minute == 0
        expected_date = failed_at.date() + timedelta(days=1)
        assert next_due_at.date() == expected_date


class TestGetStageName:
    """Тесты для функции get_stage_name"""

    def test_stage_names(self):
        """Тест получения имен всех стадий"""
        assert get_stage_name(0) == 'immediate'
        assert get_stage_name(1) == 'short_term'
        assert get_stage_name(2) == 'evening'
        assert get_stage_name(3) == 'day_1'
        assert get_stage_name(4) == 'day_3'
        assert get_stage_name(5) == 'day_7'
        assert get_stage_name(6) == 'day_14'
        assert get_stage_name(7) == 'day_30'
        assert get_stage_name(8) == 'monthly'
        assert get_stage_name(9) == 'monthly'
        assert get_stage_name(100) == 'monthly'


class TestGetStageDescription:
    """Тесты для функции get_stage_description"""

    def test_stage_descriptions(self):
        """Тест получения описаний всех стадий"""
        assert get_stage_description(0) == 'Сразу'
        assert get_stage_description(1) == 'Через 20 минут'
        assert get_stage_description(2) == 'Вечером в 20:00'
        assert get_stage_description(3) == 'Завтра в 07:00'
        assert get_stage_description(4) == 'Через 3 дня в 07:00'
        assert get_stage_description(5) == 'Через 7 дней в 07:00'
        assert get_stage_description(6) == 'Через 14 дней в 07:00'
        assert get_stage_description(7) == 'Через 30 дней в 07:00'
        assert get_stage_description(8) == 'Раз в месяц в 07:00'
        assert get_stage_description(100) == 'Раз в месяц в 07:00'


class TestEbbinghausScheduler:
    """Тесты для legacy класса EbbinghausScheduler (для обратной совместимости)"""

    @pytest.fixture
    def scheduler(self):
        """Фикстура для создания планировщика"""
        return EbbinghausScheduler("Asia/Yekaterinburg")

    def test_init_default_timezone(self):
        """Тест инициализации с часовым поясом по умолчанию"""
        scheduler = EbbinghausScheduler()
        assert scheduler.timezone_name == "Asia/Yekaterinburg"

    def test_init_custom_timezone(self):
        """Тест инициализации с пользовательским часовым поясом"""
        scheduler = EbbinghausScheduler("Europe/Moscow")
        assert scheduler.timezone_name == "Europe/Moscow"

    def test_calculate_success_rate_normal(self, scheduler):
        """Тест расчета процента успешности - нормальный случай"""
        success_rate = scheduler.calculate_success_rate(10, 7)
        assert success_rate == 0.7

    def test_calculate_success_rate_zero_total(self, scheduler):
        """Тест расчета процента успешности - нет повторений"""
        success_rate = scheduler.calculate_success_rate(0, 0)
        assert success_rate == 0.0

    def test_calculate_success_rate_perfect(self, scheduler):
        """Тест расчета процента успешности - 100% успех"""
        success_rate = scheduler.calculate_success_rate(5, 5)
        assert success_rate == 1.0

    def test_intervals_constant_values(self, scheduler):
        """Тест что интервалы соответствуют константам"""
        expected_intervals = {
            'immediate': 0,
            'short_term': 0,
            'evening': 0,
            'day_1': 1,
            'day_3': 3,
            'day_7': 7,
            'day_14': 14,
            'day_30': 30
        }

        assert scheduler.INTERVALS == expected_intervals


class TestMonthlyPhaseStability:
    """Тесты для проверки стабильности месячной фазы"""

    def test_monthly_phase_interval_stays_30_days(self):
        """Тест что интервал месячной фазы всегда 30 дней"""
        tz = ZoneInfo("Asia/Yekaterinburg")
        created_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=tz)

        # Последовательные успешные повторения на месячной фазе
        last_success = created_at

        for i in range(5):  # 5 месячных повторений
            next_due_at, next_stage = calculate_next_repetition(
                created_at, 8, "Asia/Yekaterinburg", last_success
            )

            # Стадия остается 8
            assert next_stage == 8

            # Интервал ровно 30 дней
            days_diff = (next_due_at.date() - last_success.date()).days
            assert days_diff == 30

            # Обновляем last_success для следующей итерации
            last_success = next_due_at

    def test_monthly_phase_never_shortens(self):
        """Тест что интервал никогда не становится короче 30 дней"""
        tz = ZoneInfo("Asia/Yekaterinburg")
        created_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=tz)

        # Многократные повторения
        last_success = created_at

        for stage in [8, 8, 8, 8]:  # Несколько повторений на стадии 8
            next_due_at, next_stage = calculate_next_repetition(
                created_at, stage, "Asia/Yekaterinburg", last_success
            )

            days_diff = (next_due_at.date() - last_success.date()).days
            # Интервал должен быть ровно 30 дней (не меньше)
            assert days_diff == 30

            last_success = next_due_at
