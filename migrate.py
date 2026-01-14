#!/usr/bin/env python3
"""
Инициализация БД для Render
"""
import os
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db, Game

def init_database():
    """Создание таблиц и тестовых данных"""
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        
        # Проверяем, есть ли игры
        if Game.query.count() == 0:
            # Добавляем тестовые игры
            test_games = [
                Game(name="Змейка", description="Классическая игра змейка", rating=4.8, is_featured=True),
                Game(name="Тетрис", description="Классический тетрис", rating=4.7, is_featured=True),
                Game(name="Крестики-нолики", description="Игра на двоих", rating=4.2),
                Game(name="Камень-ножницы-бумага", description="Угадай выбор компьютера", rating=4.0),
            ]
            
            for game in test_games:
                db.session.add(game)
            
            db.session.commit()
            print("✅ Добавлено 4 тестовые игры")
        else:
            print("✅ База данных уже содержит данные")
        
        print(f"✅ Всего игр: {Game.query.count()}")
        print("✅ База данных готова!")

if __name__ == "__main__":
    init_database()
