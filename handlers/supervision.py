"""COHORT_V2: Supervision case logbook — create, list, progress, close."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from core.db.supervision_repository import (
    close_supervision_case,
    get_supervision_logbook,
    get_supervision_open_cases,
    insert_supervision_case,
)
from database import get_user_lang, get_user_timezone, now_str, to_user_tz
from keyboards import cancel_keyboard
from states.supervision_states import SupervisionCaseForm
from translations import t

router = Router()
log = logging.getLogger(__name__)


# ══ /supervision_case — FSM wizard ════════════════════════════════════════

@router.message(Command("supervision_case"))
async def sup_case_start(message: Message, state: FSMContext):
    """COHORT_V2: Step 1 — show anonymization warning, then ask for client alias."""
    from plan_limits import get_user_plan
    lang = await get_user_lang(message.from_user.id)
    plan = await get_user_plan(message.from_user.id)
    if not plan.get("supervision"):
        msg = ("⚠️ Супервизия доступна только на тарифе Pro.\nВведите промокод: /promo"
               if lang == "ru" else
               "⚠️ Supervision is available on the Pro plan only.\nEnter a promo code: /promo")
        await message.answer(msg)
        return
    await state.set_state(SupervisionCaseForm.client_alias)
    await message.answer(t(lang, "sup_anonymize_warning"))
    await message.answer(t(lang, "sup_case_alias"), reply_markup=cancel_keyboard(lang))
    log.info("COHORT_V2: supervision case started by user_id=%d", message.from_user.id)


@router.message(SupervisionCaseForm.client_alias)
async def sup_got_alias(message: Message, state: FSMContext):
    """COHORT_V2: Step 2 — save alias, ask presenting issue."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(client_alias=message.text.strip())
    await state.set_state(SupervisionCaseForm.presenting_issue)
    await message.answer(t(lang, "sup_case_issue"), reply_markup=cancel_keyboard(lang))


@router.message(SupervisionCaseForm.presenting_issue)
async def sup_got_issue(message: Message, state: FSMContext):
    """COHORT_V2: Step 3 — save issue, ask hypothesis."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(presenting_issue=message.text.strip())
    await state.set_state(SupervisionCaseForm.hypothesis)
    await message.answer(t(lang, "sup_case_hypothesis"), reply_markup=cancel_keyboard(lang))


@router.message(SupervisionCaseForm.hypothesis)
async def sup_got_hypothesis(message: Message, state: FSMContext):
    """COHORT_V2: Step 4 — save hypothesis, ask intervention."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(hypothesis=message.text.strip())
    await state.set_state(SupervisionCaseForm.intervention)
    await message.answer(t(lang, "sup_case_intervention"), reply_markup=cancel_keyboard(lang))


@router.message(SupervisionCaseForm.intervention)
async def sup_got_intervention(message: Message, state: FSMContext):
    """COHORT_V2: Step 5 — save intervention, ask expected outcome."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(intervention=message.text.strip())
    await state.set_state(SupervisionCaseForm.outcome)
    await message.answer(t(lang, "sup_case_outcome"), reply_markup=cancel_keyboard(lang))


@router.message(SupervisionCaseForm.outcome)
async def sup_got_outcome(message: Message, state: FSMContext):
    """COHORT_V2: Final step — save case to DB."""
    lang = await get_user_lang(message.from_user.id)
    uid = message.from_user.id
    data = await state.get_data()
    await state.clear()

    ts = now_str()
    case_id = await insert_supervision_case(
        psychologist_id=uid,
        client_alias=data.get("client_alias", ""),
        presenting_issue=data.get("presenting_issue", ""),
        hypothesis=data.get("hypothesis", ""),
        intervention=data.get("intervention", ""),
        outcome=message.text.strip(),
        created_at=ts,
    )

    await message.answer(t(lang, "sup_case_saved", alias=data.get("client_alias", "")))
    log.info("COHORT_V2: supervision case_id=%d created by user_id=%d", case_id, uid)


# ══ /supervision_logbook — list all cases ═════════════════════════════════

@router.message(Command("supervision_logbook"))
async def sup_logbook(message: Message):
    """COHORT_V2: Show all supervision cases for this psychologist."""
    from plan_limits import get_user_plan
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    plan = await get_user_plan(uid)
    if not plan.get("supervision"):
        msg = ("⚠️ Супервизия доступна только на тарифе Pro.\nВведите промокод: /promo"
               if lang == "ru" else
               "⚠️ Supervision is available on the Pro plan only.\nEnter a promo code: /promo")
        await message.answer(msg)
        return

    cases = await get_supervision_logbook(uid)

    if not cases:
        await message.answer(t(lang, "sup_logbook_empty"))
        return

    tz_name, _ = await get_user_timezone(uid)
    lines = [t(lang, "sup_logbook_title", count=len(cases))]
    for case_id, alias, status, created_at in cases:
        date_str = to_user_tz(created_at, tz_name, "%d.%m.%Y") if created_at else "?"
        lines.append(t(lang, "sup_logbook_row", id=case_id, alias=alias,
                       status=status, date=date_str))
    await message.answer("\n".join(lines))
    log.info("COHORT_V2: supervision logbook shown to user_id=%d count=%d", uid, len(cases))


# ══ /supervision_progress — open cases with full detail ═══════════════════

@router.message(Command("supervision_progress"))
async def sup_progress(message: Message):
    """COHORT_V2: Show open supervision cases with full detail + close button."""
    from plan_limits import get_user_plan
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    plan = await get_user_plan(uid)
    if not plan.get("supervision"):
        msg = ("⚠️ Супервизия доступна только на тарифе Pro.\nВведите промокод: /promo"
               if lang == "ru" else
               "⚠️ Supervision is available on the Pro plan only.\nEnter a promo code: /promo")
        await message.answer(msg)
        return

    cases = await get_supervision_open_cases(uid)

    if not cases:
        await message.answer(t(lang, "sup_progress_empty"))
        return

    await message.answer(t(lang, "sup_progress_title"))
    for case_id, alias, issue, hyp, interv, outcome in cases:
        text = t(lang, "sup_progress_row",
                 id=case_id, alias=alias, issue=issue or "—",
                 hyp=hyp or "—", interv=interv or "—", outcome=outcome or "—")
        close_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(lang, "sup_close_btn"),
                callback_data=f"sv_close_{case_id}",
            )
        ]])
        await message.answer(text, reply_markup=close_kb)
    log.info("COHORT_V2: supervision progress shown to user_id=%d open=%d", uid, len(cases))


# ══ Close supervision case callback ═══════════════════════════════════════

@router.callback_query(F.data.startswith("sv_close_"))
async def sup_close_case(callback: CallbackQuery):
    """COHORT_V2: Mark a supervision case as closed."""
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    case_id = int(callback.data[len("sv_close_"):])

    closed = await close_supervision_case(case_id, uid, now_str())
    if not closed:
        await callback.answer(t(lang, "sup_case_not_found"), show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t(lang, "sup_case_closed", id=case_id))
    log.info("COHORT_V2: supervision case_id=%d closed by user_id=%d", case_id, uid)
