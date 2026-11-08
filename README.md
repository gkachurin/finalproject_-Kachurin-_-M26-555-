# ValutaTrade Hub

Консольная платформа для симуляции торговли валютами.

Проект состоит из двух частей:

- **Core Service** — CLI, пользователи, кошельки, сделки, история действий.
- **Parser Service** — отдельный модуль, который собирает курсы из публичных API (CoinGecko для криптовалют, ExchangeRate-API для фиата) и сохраняет их в локальный кеш `data/rates.json` и историю `data/exchange_rates.json`.

## Демонстрация

Запись демонстрации работы приложения:

[Asciinema](https://asciinema.org/a/7Y8PIP34SRSdGtR0)

Локальное воспроизведение:

```bash
asciinema play final_project.cast
```

## Структура проекта

```text
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
├── Makefile                   # команды запуска и проверки проекта
├── pyproject.toml             # настройки проекта и зависимости
├── README.md                  # документация
└── uv.lock                    # зафиксированные версии зависимостей
```

## Установка

Требуется Python 3.12+ и uv.

```bash
git clone https://github.com/gkachurin/finalproject_-Kachurin-_-M26-555-.git
cd finalproject_-Kachurin-_-M26-555-
uv sync
```

## Ключ ExchangeRate-API

Курсы фиатных валют берутся из [ExchangeRate-API](https://www.exchangerate-api.com/).

Ключ **не хранится в репозитории**, он читается из переменной окружения:

```bash
export EXCHANGERATE_API_KEY=ваш_ключ
```

Без ключа обновятся только криптовалюты (CoinGecko работает без ключа), а фиатные курсы будут недоступны. Переменная действует только в текущем терминале, поэтому задавайте её в том же окне, где запускаете приложение.

## Запуск

Из корневой директории проекта:

```bash
uv run main.py
```

Или через Makefile:

```bash
make run
```

## Команды

| Команда | Описание |
|---|---|
| `register --username <имя> --password <пароль>` | Регистрация (пароль не короче 4 символов) |
| `login --username <имя> --password <пароль>` | Вход |
| `deposit --amount <число>` | Пополнение USD-кошелька (симуляция ввода средств) |
| `buy --currency <код> --amount <число>` | Покупка валюты за USD |
| `sell --currency <код> --amount <число>` | Продажа валюты за USD |
| `show-portfolio [--base <код>]` | Портфель и стоимость в базовой валюте (по умолчанию USD) |
| `get-rate --from <код> --to <код>` | Курс пары и обратный курс |
| `update-rates [--source coingecko\|exchangerate]` | Обновить курсы через Parser Service |
| `show-rates [--currency <код>] [--top <N>] [--base <код>]` | Курсы из локального кеша |

Поддерживаемые валюты: `USD, EUR, GBP, RUB, BTC, ETH, SOL`.

### Примеры

```text
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