from keyboards.kb_builders import *

return_button = {'text': '⬅️ Вернуться в меню', 'call_data': 'back_to_menu'}
return_to_funcs = build_inline_kb([{'text': '⬅️ Назад', 'call_data': 'show_all'}])
return_to_school = build_inline_kb([{'text': '⬅️ Назад', 'call_data': 'school_show'}])
return_to_school_delete = build_inline_kb([{'text': '⬅️ Назад', 'call_data': 'school_show_delete'}])
return_to_profile = build_inline_kb([{'text': '⬅️ Назад', 'call_data': 'me_show'}])

auth_kb = build_inline_kb([{'text': 'Авторизация 🔐', 'call_data': 'new_user'}])
retry_kb = build_inline_kb([{'text': 'Попробовать снова ↩️', 'call_data': 'new_user'}])

menu_kb = build_inline_kb(
    [{'text': 'Расписание 🕘', 'call_data': 'schedule_show'},
     {'text': 'Домашние задания 🗓', 'call_data': 'homework_show'},
     {'text': 'Оценки 💯', 'call_data': 'marks_show'},
     {'text': 'Моя школа 🏫', 'call_data': 'school_show'},
     {'text': 'Все функции 🌟', 'call_data': 'show_all'},
     {'text': '⚙️ Настройки', 'call_data': 'settings_show'},
     ]
)

me_kb = build_inline_kb(
    [
        {'text': 'Мои документы 📃', 'call_data': 'me_docs'},
        {'text': 'Мои предметы 📚', 'call_data': 'me_subjects'},
        {'text': '⬅️ Назад', 'call_data': 'show_all'}
    ]
)
functions_kb = build_functions_inline()
school_kb = build_school_inline()

settings_kb = build_inline_kb(
    [
        {'text': 'Переключить сохранение 🔀', 'call_data': 'settings_remember'},
        {'text': 'Переключить расписание 🔀', 'call_data': 'settings_changetype'},
        {'text': 'Обновить расписание 🔄', 'call_data': 'settings_refresh'},
        {'text': 'Выйти из аккаунта ❌', 'call_data': 'settings_exit'},
        return_button
    ]
)

marks_kb = build_marks_inline()
subject_marks_kb = build_trimester_inline()

homeworks_kb = build_dates_inline('homework')
schedule_kb = build_dates_inline('schedule')
