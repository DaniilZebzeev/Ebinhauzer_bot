"""
SQLAlchemy модели для базы данных
"""
from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import (
    BigInteger, Column, Integer, String, Text, Boolean,
    DateTime, Date, Time, ForeignKey, func, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class User(Base):
    """Таблица пользователей"""
    __tablename__ = "users"
    
    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    timezone = Column(String(50), default="Asia/Yekaterinburg")
    notification_time = Column(Time, default=time(7, 0))
    is_active = Column(Boolean, default=True)
    is_acknowledged = Column(Boolean, default=False)  # Ознакомился ли с инструкцией
    
    # Relationships
    study_materials = relationship("StudyMaterial", back_populates="user", cascade="all, delete-orphan")
    repetition_schedules = relationship("RepetitionSchedule", back_populates="user", cascade="all, delete-orphan")
    repetition_results = relationship("RepetitionResult", back_populates="user", cascade="all, delete-orphan")
    user_statistics = relationship("UserStatistics", back_populates="user", cascade="all, delete-orphan")


class StudyMaterial(Base):
    """Таблица учебных материалов"""
    __tablename__ = "study_materials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    current_stage = Column(Integer, default=0)  # Текущая стадия повторений (0-8)
    last_success_at = Column(DateTime, nullable=True)  # Время последнего успешного повторения

    # Relationships
    user = relationship("User", back_populates="study_materials")
    repetition_schedules = relationship("RepetitionSchedule", back_populates="material", cascade="all, delete-orphan")
    repetition_results = relationship("RepetitionResult", back_populates="material", cascade="all, delete-orphan")


class RepetitionSchedule(Base):
    """Таблица расписания повторений"""
    __tablename__ = "repetition_schedule"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    repetition_type = Column(String(20), nullable=False)  # 'immediate', 'short_term', 'evening', 'day_1', etc.
    interval_days = Column(Integer, nullable=False)  # 0, 0, 0, 1, 3, 7, 14, 30
    current_stage = Column(Integer, nullable=False, default=0)  # Стадия этого повторения (0-8)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    scheduled_datetime = Column(DateTime, nullable=True)  # Точное время повторения с учетом timezone

    # Relationships
    user = relationship("User", back_populates="repetition_schedules")
    material = relationship("StudyMaterial", back_populates="repetition_schedules")
    repetition_results = relationship("RepetitionResult", back_populates="schedule", cascade="all, delete-orphan")

    # Индексы для оптимизации
    __table_args__ = (
        Index('ix_user_material_incomplete', 'user_id', 'material_id', 'is_completed'),
        Index('ix_scheduled_date', 'scheduled_date'),
        {'extend_existing': True}
    )


class RepetitionResult(Base):
    """Таблица результатов повторений"""
    __tablename__ = "repetition_results"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("repetition_schedule.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=False)
    was_successful = Column(Boolean, nullable=False)
    completed_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="repetition_results")
    material = relationship("StudyMaterial", back_populates="repetition_results")
    schedule = relationship("RepetitionSchedule", back_populates="repetition_results")


class UserStatistics(Base):
    """Таблица статистики пользователей"""
    __tablename__ = "user_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    date = Column(Date, default=func.current_date())
    successful_repetitions = Column(Integer, default=0)
    failed_repetitions = Column(Integer, default=0)
    total_materials_added = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_statistics")
    
    # Уникальный индекс для user_id + date
    __table_args__ = (
        {'extend_existing': True}
    )
