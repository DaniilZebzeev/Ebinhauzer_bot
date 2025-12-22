-- Инициализация базы данных для Telegram-бота по методу Эббингауза

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Установка часового пояса по умолчанию
SET timezone = 'Asia/Yekaterinburg';

-- Создание пользователя приложения (если нужно)
-- DO $$ 
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ebbinghaus_user') THEN
--         CREATE ROLE ebbinghaus_user WITH LOGIN PASSWORD 'your_password';
--     END IF;
-- END
-- $$;

-- Создание индексов для оптимизации (будут созданы через Alembic миграции)
-- Но можно подготовить базовую структуру

-- Настройка базы данных для работы с русской локалью
UPDATE pg_database SET datcollate='ru_RU.UTF-8', datctype='ru_RU.UTF-8' WHERE datname='ebbinghaus_db';

-- Комментарии для документации
COMMENT ON DATABASE ebbinghaus_db IS 'База данных для Telegram-бота обучения по методу Эббингауза';
