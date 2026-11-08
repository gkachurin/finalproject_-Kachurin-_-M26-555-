# ValutaTrade Hub

Консольная платформа для симуляции торговли валютами.

Проект состоит из двух частей:

- **Core Service** — CLI, пользователи, кошельки, сделки, история действий.
- **Parser Service** — отдельный модуль, который собирает курсы из публичных API
  (CoinGecko для криптовалют, ExchangeRate-API для фиата) и сохраняет их в локальный
  кеш `data/rates.json` и историю `data/exchange_rates.json`.

## Демонстрация

[asciicast]  https://asciinema.org/a/7Y8PIP34SRSdGtR0 или asciinema play final_project.cast

## Структура проекта

finalproject_-Kachurin-_-M26-555-/
├── data/
│   ├── users.json             # пользователи
│   ├── portfolios.json        # портфели и кошельки
│   ├── rates.json             # кеш актуальных курсов (читает Core Service)
│   └── exchange_rates.json    # история измерений (пишет Parser Service)
├── logs/                      # actions.log, parser.log (создаются автоматически)
├── valutatrade_hub/
│   ├── logging_config.py      # настройка логов и ротации
│   ├── decorators.py          # @log_action
│   ├── core/
│   │   ├── currencies.py      # Currency, FiatCurrency, CryptoCurrency, реестр
│   │   ├── exceptions.py      # доменные исключения
│   │   ├── models.py          # User, Wallet, Portfolio
│   │   ├── usecases.py        # бизнес-логика
│   │   └── utils.py           # валидация кодов и сумм
│   ├── infra/
│   │   ├── settings.py        # Singleton SettingsLoader
│   │   └── database.py        # Singleton DatabaseManager (JSON, атомарная запись)
│   ├── parser_service/
│   │   ├── config.py          # ParserConfig
│   │   ├── api_clients.py     # CoinGeckoClient, ExchangeRateApiClient
│   │   ├── updater.py         # RatesUpdater
│   │   ├── storage.py         # запись rates.json и exchange_rates.json
│   │   └── scheduler.py       # периодическое обновление
│   └── cli/
│       └── interface.py       # команды
├── main.py
├── pyproject.toml
└── uv.lock

## Установка

Требуется Python 3.12+ и uv.

git clone https://github.com/gkachurin/finalproject_-Kachurin-_-M26-555-
cd ffinalproject_-Kachurin-_-M26-555-
uv sync

## Ключ ExchangeRate-API

