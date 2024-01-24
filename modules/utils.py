import asyncio
from aiogram.filters.state import State


async def terminate_playwright(state: State, pw):
    await asyncio.sleep(180)

    if await state.get_data():
        await state.clear()
        await pw.__aexit__()
        raise TimeoutError
