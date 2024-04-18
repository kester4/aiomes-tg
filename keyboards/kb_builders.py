from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BACK = [InlineKeyboardButton(text='⬅️ Вернуться в меню', callback_data='back_to_menu')]


def build_inline_kb(buttons: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=button["text"], callback_data=button["call_data"])]
        for button in buttons
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_dates_inline(value: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text='⬅️', callback_data=f'{value}_prev'),
            InlineKeyboardButton(text='➡️', callback_data=f'{value}_next')
        ],
        BACK
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_marks_inline() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='По неделям 📅', callback_data='subjects_show')],
        [
            InlineKeyboardButton(text='⬅️', callback_data='marks_prev'),
            InlineKeyboardButton(text='➡️', callback_data='marks_next')
        ],
        BACK
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_trimester_inline(excluded_trimester: int) -> InlineKeyboardMarkup:
    trimesters = {
        0: '1️⃣',
        1: '2️⃣',
        2: '3️⃣',
        3: '4️⃣'
    }
    del trimesters[excluded_trimester]
    
    buttons = [
        [InlineKeyboardButton(text='По предметам 🌐', callback_data='marks_show')],
        [
            InlineKeyboardButton(text=symbol, callback_data=f'subjects_{i}') for i, symbol in trimesters.items() 
        ],
        BACK
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_functions_inline() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='Мой профиль 👨‍🎓', callback_data='me_show')],
        [InlineKeyboardButton(text='Уведомления 🔔', callback_data='rest_notifications')],
        [InlineKeyboardButton(text='Посещаемость 👀', callback_data='rest_visits')],
        [InlineKeyboardButton(text='Рейтинг в классе 🏆', callback_data='rest_rating')],
        [InlineKeyboardButton(text='Оценки прошлого года 🧾', callback_data='rest_archive')],
        BACK
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_school_inline() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="О школе 🔎", callback_data="school_info")],
        [InlineKeyboardButton(text="Меню столовой 🍴", callback_data='menu_cafe')],
        [InlineKeyboardButton(text="Меню буфета 🍭", callback_data='menu_buffet')],
        [InlineKeyboardButton(text='Расписание каникул ✨', callback_data='school_weekdays')],
        BACK
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
