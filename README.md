# Trend Aggregator Bot

Telegram-бот для автоматического сбора зарубежных трендов из США, Европы, Кореи, Японии и Китая с переводом на русский язык через AI.

## Архитектура

```
project/
├── app/
│   ├── bot/            # Telegram бот (aiogram 3.x)
│   ├── handlers/       # Обработчики команд и колбэков
│   ├── keyboards/      # Inline-клавиатуры
│   ├── services/
│   │   ├── ai/         # Промпты для OpenAI
│   │   ├── ai_processor.py  # AI обработка (OpenAI GPT-4o)
│   │   └── translator.py    # Fallback переводчик
│   ├── parsers/        # RSS и Reddit парсеры
│   ├── database/       # SQLAlchemy модели, CRUD, сессия
│   ├── scheduler/      # APScheduler планировщик
│   ├── middlewares/    # Middleware логирования
│   ├── utils/          # Logger, Cache
│   └── config.py       # Pydantic конфигурация
├── main.py             # Точка входа
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Источники

### RSS
- **США/Европа:** Allure, Vogue, Cosmopolitan, Refinery29, WWD, Byrdie
- **Корея:** Naver Beauty, Beauty Korea, K-Beauty RSS
- **Япония:** Fashion Press Japan, Fashionsnap
- **Китай:** Sina Fashion, Sohu Fashion

### Reddit
- r/beauty, r/AsianBeauty, r/SkincareAddiction, r/FemaleFashionAdvice, r/Kbeauty, r/Makeup, r/HaircareScience, r/Fashion

## Pipeline обработки

1. **Сбор** — RSS + Reddit (каждые 30 мин)
2. **Дедупликация** — по URL
3. **AI обработка** (GPT-4o):
   - Определение языка и перевод на русский
   - Генерация заголовка на русском
   - AI-резюме (3-5 предложений)
   - Определение категории (Beauty, Fashion, Lifestyle, Trends, K/J/C-Beauty)
4. **Публикация** — авто-отправка в Telegram канал (каждые 10 мин)

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/next` | Следующая неопубликованная статья |
| `/stats` | Статистика (админ) |
| `/sources` | Статистика по источникам (админ) |
| `/force_fetch` | Принудительный сбор трендов (админ) |
| `/broadcast` | Массовая рассылка (админ) |

## Быстрый запуск (локально)

```bash
# 1. Клонировать
git clone <repo> && cd trend-aggregator-bot

# 2. Настроить .env
cp .env.example .env
# Заполнить BOT_TOKEN и OPENAI_API_KEY

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить
python main.py
```

## Запуск через Docker

```bash
docker-compose up -d --build
```

### BotHost

1. Загрузите код на сервер
2. Установите переменные окружения через панель BotHost:
   - `BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `DATABASE_URL` (PostgreSQL от BotHost)
   - `OWNER_ID` (ваш Telegram ID)
3. Убедитесь, что `DATABASE_URL` указывает на PostgreSQL BotHost
4. Запустите бота

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|------------|-------------|-------------|----------|
| BOT_TOKEN | Да | — | Токен Telegram бота |
| OPENAI_API_KEY | Да | — | Ключ OpenAI API |
| DATABASE_URL | Нет | sqlite+aiosqlite:///./data/trends.db | URL базы данных |
| OWNER_ID | Нет | 0 | Telegram ID администратора |
| CHANNEL_ID | Нет | — | ID канала для публикации |
| FETCH_INTERVAL_MINUTES | Нет | 30 | Интервал сбора трендов |
| PUBLISH_INTERVAL_MINUTES | Нет | 10 | Интервал публикации |
| LOG_LEVEL | Нет | DEBUG | Уровень логирования |
