#!/bin/bash
# 1. ПРОВЕРКА И СОЗДАНИЕ VENV
if [ ! -f "venv/bin/activate" ]; then
    echo -e "\033[1;31m[!] Окружение не найдено. Создаю заново...\033[0m"
    # Удаляем битую папку, если она есть
    rm -rf venv
    python -m venv venv
fi

# 2. АКТИВАЦИЯ
source venv/bin/activate || { echo "Ошибка активации!"; exit 1; }

# Проверяем, менялся ли файл зависимостей
md5sum requirements.txt > .current_req_hash

if ! diff -q .current_req_hash .last_installed_hash > /dev/null 2>&1; then
    echo "[!] Зависимости изменились. Обновляю пакеты..."
    pip install -r requirements.txt
    cp .current_req_hash .last_installed_hash
fi

python main.py