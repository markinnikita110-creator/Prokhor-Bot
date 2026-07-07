"""Cohort checkins service layer.

Contains scenario functions that span multiple DB steps and interact with
Telegram (sending messages). CRUD primitives live in
core.db.cohort_checkins_repository; ownership verification in
core.db.cohorts_repository.
"""

import logging

log = logging.getLogger(__name__)


async def send_checkin_to_members(
    bot,
    cohort_id: int,
    members: list,
    question: str,
    make_keyboard,
) -> int:
    """Send the check-in question to every active member.

    Args:
        bot: aiogram Bot instance.
        cohort_id: used only for keyboard callback data.
        members: list of (id, telegram_id, name) rows from get_active_members.
        question: the question text to send.
        make_keyboard: callable(cohort_id, member_tg) -> InlineKeyboardMarkup.

    Returns:
        Number of successfully delivered messages.
    """
    sent = 0
    for _, member_tg, _ in members:
        try:
            kb = make_keyboard(cohort_id, member_tg)
            await bot.send_message(member_tg, question, reply_markup=kb)
            sent += 1
        except Exception as exc:
            log.warning(
                "COHORT_CHECKIN: send fail cohort_id=%d member_tg=%d: %s",
                cohort_id, member_tg, exc,
            )
    log.info(
        "COHORT_CHECKIN: checkin sent cohort_id=%d sent=%d/%d",
        cohort_id, sent, len(members),
    )
    return sent


async def broadcast_to_members(
    bot,
    cohort_id: int,
    members: list,
    text: str,
) -> int:
    """Broadcast a plain-text message to every active member.

    Args:
        bot: aiogram Bot instance.
        cohort_id: used only for logging.
        members: list of (id, telegram_id, name) rows from get_active_members.
        text: message text to send.

    Returns:
        Number of successfully delivered messages.
    """
    sent = 0
    for _, member_tg, _ in members:
        try:
            await bot.send_message(member_tg, text)
            sent += 1
        except Exception as exc:
            log.warning(
                "COHORT_CHECKIN: broadcast fail cohort_id=%d member_tg=%d: %s",
                cohort_id, member_tg, exc,
            )
    log.info(
        "COHORT_CHECKIN: broadcast cohort_id=%d sent=%d/%d",
        cohort_id, sent, len(members),
    )
    return sent
