from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

dp = Dispatcher()


@dp.message(Command("stats"))
async def send_stats(m: Message):
    if m.from_user.id not in [1145870470, 1117675225]:
        return
    await m.answer(f'Авторизованных: {len(users_objects)}\n\nВсего: {len(message_dict)}')


@dp.message(Command("mail"))
async def mailing(m: Message):
    if m.from_user.id not in [1145870470, 1117675225]:
        return
    text = m.text[5:]
    errors, total = 0, 0
    mailing_dict[m.message_id] = []
    for chat_id in message_dict.keys():
        try:
            mailing_dict[m.message_id].append(await bot.send_message(chat_id, text, parse_mode="Markdown"))
            total += 1
        except Exception:
            errors += 1
    await m.answer(f'Успешно: {total}\nНеуспешно: {errors}\n\nID рассылки: <code>{m.message_id}</code>')


@dp.message(Command("mail_delete"))
async def delete_mailing(m: Message):
    if m.from_user.id not in [1145870470, 1117675225]:
        return
    m_id = int(m.text.split(" ")[1])
    for msg in mailing_dict.get(m_id, []):
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
    mailing_dict.clear()
    await m.answer('Успешно.')
