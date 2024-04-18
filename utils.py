import asyncio
import json
from json.decoder import JSONDecodeError
from datetime import date, timedelta

import aiomes
from aiogram.filters.state import State
from playwright.async_api import async_playwright

from db import UsersDB
from modules.parsers import parse_short_schedule


async def terminate_context(state: State, context):
    await asyncio.sleep(20)

    if await state.get_data():
        await state.clear()
        await context.close()
        raise TimeoutError


async def get_short_schedule(db: UsersDB, user_object: aiomes.Client, user_id: int):
    schedule = await user_object.get_schedule_short([date.today() + timedelta(i) for i in range(7)])
    schedule = await parse_short_schedule(schedule)

    await db.insert_short_schedule(schedule, user_id)
    return schedule


def save_data(data: dict, filename: str):
    with open(f'storage/{filename}.json', 'w') as file:
        json.dump(data, file)


def load_data(filename: str):
    try:
        with open(f'storage/{filename}.json', 'r') as file:
            json_dict = json.load(file)
            return {int(key): int(val) for key, val in json_dict.items()}
    except (FileNotFoundError, JSONDecodeError):
        return {}
