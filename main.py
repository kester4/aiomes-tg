import os
import asyncio
import logging
from datetime import date, timedelta, datetime as dt

import aiomes
from aiomes.errors import *
from aiomes.user_auth import AUTH_URL

from playwright.async_api import async_playwright
from playwright._impl._errors import TimeoutError as TE
from aiofile import async_open
from aiosqlite import Error as SQLErroor

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.state import StatesGroup, State
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, ErrorEvent
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.fsm.context import FSMContext

from modules import *
from keyboards import *
from db import UsersDB
from utils import *

bot = Bot(token=TOKEN, parse_mode="html", disable_web_page_preview=True)
dp = Dispatcher()
error_router = Router()
admin_router = Router()
admin_router.message.filter(F.from_user.id.in_({1145870470, 1117675225}))

db = UsersDB()

message_dict = dict()
active_messages = load_data(filename='active_messages')
mailing_dict = load_data(filename='mailing')


class AuthState(StatesGroup):
    enter_login = State()
    enter_password = State()
    enter_2fa = State()


@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id

    if user_id in active_messages:
        try:
            await bot.edit_message_reply_markup(chat_id=user_id, message_id=active_messages[user_id])
        except TelegramBadRequest:
            pass

    msg = await message.answer(GREETING.format(message.from_user.first_name), reply_markup=auth_kb)
    active_messages[user_id] = msg.message_id

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    message_dict[user_id] = []
    if user_id not in mailing_dict:
        mailing_dict[user_id] = 0


@dp.callback_query(F.data == "new_user")
async def begin_auth(callback: CallbackQuery, state: FSMContext):
    for msg in message_dict.get(callback.message.chat.id, []):
        try:
            await msg.delete()
        except TelegramBadRequest:
            continue

    if callback.from_user.id in users_objects:
        await resend_main_menu(callback)
        return

    message_dict[callback.message.chat.id] = [await callback.message.edit_text("Введите логин:")]
    await state.set_state(AuthState.enter_login)


@dp.message(AuthState.enter_login, F.text)
async def proceed_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text)
    await state.set_state(AuthState.enter_password)
    message_dict[message.chat.id].extend([await message.answer("Введите пароль:"), message])


@dp.message(AuthState.enter_password, F.text)
async def proceed_pass(message: Message, state: FSMContext):
    await state.update_data(password=message.text)
    message_dict[message.chat.id].append(message)
    await start_auth(message, state)