Курсы фиатных валют берутся из [ExchangeRate-API](https://www.exchangerate-api.com/).
Ключ **не хранится в репозитории**, он читается из переменной окружения:

export EXCHANGERATE_API_KEY=ваш_ключ

Без ключа обновятся только криптовалюты (CoinGecko работает без ключа), а фиатные
курсы будут недоступны. Переменная действует только в текущем терминале, поэтому
задавайте её в том же окне, где запускаете приложение.

## Запуск

uv run main.py

## Команды

| Команда | Описание |
|
| `register --username <имя> --password <пароль>` | регистрация (пароль не короче 4 символов) |
| `login --username <имя> --password <пароль>` | вход |
| `deposit --amount <число>` | пополнение USD-кошелька (симуляция ввода средств) |
| `buy --currency <код> --amount <число>` | покупка валюты за USD |
| `sell --currency <код> --amount <число>` | продажа валюты за USD |
| `show-portfolio [--base <код>]` | портфель и стоимость в базовой валюте (по умолчанию USD) |
| `get-rate --from <код> --to <код>` | курс пары и обратный курс |
| `update-rates [--source coingecko\|exchangerate]` | обновить курсы через Parser Service |
| `show-rates [--currency <код>] [--top <N>] [--base <код>]` | курсы из локального кеша |

Поддерживаемые валюты: `USD, EUR, GBP, RUB, BTC, ETH, SOL`.

### Примеры

```
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=5). Войдите: login --username alice --password ****

> login --username alice --password 1234
Вы вошли как 'alice'

> deposit --amount 10000
Пополнение выполнено: +10,000.00 USD
- USD: было 0.00 → стало 10,000.00

> buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 75,966.00 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 3,798.30 USD

> sell --currency BTC --amount 0.01
Продажа выполнена: 0.0100 BTC по курсу 75,966.00 USD/BTC
Изменения в портфеле:
- BTC: было 0.0500 → стало 0.0400
Оценочная выручка: 759.66 USD

> show-portfolio --base EUR
Портфель пользователя 'alice' (база: EUR):
+--------+-----------+-----------------+
| Валюта |   Баланс  | Стоимость в EUR |
+--------+-----------+-----------------+
|  BTC   |   0.0400  |     2,722.01    |
|  USD   | 6,961.36  |     6,236.48    |
| ИТОГО  |           |     8,958.49    |
+--------+-----------+-----------------+

> get-rate --from USD --to BTC
Курс USD→BTC: 0.00001316 (обновлено: 2026-11-08 16:12:40)
Обратный курс BTC→USD: 75,966.00

> update-rates
Обновление успешно. Обновлено курсов: 6. Последнее обновление: 2026-11-08T17:16:01Z

> show-rates --top 2
Курсы из кеша (обновлено: 2026-11-08T17:16:02Z):
+---------+-----------+---------------------+
|   Пара  |    Курс   |      Обновлено      |
+---------+-----------+---------------------+
| BTC_USD | 75,644.00 | 2026-11-08 17:16:01 |
| ETH_USD |  2,224.69 | 2026-11-08 17:16:01 |
+---------+-----------+---------------------+
```

### Ошибки

```
> sell --currency BTC --amount 100
Недостаточно средств: доступно 0.0400 BTC, требуется 100.0000 BTC

> buy --currency XYZ --amount 1
Неизвестная валюта 'XYZ'. Поддерживаемые коды: USD, EUR, RUB, BTC, ETH, SOL, GBP. ...

> buy --currency BTC --amount -5
'amount' должен быть положительным числом

> show-rates --currency ABC
Курс для 'ABC' не найден в кеше.
```

## Кеш курсов и TTL

Core Service читает курсы только из `data/rates.json`. У каждой пары есть время
обновления `updated_at`. Время жизни кеша (TTL) задаётся настройкой `rates_ttl`
(по умолчанию **300 секунд**).

При запросе курса (`get-rate`, `buy`, `sell`, `show-portfolio`):

1. Если курс в кеше моложе TTL — он используется сразу.
2. Если курс устарел или отсутствует — запускается Parser Service и кеш обновляется.
3. Если обновить не удалось — выводится сообщение о недоступности курса.

Курсы между валютами, для которых нет прямой пары, считаются через USD
(например, `EUR → RUB = EUR_USD / RUB_USD`).

## Parser Service

Парсер получает курсы из двух источников и приводит их к единому формату:

- **CoinGecko** — BTC, ETH, SOL (без ключа);
- **ExchangeRate-API** — EUR, GBP, RUB (нужен `EXCHANGERATE_API_KEY`).

Сбой одного источника не останавливает обновление: курсы из второго всё равно
сохраняются, а ошибка записывается в `logs/parser.log`.

Данные пишутся атомарно. Результат:

- `data/rates.json` — последний курс каждой пары;
- `data/exchange_rates.json` — история всех измерений (`id` вида
  `BTC_USD_2026-11-08T17:16:01Z`).

**Ручное обновление:**

> update-rates
> update-rates --source coingecko

## Конфигурация

Настройки находятся в секции `[tool.valutatrade]` файла `pyproject.toml`
и читаются через Singleton `SettingsLoader`:

| Ключ | Назначение | По умолчанию |
|
| `users_file`, `portfolios_file` | пути к данным пользователей | `data/...` |
| `rates_file`, `history_file` | кеш и история курсов | `data/...` |
| `rates_ttl` | время жизни кеша, секунды | `300` |
| `default_base_currency` | базовая валюта | `USD` |
| `log_file`, `parser_log_file` | пути к логам | `logs/...` |
| `log_level`, `log_format` | уровень и формат (`text` или `json`) | `INFO`, `text` |
| `log_max_bytes`, `log_backup_count` | ротация логов | `1048576`, `3` |

Параметры API (URL, списки валют, таймаут) лежат в `parser_service/config.py`.

## Логирование

Операции `register`, `login`, `deposit`, `buy`, `sell` пишутся в `logs/actions.log`
декоратором `@log_action` (с ротацией файлов):

```
2026-11-08 17:20:11 | INFO | BUY user='alice' currency='BTC' amount=0.05 rate=75966.0 base='USD' result=OK
```

Исключения не подавляются: они фиксируются в логе и пробрасываются дальше,
в CLI показываются дружелюбные сообщения. Работа парсера пишется в `logs/parser.log`.

## Архитектурные решения

- **Слои:** CLI только разбирает команды и выводит текст, вся логика в `core/usecases.py`.
- **Модели:** `User` (соль + SHA-256), `Wallet` (валидируемый `balance`), `Portfolio`.
- **Валюты:** абстрактный `Currency` и наследники `FiatCurrency`, `CryptoCurrency`.
- **Исключения:** `InsufficientFundsError`, `CurrencyNotFoundError`, `ApiRequestError`.
- **Singleton:** `SettingsLoader`, `DatabaseManager`.

## Разработка

uv sync
uv run ruff check
uv run ruff format