# pyright: reportAny=false
"""dbt-osmosis のロギングモジュール。このモジュール自体は、デフォルトの LOGGER インスタンスへの呼び出しをプロキシするため、ロガーとして使用できます。"""

from __future__ import annotations

import logging
import typing as t
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path

import rich
from rich.logging import RichHandler

_LOG_FILE_FORMAT = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
_LOG_PATH = Path.home().absolute() / ".dbt-osmosis" / "logs"
_LOGGING_LEVEL = logging.INFO


def get_rotating_log_handler(name: str, path: Path, formatter: str) -> RotatingFileHandler:
    """このハンドラは、ホームの.dbt-osmosisディレクトリのログに警告と高レベルの出力を書き込み、
    必要に応じてそれらをローテーションします。"""
    path.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        str(path / f"{name}.log"),
        maxBytes=int(1e6),
        backupCount=3,
    )
    handler.setFormatter(logging.Formatter(formatter))
    handler.setLevel(logging.WARNING)
    return handler


@lru_cache(maxsize=10)
def get_logger(
    name: str = "dbt-osmosis",
    level: t.Union[int, str] = _LOGGING_LEVEL,
    path: Path = _LOG_PATH,
    formatter: str = _LOG_FILE_FORMAT,
) -> logging.Logger:
    """ロガーを構築してキャッシュします。モジュールレベルの属性、または呼び出しごとに設定できます。

    各モジュールで個別のポインタをインスタンス化する必要がなく、ロガー管理が簡素化されます。

    Args:
        name (str, optional): ロガー名。`~/.dbt-osmosis/logs` ディレクトリ内の出力ログファイル名にも使用されます。
        level (Union[int, str], optional): ログレベル。コンソールハンドラーに明示的に渡され、コンソールに出力されるログメッセージのレベルを決定します。デフォルトはlogging.INFOです。
        path (Path, optional): 警告レベル+のログファイルを出力するパス。デフォルトは `~/.dbt-osmosis/logs` です。
        formatter (str, optional): 出力ログファイルの形式。デフォルトは "time — name — level — message" 形式です。

    Returns:
        logging.Logger: ログのローテーションとコンソールストリーミングを備えたロガーを用意しました。関数から直接実行できます。
    """
    if isinstance(level, str):
        level = getattr(logging, level, logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(get_rotating_log_handler(name, path, formatter))
    logger.addHandler(
        RichHandler(
            level=level,
            console=rich.console.Console(stderr=True),
            rich_tracebacks=True,
            markup=True,
            show_time=False,
        )
    )
    logger.propagate = False
    return logger


LOGGER = get_logger()
"""dbt-osmosis のデフォルトロガー"""


def set_log_level(level: t.Union[int, str]) -> None:
    """デフォルトのロガーのログレベルを設定する"""
    global LOGGER
    if isinstance(level, str):
        level = getattr(logging, level, logging.INFO)
    LOGGER.setLevel(level)
    for handler in LOGGER.handlers:
        # NOTE: RotatingFileHandler is fixed at WARNING level.
        if isinstance(handler, RichHandler):
            handler.setLevel(level)


class LogMethod(t.Protocol):
    """ロガーメソッドのプロトコル"""

    def __call__(self, msg: t.Any, /, *args: t.Any, **kwds: t.Any) -> t.Any: ...


def __getattr__(name: str) -> LogMethod:
    if name == "set_log_level":
        return set_log_level
    func = getattr(LOGGER, name)
    return func
