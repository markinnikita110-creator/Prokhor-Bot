"""backup_service.py — автоматическое резервное копирование SQLite.

Логика:
• каждые 12 часов создаёт безопасную копию prokhor.db через sqlite3.backup()
• отправляет файл в приватный Telegram-канал BACKUP_CHANNEL_ID
• после успешной отправки удаляет локальную копию
• при ошибке → подробный лог в консоль + сообщение в канал
• при запуске проверяет, не пропущен ли плановый бэкап (телефон был выключен)

Работает на стороне телефона (UserLAnd); Replit в резервировании не участвует.

Исправленные корректность-критичные проблемы:
  1. Проверка существования и непустоты DB перед backup() — предотвращает
     «успешную» отправку пустой базы при неверном пути.
  2. Блокирующие операции (sqlite3.backup, файловый I/O) вынесены в executor —
     не блокируют event loop aiogram (важно на UserLAnd/Android).
  3. Async-lock предотвращает одновременный запуск двух задач бэкапа.
  4. Файловый дескриптор гарантированно закрывается через try/finally.
  5. Ошибки записи .last_backup перехватываются и логируются.
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

# ── Конфигурация ────────────────────────────────────────────────────────────

DB_PATH           = "prokhor.db"
BACKUP_CHANNEL_ID = -1004498789408
BACKUP_INTERVAL_H = 12
LAST_BACKUP_FILE  = ".last_backup"

log = logging.getLogger(__name__)

# Предотвращает одновременный запуск двух задач бэкапа
_backup_lock = asyncio.Lock()


# ── Вспомогательные функции (синхронные — вызываются через executor) ─────────

def _do_sqlite_backup(src_path: str, dst_path: str) -> None:
    """Копирует БД через sqlite3.backup(). Вызывать только в executor."""
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dst_path)
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()


def _read_last_backup_time() -> datetime | None:
    """Возвращает время последнего успешного бэкапа или None."""
    try:
        text = Path(LAST_BACKUP_FILE).read_text().strip()
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _write_last_backup_time(dt: datetime) -> None:
    """Записывает время успешного бэкапа. Вызывать только в executor."""
    try:
        Path(LAST_BACKUP_FILE).write_text(dt.isoformat())
    except Exception as exc:
        # Не критично: следующий запуск просто сделает бэкап заново
        log.error("BACKUP: не удалось записать .last_backup: %s", exc)


def _needs_immediate_backup() -> bool:
    """True, если с момента последнего бэкапа прошло ≥ 12 часов."""
    last = _read_last_backup_time()
    if last is None:
        return True
    return datetime.utcnow() - last >= timedelta(hours=BACKUP_INTERVAL_H)


# ── Основная функция ─────────────────────────────────────────────────────────

async def create_backup_and_send(bot: Bot) -> None:
    """Создаёт бэкап, отправляет в канал, удаляет локальный файл.

    Защищена async-локом: если предыдущий бэкап ещё выполняется,
    новый вызов тихо пропускается (не встаёт в очередь).
    """
    if _backup_lock.locked():
        log.warning("BACKUP: предыдущий бэкап ещё выполняется — пропуск")
        return

    async with _backup_lock:
        await _run_backup(bot)


async def _run_backup(bot: Bot) -> None:
    loop     = asyncio.get_running_loop()
    now      = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")
    filename = f"backup_{date_str}_{time_str}.db"

    log.info("BACKUP: start → %s", filename)

    # 1. Предварительная проверка: БД должна существовать и быть непустой
    db_path = Path(DB_PATH)
    if not db_path.exists():
        msg = f"❌ BACKUP ERROR: файл базы данных не найден: {DB_PATH!r}"
        log.error("BACKUP: %s", msg)
        await _send_error(bot, msg)
        return
    if db_path.stat().st_size == 0:
        msg = f"❌ BACKUP ERROR: файл базы данных пуст: {DB_PATH!r}"
        log.error("BACKUP: %s", msg)
        await _send_error(bot, msg)
        return

    # 2. Создаём копию через sqlite3.backup() в executor (не блокирует loop)
    try:
        await loop.run_in_executor(None, _do_sqlite_backup, DB_PATH, filename)
    except Exception as exc:
        msg = f"❌ BACKUP ERROR (создание копии): {exc}"
        log.exception("BACKUP: sqlite3.backup() failed")
        _try_delete(filename)
        await _send_error(bot, msg)
        return

    # 3. Получаем размер файла
    try:
        size_bytes = Path(filename).stat().st_size
        size_kb    = size_bytes / 1024
        size_str   = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"
    except Exception:
        size_str = "неизвестно"

    # 4. Формируем подпись
    caption = (
        f"📦 *Автоматический резервный бэкап SQLite*\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время (UTC): {now.strftime('%H:%M')}\n"
        f"💾 Размер: {size_str}"
    )

    # 5. Отправляем файл в канал — дескриптор всегда закрывается
    sent_ok = False
    doc = None
    try:
        doc = open(filename, "rb")
        await bot.send_document(
            chat_id=BACKUP_CHANNEL_ID,
            document=doc,
            caption=caption,
            parse_mode="Markdown",
        )
        sent_ok = True
        log.info("BACKUP: sent to channel %d (%s)", BACKUP_CHANNEL_ID, size_str)
    except Exception as exc:
        msg = f"❌ BACKUP ERROR (отправка файла): {exc}"
        log.exception("BACKUP: send_document failed")
        await _send_error(bot, msg)
    finally:
        if doc is not None:
            doc.close()

    # 6. Удаляем локальную копию (в executor — I/O не блокирует loop)
    await loop.run_in_executor(None, _try_delete, filename)

    # 7. Фиксируем время — только при успешной отправке
    if sent_ok:
        await loop.run_in_executor(None, _write_last_backup_time, now)
        log.info("BACKUP: done ✓ %s", filename)


# ── Вспомогательные утилиты ──────────────────────────────────────────────────

def _try_delete(path: str) -> None:
    """Удаляет файл, игнорируя ошибки (файл мог не создаться)."""
    try:
        os.remove(path)
    except OSError:
        pass


async def _send_error(bot: Bot, text: str) -> None:
    """Отправляет сообщение об ошибке в канал (best-effort)."""
    try:
        await bot.send_message(BACKUP_CHANNEL_ID, text)
    except Exception as inner:
        log.error("BACKUP: не удалось отправить сообщение об ошибке: %s", inner)


# ── Планировщик ──────────────────────────────────────────────────────────────

def start_backup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Запускает APScheduler с задачей каждые 12 часов.

    Если с момента последнего успешного бэкапа прошло ≥ 12 часов (например,
    телефон был выключен), немедленно ставит разовую задачу на «через 5 секунд»,
    чтобы не ждать следующего планового интервала.

    Возвращает запущенный планировщик.
    """
    scheduler = AsyncIOScheduler()

    # Плановый бэкап каждые 12 часов
    scheduler.add_job(
        create_backup_and_send,
        trigger="interval",
        hours=BACKUP_INTERVAL_H,
        id="backup_interval",
        args=[bot],
        replace_existing=True,
    )

    # Проверяем, не пропущен ли бэкап пока бот был выключен
    if _needs_immediate_backup():
        last = _read_last_backup_time()
        if last is None:
            reason = "первый запуск"
        else:
            delta_h = (datetime.utcnow() - last).total_seconds() / 3600
            reason  = f"прошло {delta_h:.1f} ч с последнего бэкапа"
        log.info("BACKUP: требуется немедленный бэкап (%s)", reason)
        scheduler.add_job(
            create_backup_and_send,
            trigger="date",
            run_date=datetime.utcnow() + timedelta(seconds=5),
            id="backup_immediate",
            args=[bot],
            replace_existing=True,
        )

    scheduler.start()
    log.info(
        "BACKUP: планировщик запущен (интервал %d ч, канал %d)",
        BACKUP_INTERVAL_H, BACKUP_CHANNEL_ID,
    )
    return scheduler
