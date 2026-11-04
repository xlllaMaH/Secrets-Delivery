# Secret Delivery

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?style=flat&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-migrations-6BA81E?style=flat)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat&logo=pydantic&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)
![AES-256-GCM](https://img.shields.io/badge/AES--256--GCM-encryption-4B5563?style=flat)
![Argon2](https://img.shields.io/badge/Argon2id-passwords-7C3AED?style=flat)

API-сервис для безопасной передачи секретов (паролей, ключей, текста) по одноразовым ссылкам. Секрет шифруется, открывается ограниченное число раз и сам удаляется.

> Сейчас готов бэкенд (REST API). Что планируется дальше, смотрите в разделе «Планы развития».
>
> **Важно:** пока нет ограничения частоты запросов (rate limit), не выставляйте сервис в интернет без прокси (например, nginx) с таким ограничением.

## Содержание

- [Как это работает](#как-это-работает)
- [Структура проекта](#структура-проекта)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Запуск для разработки](#запуск-для-разработки)
- [Настройки (.env)](#настройки-env)
- [API](#api)
- [Тесты и проверки](#тесты-и-проверки)
- [Планы развития](#планы-развития)

## Как это работает

1. Зарегистрированный пользователь создаёт секрет и получает `token` и `key`.
2. Из них собирается ссылка вида `https://<сайт>/s/<token>#<key>`. Часть после `#` браузер на сервер не отправляет.
3. Получатель открывает ссылку без регистрации, клиент отправляет ключ в теле запроса `POST /notes/{token}/reveal`.
4. Секрет расшифровывается и показывается. Когда просмотры закончились или истёк срок, содержимое удаляется, а запись остаётся в архиве кабинета.

Что важно для безопасности:
- Шифрование AES-256-GCM. Ключ случайный на каждый секрет и **нигде не хранится на сервере**: текст секрета лежит в базе только в зашифрованном виде, и без ссылки его не прочитать даже с доступом к базе. Название, срок и число просмотров хранятся открыто, поэтому не пишите секреты в название.
- Неверный ключ, несуществующий токен и сгоревший секрет дают один и тот же ответ `404`, по нему нельзя понять, существует ли секрет.
- Пароли пользователей хранятся как Argon2id. Вход через JWT: access-токен живёт 15 минут, refresh-токены обновляются с ротацией и защитой от повторного использования.
- Просмотры владельца не сжигают секрет, а в личном кабинете содержимое не показывается, только метаданные.

## Структура проекта

```
secret_delivery/
├── src/
│   ├── main.py             приложение и роутеры
│   ├── config.py           настройки из .env
│   ├── database.py         подключение к базе
│   ├── auth/               регистрация, вход, токены
│   ├── users/              пользователи
│   ├── notes/              секреты и личный кабинет
│   ├── crypto/             пароли (Argon2) и шифрование (AES-GCM)
│   ├── cleanup/            команда очистки
│   └── health/             проверка здоровья
├── alembic/                миграции
├── tests/                  тесты
├── Dockerfile              образ приложения
├── docker-compose.yml      запуск всех сервисов
└── .env.example            шаблон настроек
```

Слои: `router` (HTTP) → `service` (логика) → `models` и `crypto`.

## Быстрый старт (Docker)

Нужны Docker и Docker Compose.

```bash
git clone https://github.com/xlllaMaH/Secrets-Delivery.git
cd Secrets-Delivery
cp .env.example .env
```

Откройте `.env` и заполните:
- `POSTGRES_PASSWORD`: пароль базы (только буквы, цифры, `-` и `_`);
- `JWT_SECRET`: длинная случайная строка, не короче 32 символов:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  # или, если Python нет:
  openssl rand -base64 48
  ```

Запуск:

```bash
docker compose up -d
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

Что поднимается:

| Сервис | Назначение |
|---|---|
| `db` | PostgreSQL 16, данные хранятся в томе `pgdata` |
| `migrate` | применяет миграции и завершается |
| `app` | API на `127.0.0.1:8000` (порт меняется через `APP_PORT`) |
| `cleanup` | раз в час удаляет просроченные данные |

Остановить: `docker compose down` (с флагом `-v` удалятся и данные базы).

## Запуск для разработки

Нужны Python 3.12, uv и PostgreSQL.

1. Создайте базы `delivery_db` и `delivery_test` и отдельного пользователя.
2. `cp .env.example .env`, заполните `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET`. Для Swagger поставьте `DOCS_ENABLED=true`.
3. Установите зависимости, примените миграции, запустите:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs` (если `DOCS_ENABLED=true`).

Чистка просроченных данных вручную: `uv run python -m src.cleanup`.

## Настройки (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | нет | Строка подключения к базе (`postgresql+asyncpg://...`) |
| `TEST_DATABASE_URL` | нет | Отдельная база для тестов |
| `JWT_SECRET` | нет | Секрет подписи токенов, не короче 32 символов |
| `JWT_ALGORITHM` | `HS256` | `HS256`, `HS384` или `HS512` |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | Срок жизни access-токена |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Срок жизни refresh-токена |
| `HASH_CONCURRENCY` | `4` | Сколько паролей хешируется параллельно (на один процесс) |
| `DOCS_ENABLED` | `false` | Включает `/docs`, `/redoc`, `/openapi.json` (только для разработки) |
| `CORS_ORIGINS` | пусто | Разрешённые адреса сайтов через запятую; `*` запрещена, пусто означает CORS выключен |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | нет | Для Docker Compose |
| `APP_PORT` | `8000` | Порт приложения на вашем компьютере (Docker) |

Приложение не запустится с неверными значениями (короткий секрет, нулевые сроки, неизвестный алгоритм) и назовёт проблемную переменную.

## API

Пробовать запросы удобнее всего в Swagger: включите `DOCS_ENABLED=true` и откройте `/docs`.

| Метод и путь | Назначение |
|---|---|
| `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` | Регистрация, вход, обновление токенов, выход |
| `GET /users/me` | Текущий пользователь |
| `POST /notes` | Создать секрет (нужен вход) |
| `POST /notes/{token}/reveal` | Открыть секрет по ссылке |
| `GET /notes?status=active\|archive` | Мои секреты (`limit`, `offset` для страниц) |
| `GET /notes/{id}` | Карточка секрета без содержимого |
| `POST /notes/{id}/archive` | Отозвать ссылку (секрет уходит в архив) |
| `GET /health` | Проверка работы и доступности базы |

Параметры секрета: текст до 10 000 символов, срок от 1 до 720 часов (по умолчанию 24), число просмотров от 1 до 100 (по умолчанию 1).

## Тесты и проверки

Нужна база из `TEST_DATABASE_URL`.

```bash
uv run pytest -v
uv run ruff check src tests
uv run ruff format --check src tests
```

## Планы развития

**Ближайшее** 🔜
- **Защита от перебора**: ограничение частоты запросов (rate limit) на вход и открытие секретов
- **Автоматическая сборка**: проверки на GitHub Actions и публикация образа в Docker Hub
- **Веб-интерфейс**: создание секретов и открытие по ссылке

**Позже** 🕒
- **Файлы**: передача PDF и Word, хранилище S3
- **Адресная отправка**: секрет конкретному пользователю
- **Почта**: подтверждение адреса и уведомления
- **Вход через Google**: авторизация по OAuth 2.0
- **Сессии на куки** вместо Bearer-токена
