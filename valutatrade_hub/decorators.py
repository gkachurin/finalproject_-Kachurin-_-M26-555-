"""Декораторы для логирования действий."""

import functools
import inspect
from contextvars import ContextVar
from typing import Any, Callable

from valutatrade_hub.logging_config import logger

SENSITIVE_ARGS = {"password", "new_password"}
_log_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "log_context", default=None
)


def set_log_context(**values: Any) -> None:
    """Добавляет в запись лога данные, известные только внутри usecase."""
    context = _log_context.get()
    if context is not None:
        context.update(values)


def _log(action, func, arguments, context, verbose, error=None) -> None:
    user = func.__globals__.get("current_user")
    username = user.username if user else arguments.get("username")
    result = "OK" if error is None else "ERROR"

    fields = {
        "user": username,
        "currency": arguments.get("currency_code"),
        "amount": arguments.get("amount"),
        "rate": context.get("rate"),
        "base": context.get("base"),
    }
    text = " ".join(
        [action]
        + [f"{key}={value!r}" for key, value in fields.items() if value is not None]
        + [f"result={result}"]
    )
    if error is not None:
        text += f" error_type={type(error).__name__} error_message={str(error)!r}"
    if verbose:
        safe = {
            key: value
            for key, value in {**arguments, **context}.items()
            if key not in SENSITIVE_ARGS
        }
        text += f" context={safe}"

    extra = {
        "action": action,
        "username": username,
        "user_id": user.user_id if user else None,
        "currency": fields["currency"],
        "amount": fields["amount"],
        "rate": fields["rate"],
        "result": result,
    }
    if error is None:
        logger.info(text, extra=extra)
    else:
        logger.error(text, extra=extra, exc_info=not isinstance(error, ValueError))


def log_action(action_name: str, verbose: bool = False) -> Callable:
    """Логирует операцию (INFO/ERROR), не глотая исключения."""

    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)
        action = action_name.upper()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            arguments = dict(signature.bind_partial(*args, **kwargs).arguments)
            context: dict[str, Any] = {}
            token = _log_context.set(context)
            try:
                result = func(*args, **kwargs)
            except Exception as error:
                _log(action, func, arguments, context, verbose, error)
                raise
            else:
                _log(action, func, arguments, context, verbose)
                return result
            finally:
                _log_context.reset(token)

        return wrapper

    return decorator