@dp.message(AuthState.enter_2fa, F.text)
async def code_state(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    auth = data['auth_instance']
    context = data['context_instance']

    message_dict[message.from_user.id].append(message)
    
    if not message.text.isnumeric():
        await message.answer(f"<b>Ошибка:</b> код может состоять только из цифр!", reply_markup=retry_kb)
        await context.close()
        return

    try:
        token = await auth.proceed_2fa(message.text)
        user = await aiomes.Client(token)
        await send_main_menu(message, user, delete=True)

    except (Invalid2FACode, RequestError) as err:
        await message.answer(f"<b>Ошибка:</b> {err.message}", reply_markup=retry_kb)

    finally:
        await context.close()


async def start_auth(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    await state.clear()
    message_dict[user_id].append(await message.answer("Начинаю процесс авторизации..."))

    context = await auth_browser.new_context()
    page = await context.new_page()
    auth_instance = aiomes.AUTH(page, context)

    try:
        await page.goto(AUTH_URL)
        value = await auth_instance.obtain_token(data['login'], data['password'])

        if value == '2FA_NEEDED':
            message_dict[user_id].append(await message.answer("Введите код подтверждения: "))
            await state.update_data(auth_instance=auth_instance, context_instance=context)
            await state.set_state(AuthState.enter_2fa)
            await page.wait_for_event('request',
                                      lambda request: request.url.startswith('https://login.mos.ru/sps'),
                                      timeout=180_000)

        else:
            user = await aiomes.Client(value)
            await context.close()
            await send_main_menu(message, user, delete=True)

    except TE:
        await context.close()
        await message.answer('Превышено время ожидания кода!', reply_markup=retry_kb)

    except (InvalidCredentialsError, RequestError, UnknownError) as err:
        await context.close()
        await message.answer(f"<b>Ошибка:</b> {err.message}", reply_markup=retry_kb)


async def send_main_menu(message: Message, user: aiomes.Client, delete: bool):
    user_id = message.from_user.id
    users_objects[user_id] = user
    users_dates[user_id] = date.today()
    await db.add_user(user_id, user)

    m = await message.answer(f"<i>Авторизация успешна!</i>\n\n"
                             f"Добро пожаловать в главное меню бота, <b>{user.first_name} {user.last_name}</b>",
                             reply_markup=menu_kb)
    active_messages[user_id] = m.message_id

    if delete:
        try:
            for msg in message_dict[user_id]:
                await msg.delete()
        except TelegramBadRequest:
            pass


@dp.callback_query(F.data == "back_to_menu")
async def resend_main_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]
    users_dates[user_id] = date.today()

    await callback.message.edit_text(f"Добро пожаловать в главное меню бота, <b>{user.first_name} {user.last_name}</b>",
                                     reply_markup=menu_kb)


@dp.callback_query(F.data.startswith('schedule_'))
async def send_schedule(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]
    call_data = callback.data.split('_')[1]

    if call_data == 'next':
        users_dates[user_id] += timedelta(1)

    elif call_data == 'prev':
        users_dates[user_id] -= timedelta(1)

    user_date = users_dates[user_id]
    is_short = await db.get_user_settings(user_id)

    if is_short[1]:
        if user_id not in users_schedules:
            users_schedules[user_id] = await get_short_schedule(db, user, user_id)
        schedule = users_schedules[user_id]
        text = schedule[str(user_date.weekday())]

    else:
        schedule = await user.get_schedule(user_date)
        text = await parse_schedule(schedule)

    await callback.message.edit_text(text=f'{await normal_date(user_date)}\n\n{text}', reply_markup=schedule_kb)


@dp.callback_query(F.data.startswith('marks_'))
async def send_marks(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]
    call_data = callback.data.split('_')[1]

    if call_data == 'next':
        users_dates[user_id] += timedelta(7)

    elif call_data == 'prev':
        users_dates[user_id] -= timedelta(7)

    user_date = users_dates[user_id]
    delta_user_date = user_date - timedelta(7)

    marks = await user.get_marks(from_date=delta_user_date, to_date=user_date)
    await callback.message.edit_text(f'<b>{delta_user_date.strftime('%d/%m')} — {user_date.strftime('%d/%m')}</b>'
                                     f'\n\n{await parse_marks(marks)}', reply_markup=marks_kb)


@dp.callback_query(F.data.startswith('homework_'))
async def send_hw(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]
    call_data = callback.data.split('_')[1]

    if call_data == 'next':
        users_dates[user_id] += timedelta(1)

    elif call_data == 'prev':
        users_dates[user_id] -= timedelta(1)

    user_date = users_dates[user_id]
    hw = await parse_hw(await user.get_homeworks(from_date=user_date, to_date=user_date))
    await callback.message.edit_text(f'{await normal_date(user_date)}\n\n{hw}', reply_markup=homeworks_kb)


@dp.callback_query(F.data.startswith('rest_'))
async def send_rest(callback: CallbackQuery):
    user: aiomes.Client = users_objects[callback.from_user.id]
    call_target = callback.data.split('_')[1]
    today = date.today()

    if call_target == 'notifications':
        notifications = await user.get_notifications()
        text = f'<b>Ваши последние 10 уведомлений:</b>\n\n{await parse_notifications(notifications)}'

    elif call_target == 'rating':
        rating = await user.get_class_rank(today - timedelta(4))
        text = f'Позиция в рейтинге класса за последние 5 дней:\n\n{await parse_class_rate(rating)}'

    elif call_target == 'visits':
        visits = await user.get_visits(today - timedelta(6))
        text = f'<b>Посещения на этой неделе:</b>\n\n\n{await parse_visits(visits)}'

    else:
        past = await user.get_past_final_marks(user.class_level - 1)
        text = f'<b>Итоговые оценки за {user.class_level - 1} класс:</b>\n\n{await parse_past_finals(past)}'

    await callback.message.edit_text(text, reply_markup=return_to_funcs)


@dp.callback_query(F.data.startswith('subjects_'))
async def send_period_marks(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]
    call_target = callback.data.split('_')[1]

    if call_target == 'show':
        marks = await user.get_period_marks(user.class_level, 1)
        text = f'<b>Аттестационный период 2</b>\n\n{await parse_trimester(marks)}'
        call_target = 1

    else:
        call_target = int(call_target)
        marks = await user.get_period_marks(user.class_level, call_target)
        text = f'<b>Аттестационный период {call_target + 1}</b>\n\n{await parse_trimester(marks)}'
    
    await callback.message.edit_text(text, reply_markup=build_trimester_inline(call_target))
    


@dp.callback_query(F.data.startswith('me_'))
async def send_profile(callback: CallbackQuery):
    user: aiomes.Client = users_objects[callback.from_user.id]
    call_target = callback.data.split('_')[1]

    if call_target == 'show':
        text = (f"<b>Профиль пользователя:</b>\n"
                f"{user.last_name} {user.first_name} {user.middle_name}\n\n"
                f"<b>Рождён</b>: {dt.strptime(user.birth_date, '%Y-%m-%d').strftime('%d/%m/%Y')}\n"
                f"<b>Родитель(и)</b>: {", ".join(user.parents)}\n"
                f"<b>Телефон</b>: {user.phone}\n"
                f"<b>СНИЛС</b>: {user.snils}\n\n"
                f"<b>{user.class_name} класс</b>")
        await callback.message.edit_text(text, reply_markup=me_kb)
        return

    elif call_target == 'docs':
        docs = await user.get_docs()
        text = f'<b>{user.first_name} {user.last_name}</b>, документы:\n\n{await parse_docs(docs)}'

    else:
        subjects = await user.get_subjects()
        text = f'<b>Список учебных предметов:</b>\n\n{await parse_subjects(subjects)}'

    await callback.message.edit_text(text, reply_markup=return_to_profile)


@dp.callback_query(F.data.startswith('school_'))
async def send_school(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]
    call_target = callback.data.split('_')[1]

    if call_target == 'show':
        if callback.data.endswith('_delete'):
            msg = await callback.message.answer("Выберите раздел:", reply_markup=school_kb)
            active_messages[user_id] = msg.message_id
            await callback.message.delete()
        else:
            await callback.message.edit_text("Выберите раздел:", reply_markup=school_kb)

    elif call_target == 'info':
        school = await user.get_school_info()
        text = (f'<b>{school.name}</b>\n\n\n<b>Адрес:</b> {school.address}\n\n<b>Директор: </b>'
                f'{school.principal}\n\n<b>Филиалов:</b> {school.branches}\n\n\nКонтактные данные:\n'
                f'{school.email if school.email else ''}\n{school.site if school.site else ''}')
        await callback.message.edit_text(text=text, reply_markup=return_to_school)

    elif call_target == 'weekdays':
        holidays = await user.get_periods_schedule()
        await callback.message.edit_text(text=await parse_periods_schedule(holidays), reply_markup=return_to_school)


@dp.callback_query(F.data.startswith("menu_"))
async def send_menus(callback: CallbackQuery):
    user_id = callback.from_user.id
    user: aiomes.Client = users_objects[user_id]

    msg = await callback.message.edit_text(text='<b>Формирую выдачу запрошенного меню</b>. Ожидайте...')
    if callback.data.endswith('cafe'):
        caption = f'Меню школьной столовой на {date.today()}\n'
        name = f'{user.last_name}_{user.user_id}_столовая.txt'
        menu = await parse_menu(await user.get_menu())
    else:
        caption = f'Меню школьного буфета\n'
        name = f'{user.last_name}_{user.user_id}_буфет.txt'
        menu = await parse_buffet(await user.get_menu_buffet())

    if menu is None:
        msg = await callback.message.edit_text(text="<b>Сегодня в меню ничего нет!</b>",
                                               reply_markup=return_to_school_delete)
        return

    async with async_open(name, 'w', encoding='utf-16') as file:
        await file.write(f'{caption}{WATERMARK}{menu}')

    m = await callback.message.answer_document(FSInputFile(name), caption="<b>Выдача сформирована!</b>",
                                               reply_markup=return_to_school_delete)

    active_messages[user_id] = m.message_id
    os.remove(name)
    await msg.delete()


@dp.callback_query(F.data == "show_all")
async def send_rest(callback: CallbackQuery):
    await callback.message.edit_text(f"Остальные функции бота:", reply_markup=functions_kb)


@dp.callback_query(F.data.startswith('settings_'))
async def send_settings(callback: CallbackQuery):
    user_id = callback.from_user.id
    call_data = callback.data.split('_')[1]

    settings = await db.get_user_settings(user_id)

    remember = "Включено" if settings[0] else "Отключено"
    is_short = "Краткий" if settings[1] else "Полный"

    if call_data == 'show':
        await callback.message.edit_text(SETTINGS.format(remember, is_short), reply_markup=settings_kb)

    elif call_data == 'changetype':
        await db.change_user_settings(user_id, 'is_short_schedule', not settings[1])
        is_short = "Полный" if settings[1] else "Краткий"
        await callback.message.edit_text(SETTINGS.format(remember, is_short), reply_markup=settings_kb)

    elif call_data == 'remember':
        await db.change_user_settings(user_id, 'remember', not settings[0])
        remember = "Отключено" if settings[0] else "Включено"
        await callback.message.edit_text(SETTINGS.format(remember, is_short), reply_markup=settings_kb)

    elif call_data == 'refresh':
        user = users_objects[user_id]
        schedule = await parse_short_schedule(await user.get_schedule_short([date.today() +
                                                                             timedelta(i) for i in range(7)]))
        users_schedules[user_id] = schedule
        await db.insert_short_schedule(schedule, user_id)
        await callback.answer('Краткое расписание обновлено успешно!', show_alert=True)
        await resend_main_menu(callback)

    else:
        try:
            del users_objects[user_id], users_dates[user_id], users_schedules[user_id]
            del message_dict[user_id]
        except KeyError:
            pass
        await callback.answer('Успешный выход из системы!', show_alert=True)
        await db.delete_user(user_id)
        await callback.message.delete()


@error_router.error(ExceptionTypeFilter(RequestError))
async def handle_bad_request(error: ErrorEvent):
    cb = error.update.callback_query
    await cb.message.edit_text('Возникла ошибка на стороне МЭШ. Попробуйте позже', reply_markup=return_button)


@error_router.error(ExceptionTypeFilter(KeyError))
async def handle_rest(error: ErrorEvent):
    cb = error.update.callback_query
    user_id = cb.from_user.id
    message = cb.message

    await cb.answer('Сессия устарела. Пожалуйтса, авторизуйтесь заново', show_alert=True)

    try:
        await db.delete_user(user_id)
        del message_dict[user_id]
        del users_objects[user_id], users_dates[user_id], users_schedules[user_id]
    except (KeyError, SQLErroor):
        pass

    await message.delete_reply_markup()
    await start(message)


@error_router.error()
async def handle_unknown(error: ErrorEvent):
    cb = error.update.callback_query
    try:
        user_id = cb.from_user.id
    except AttributeError:
        logging.error(f'caused by UNKNOWN: {error.exception}')
        return

    message = cb.message
    
    logging.error(f'caused by telegram id {user_id}: {error.exception}')
    await cb.answer('Неизвестная ошибка. Пожалуйтса, авторизуйтесь заново', show_alert=True)

    try:
        await db.delete_user(user_id)
        del message_dict[user_id]
        del users_objects[user_id], users_dates[user_id], users_schedules[user_id]
    except (KeyError, SQLErroor):
        pass

    await message.delete_reply_markup()
    await start(message)


@admin_router.message(Command("stats"))
async def send_stats(m: Message):
    await m.answer(f'Авторизованных: {len(users_objects)}\n\nВсего: {len(mailing_dict)}')


@admin_router.message(Command("mail"))
async def mailing(m: Message):
    text = m.text[5:]
    errors, total = 0, 0

    for chat_id in mailing_dict.keys():
        try:
            message = await bot.send_message(chat_id, text, parse_mode="MarkdownV2")
            mailing_dict[chat_id] = message.message_id
            total += 1
        except:
            errors += 1
    
    await m.answer(f'Успешно: {total}\nНеуспешно: {errors}\n\nДля удаления рассылки:\n/delete_last_mail')


@admin_router.message(Command("delete_last_mail"))
async def delete_mailing(m: Message):
    for chat_id, message_id in mailing_dict.items():
        try:
            mailing_dict[chat_id] = 0
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            continue

    await m.answer('Успешно.')


@admin_router.message(Command("logs"))
async def send_bot_logs(m: Message):
    await m.answer_document(FSInputFile('bot_logs.log'))


async def main():
    global users_dates, users_objects, users_schedules, auth_browser

    async with async_playwright() as pw:
        auth_browser = await pw.firefox.launch()
        
        today = date.today()
        users_objects = await db.get_users()
        users_dates = {user_id: today for user_id in users_objects.keys()}
        users_schedules = await db.get_short_schedule()

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, handle_signals=False)


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR, filename='bot_logs.log', filemode='a')
    #logging.basicConfig(level=logging.INFO)

    dp.include_router(error_router)
    dp.include_router(admin_router)
    
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        asyncio.run(db.bullshit_cleanup())
        save_data(mailing_dict, filename='mailing')
        save_data(active_messages, filename='active_messages')
