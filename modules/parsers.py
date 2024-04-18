from aiomes.output_types import *
from typing import List, Dict
from datetime import datetime as dt
from operator import attrgetter
from itertools import groupby
from statistics import mean

MARK_WEIGHTS_SYMBOLS = {1: '\u00B9', 2: '\u00B2', 3: '\u00B3', 4: '\u2074', 5: '\u2075'}
HTML_LINK = '<a href="{}">ссылка</a>'

WEEKDAYS = {
    0: 'Понедельник',
    1: 'Вторник',
    2: 'Cреда',
    3: 'Четверг',
    4: 'Пятница',
    5: 'Суббота',
    6: 'Воскресенье',
}
MONTHS = {
    1: 'января',
    2: 'февраля',
    3: 'марта',
    4: 'апреля',
    5: 'мая',
    6: 'июня',
    7: 'июля',
    8: 'августа',
    9: 'сентября',
    10: 'октября',
    11: 'ноября',
    12: 'декабря',
}


async def parse_schedule(items: List[ScheduleType]):
    if not items:
        return '<b>В этот день уроков нет.</b>'
    res = ''
    for l_id, item in enumerate(items):
        is_replaced = ' — <i><b>Замена</b></i>' if item.is_replaced else ''
        marks = f'\nОценки за урок: <tg-spoiler> {', '.join(item.marks)} </tg-spoiler>' if item.marks else ''
        res += (f'{l_id + 1}. <b>{item.name}</b>, <code>к.{item.room_number}</code>{is_replaced}\n'
                f'{item.start_time} — {item.end_time}{marks}\n\n')
    return res


async def parse_periods_schedule(items: List[PeriodsScheduleType]):
    res = ''
    for item in items:
        starts = dt.strptime(item.starts, '%Y-%m-%d').strftime('%d/%m/%Y')
        ends = dt.strptime(item.ends, '%Y-%m-%d').strftime('%d/%m/%Y')
        res += f'{starts} — {ends}\n<b>{item.name}</b>\n\n'
    return res


async def parse_short_schedule(d: Dict[str, List[ShortScheduleType]]):
    return {
        str(dt.strptime(key, '%Y-%m-%d').weekday()): await __parse_lessons(value) for
        key, value in d.items()
    }


async def __parse_lessons(items):
    if not items:
        return '<b>В этот день уроков нет.</b>'
    res = ''
    for idx, lesson in enumerate(items):
        res += f'{idx + 1}. <b>{lesson.name}</b>, {lesson.start_time} — {lesson.end_time}\n\n'
    return res


async def normal_date(date: datetime):
    return f'<b>{WEEKDAYS[date.weekday()]}</b>, {date.strftime('%#d')} {MONTHS[date.month]}'


async def parse_marks(items: List[BaseMarkType]):
    if not items:
        return 'У вас нет оценок за указанный период.'

    items.sort(key=attrgetter('mark_date'))
    items = {day: list(group) for day, group in groupby(items, key=attrgetter('mark_date'))}
    res = ''

    for mark_date, mark in items.items():
        marks = [f'{item.value}{MARK_WEIGHTS_SYMBOLS[item.weight]} — {item.subject_name}\n'
                 for item in mark]
        res += (f'{await normal_date(mark_date)}:\n'
                f'{''.join(marks)}\n')
    return res


async def parse_trimester(items: List[TrimesterMarksType]):
    if not items:
        return 'У вас пока нет оценок за этот период.'
    res = ''
    for item in items:
        final = f'{item.final_mark}' if item.final_mark else item.average_mark
        res += f'<b>{item.subject_name}</b>, {final}\n{', '.join(item.marks)}\n\n'
    return res


async def parse_hw(items: List[HouseworkType]):
    if not items:
        return '<b>На этот день ничего не задано.</b>'
    res = ''
    for item in items:
        files = f'\n<i>Файл(ы)</i>: {', '.join(map(lambda x: HTML_LINK.format(x), item.attached_files))}' \
            if item.attached_files else ''
        tests = f'\n<i>Тест(ы)</i>: {', '.join(map(lambda x: HTML_LINK.format(x), item.attached_tests))}' \
            if item.attached_tests else ''
        res += f'— <b><i>{item.subject_name}:</i></b>\n{item.description}{files}{tests}\n\n'
    return res


async def parse_class_rate(items: List[RankingType]):
    if not items:
        return '<b>В эту неделю рейтинг не составлялся.</b>'
    res = ''
    for item in items[::-1]:
        res += f'{item.rank_date.strftime('%#d/%m')}: {item.place}\n'
    return res


async def parse_notifications(items: List[NotificationType]):
    if not items:
        return '<b>У вас пока нет уведомлений.</b>'
    res = ''
    for item in items[:10]:
        notification_date = item.event_date.strftime('%d/%m %H:%M')

        if item.event_name == 'create_homework':
            res += (f'[{notification_date}] <u>Новое Д/З</u>\n{item.subject_name}\n'
                    f'{item.hw_description}\n\n')
        elif item.event_name == 'create_mark':
            res += (f'[{notification_date}] <u>Новая оценка</u>\n{item.subject_name}\n'
                    f'Получена <b>{item.mark_value}</b> с весом <b>{item.mark_weight}</b>\n\n')

    return res


async def parse_buffet(items: List[BuffetMenuType]):
    if items is None:
        return
    res = ''
    for item in items:
        availability = 'Доступно' if item.is_available else 'Нет в наличии'
        res += f'{item.name} — {int(item.price)}₽ [{availability}]\n'
    return res


async def parse_menu(items: List[ComplexMealType]):
    if items is None:
        return None
    res = ''
    for item in items:
        res += f'{item.title} — {item.price}₽:\n'
        for meal in item.composition:
            res += f'- {meal.name}: {meal.ingredients}. {meal.calories} ккал\n'
        res += '-' * 40 + '\n'
    return res


async def parse_visits(items: List[VisitType]):
    res = ''
    for item in items[::-1]:
        weekday = dt.strptime(item.visit_date, '%Y-%m-%d').weekday()
        res += f'<b>{WEEKDAYS[weekday]}</b>: {item.duration}\n{item.in_time} — {item.out_time}\n\n'
    return res


async def parse_past_finals(items: List[PrevYearMarksType]):
    if not items:
        return 'К сожалению, ничего не найдено.'
    res = ''
    finals = []
    for item in items:
        res += f'— {item.subject_name}: {item.final_mark}\n'
        finals.append(int(item.final_mark))
    res += f'\n<b>Средний балл</b>: {round(mean(finals), 2)}'
    return res


async def parse_docs(items: List[DocumentType]):
    res = ''
    for item in items:
        issue_D = dt.strptime(item.issue_date, '%Y-%m-%d').strftime('%d/%m/%Y') if item.issue_date else '—'

        res += (f'<b>ID документа:</b> {item.type_id}\nСерия / номер: <code>{item.series}</code> / <code>'
                f'{item.number}</code>\n<b>Выдан</b> <code>{item.issuer}</code>\n<b>Действителен до</b> <code>{issue_D}</code>\n\n')
    return res


async def parse_subjects(items: List):
    res = ''
    for item in items:
        res += f'— {item}\n'
    return res
