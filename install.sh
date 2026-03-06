#!/bin/bash
echo "🛡️ ARCH_AI: Запуск системной инициализации (Arch Linux)..."

# 1. Проверка и установка системного Python через pacman [1]
if ! command -v python3 &> /dev/null; then
    echo "📦 Python не найден. Установка системных пакетов..."
    sudo pacman -S --needed --noconfirm python python-pip python-virtualenv
else
    echo "✅ Python уже в системе."
fi

# 2. Поиск конкретной версии для venv
PYTHON_EXE=$(which python3.14 || which python3.13 || which python3.12 || which python3)
echo "🚀 Используется: $PYTHON_EXE"

# 3. Создание изолированного окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения (venv)..."
    $PYTHON_EXE -m venv venv
fi

# 4. Установка зависимостей из requirements.txt [2]
if [ -f "requirements.txt" ]; then
    echo "📥 Обновление pip и установка библиотек из списка..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
else
    echo "⚠️ Ошибка: requirements.txt не найден! Создайте его с 'requests' и 'python-dotenv'."
    exit 1
fi

# 5. Финальная настройка структуры
mkdir -p sessions
chmod +x run.sh 2>/dev/null

echo "---"
echo "✅ Установка завершена успешно."
echo "📟 Для запуска используйте: ./run.sh"