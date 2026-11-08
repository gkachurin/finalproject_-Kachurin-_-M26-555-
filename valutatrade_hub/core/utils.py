import math
from datetime import datetime

EXCHANGE_RATES = {
    "EUR_USD": 1.08,
    "BTC_USD": 59337.21,
    "RUB_USD": 0.01016,
    "ETH_USD": 3720.00,
}


def validate_currency_code(currency_code: str) -> str:
    """Проверяет и нормализует код валюты."""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты не может быть пустым")

    currency_code = currency_code.strip().upper()

    if not currency_code.isalpha():
        raise ValueError("Некорректный код валюты")

    return currency_code


def validate_amount(amount: float) -> float:
    """Проверяет положительную денежную сумму."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("'amount' должен быть положительным числом")

    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    return float(amount)


def get_exchange_rate(
    from_currency: str,
    to_currency: str,
) -> tuple[float, datetime]:
    """Возвращает курс одной валюты к другой и время получения."""
    from_code = validate_currency_code(from_currency)
    to_code = validate_currency_code(to_currency)

    if from_code == to_code:
        return 1.0, datetime.now()

    direct_key = f"{from_code}_{to_code}"
    reverse_key = f"{to_code}_{from_code}"

    if direct_key in EXCHANGE_RATES:
        return EXCHANGE_RATES[direct_key], datetime.now()

    if reverse_key in EXCHANGE_RATES:
        return 1 / EXCHANGE_RATES[reverse_key], datetime.now()

    # Попытка конвертации через USD.
    from_usd = EXCHANGE_RATES.get(f"{from_code}_USD")
    to_usd = EXCHANGE_RATES.get(f"{to_code}_USD")

    if from_usd is not None and to_usd is not None:
        return from_usd / to_usd, datetime.now()

    raise ValueError(f"Не удалось получить курс для {from_code}→{to_code}")
