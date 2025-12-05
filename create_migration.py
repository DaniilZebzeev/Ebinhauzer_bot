#!/usr/bin/env python3
"""
Скрипт для создания начальной миграции базы данных
"""
import os
import sys
import subprocess

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import sync_engine
from app.database.models import Base


def create_initial_migration():
    """Создание начальной миграции"""
    try:
        print("Creating initial migration...")
        
        # Создаем начальную миграцию
        result = subprocess.run([
            'alembic', 'revision', '--autogenerate', 
            '-m', 'Initial migration with all tables'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Initial migration created successfully!")
            print(result.stdout)
        else:
            print("❌ Failed to create migration:")
            print(result.stderr)
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating migration: {e}")
        return False


def apply_migration():
    """Применение миграции"""
    try:
        print("Applying migration...")
        
        result = subprocess.run([
            'alembic', 'upgrade', 'head'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration applied successfully!")
            print(result.stdout)
        else:
            print("❌ Failed to apply migration:")
            print(result.stderr)
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False


def main():
    """Основная функция"""
    print("🚀 Setting up database for Ebbinghaus Bot...")
    
    # Проверяем подключение к БД
    try:
        conn = sync_engine.connect()
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and connection string is correct")
        sys.exit(1)
    
    # Создаем миграцию
    if not create_initial_migration():
        sys.exit(1)
    
    # Применяем миграцию
    if not apply_migration():
        sys.exit(1)
    
    print("\n🎉 Database setup completed successfully!")
    print("You can now run the bot with: python run_local.py")


if __name__ == "__main__":
    main()
