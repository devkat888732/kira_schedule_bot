# Summer 2026 Tasks DB — полная инструкция по установке
# Ubuntu 24.04, nginx, FastAPI, PostgreSQL

# ============================================================
# ШАГ 1 — обновление системы
# ============================================================

sudo apt update && sudo apt upgrade -y


# ============================================================
# ШАГ 2 — установка PostgreSQL
# ============================================================

sudo apt install -y postgresql postgresql-contrib

# запустить и включить автостарт
sudo systemctl start postgresql
sudo systemctl enable postgresql

# создать пользователя и базу данных
sudo -u postgres psql <<EOF
CREATE USER tasksuser WITH PASSWORD 'замени_на_свой_пароль';
CREATE DATABASE tasksdb OWNER tasksuser;
GRANT ALL PRIVILEGES ON DATABASE tasksdb TO tasksuser;
EOF


# ============================================================
# ШАГ 3 — установка Python и зависимостей
# ============================================================

sudo apt install -y python3 python3-pip python3-venv

# создать папку проекта
mkdir -p /var/www/tasks
cd /var/www/tasks

# виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# установить пакеты
pip install fastapi uvicorn sqlalchemy asyncpg psycopg2-binary alembic python-dotenv


# ============================================================
# ШАГ 4 — структура проекта
# ============================================================

# /var/www/tasks/
# ├── venv/
# ├── .env
# ├── main.py
# ├── models.py
# ├── database.py
# ├── schemas.py
# └── static/
#     └── index.html


# ============================================================
# ШАГ 5 — файл .env (заполни своими данными)
# ============================================================

# создай файл /var/www/tasks/.env со следующим содержимым:
# DATABASE_URL=postgresql://tasksuser:замени_на_свой_пароль@localhost/tasksdb
# ALLOWED_ORIGIN=https://твой-домен.ru


# ============================================================
# ШАГ 6 — запуск
# ============================================================

# скопируй все .py файлы и index.html в /var/www/tasks/
# затем:

cd /var/www/tasks
source venv/bin/activate

# создать таблицы (первый раз)
python3 -c "from database import Base, engine; import models; Base.metadata.create_all(engine)"

# тестовый запуск
uvicorn main:app --host 0.0.0.0 --port 8001


# ============================================================
# ШАГ 7 — systemd сервис
# ============================================================

# создай файл /etc/systemd/system/tasks.service:
# (содержимое — в файле tasks.service ниже)

sudo systemctl daemon-reload
sudo systemctl enable tasks
sudo systemctl start tasks
sudo systemctl status tasks


# ============================================================
# ШАГ 8 — nginx
# ============================================================

sudo apt install -y nginx

# создай файл /etc/nginx/sites-available/tasks
# (содержимое — в файле nginx.conf ниже)

sudo ln -s /etc/nginx/sites-available/tasks /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx


# ============================================================
# ШАГ 9 — проверка
# ============================================================

# API документация доступна по адресу:
# http://твой-домен.ru/api/docs

# фронт:
# http://твой-домен.ru/tasks/
