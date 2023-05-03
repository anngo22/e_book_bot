import pprint
from functools import wraps
from typing import Any
import psycopg
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from utils.db import *
from aiogram.utils.callback_data import CallbackData
import utils.keyboards as kb
from config import TOKEN

ADMIN = 805312711

bot = Bot(token=TOKEN)

storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    name = State()
    age = State()


@dp.message_handler(commands=["start"])
async def process_start_command(message: types.Message):
    await message.reply(f"Привет, {message.from_user.full_name}!\n Напиши /help и я расскажу, что умею делать.")


@dp.message_handler(commands=["help"])
async def process_help_command(message: types.Message):
    await message.reply("Напиши\n /library чтобы получить список доступных жанров,\n /register чтобы зарегистрироваться")


cb = CallbackData("cb", "handle", "hint", "hint2")


# @dp.message_handler(commands=["money"])
# async def process_help_command(message: types.Message):
#     pass
#     # SQL for money sending


@dp.message_handler(commands=["library"])
async def process_library_command(message: types.Message):
    async with await psycopg.AsyncConnection.connect(
        "dbname=postgres user=postgres host='localhost' password = 'postgres'"
    ) as aconn:
        async with aconn.cursor() as acur:
            # pass  # write all values to db here

            await acur.execute(
                f"""select *
                    from e_book_library.user
                    where {message.from_user.id} = user_id;"""
            )
            res = await acur.fetchone()
    if res is None:
        await message.reply("You are not registered. Please register: /register")
    else:
        genres = await get_all_genres()
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
        for genre in genres:
            keyboard.add(
                types.InlineKeyboardButton(
                    text=genre, callback_data=cb.new(handle="gsh", hint=genre, hint2="")
                )
            )
        await message.answer("Choose your genre", reply_markup=keyboard)


@dp.callback_query_handler(cb.filter(handle="gsh"))
async def genre_selecter_handler(query: types.CallbackQuery, callback_data: dict):
    pprint.pprint(callback_data)
    selected_genre = callback_data["hint"]
    books = await get_books_by_genre(selected_genre)


    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    for book in books:
        keyboard.add(
            types.InlineKeyboardButton(
                text=book["title"],
                callback_data=cb.new(
                    handle="book_hanle", hint=str(book["book_id"]), hint2=""
                ),
            )
        )

    await bot.edit_message_text(
        f"All books of {selected_genre} genre",
        query.from_user.id,
        query.message.message_id,
        reply_markup=keyboard,
    )


@dp.callback_query_handler(cb.filter(handle="book_hanle"))
async def book_menu(query: types.CallbackQuery, callback_data: dict):
    book_id = callback_data["hint"]

    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.InlineKeyboardButton(
            text="buy", callback_data=cb.new(handle="purchase", hint=book_id, hint2="")
        )
    )
    keyboard.add(
        types.InlineKeyboardButton(
            text="rate", callback_data=cb.new(handle="rate", hint=book_id, hint2="")
        )
    )

    await bot.edit_message_text(
        f"Select action",
        query.from_user.id,
        query.message.message_id,
        reply_markup=keyboard,
    )


@dp.callback_query_handler(cb.filter(handle="purchase"))
async def money_handler(query: types.CallbackQuery, callback_data: dict):
    pprint.pprint(callback_data)
    book_id = callback_data["hint"]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    async with await psycopg.AsyncConnection.connect(CONNINFO) as aconn:
        async with aconn.cursor(row_factory=dict_row) as acur:
            res = await acur.execute(
                f"select cost from e_book_library.qualitative_characteristics where book_id = {book_id};"
            )
            res = await res.fetchone()
            pprint.pprint(res)
    keyboard.add(
        types.InlineKeyboardButton(
            text="Yes",
            callback_data=cb.new(
                handle="withdrawal_of_money", hint=book_id, hint2=res["cost"]
            ),
        ),
    )
    keyboard.add(
        types.InlineKeyboardButton(
            text="No",
            callback_data=cb.new(
                handle="no", hint=book_id, hint2=res["cost"]
            ),
        ),
    )
    await bot.edit_message_text(
        f"Cost: {res['cost']}₽",
        query.from_user.id,
        query.message.message_id,
        reply_markup=keyboard,
    )

@dp.callback_query_handler(cb.filter(handle = 'no'))
async def no_handler(query: types.CallbackQuery, callback_data: dict):
    await bot.edit_message_text(
        'Вы вернулись на главное меню.',
        query.from_user.id,
        query.message.message_id,
    )

@dp.callback_query_handler(cb.filter(handle="withdrawal_of_money"))
async def money_handler(query: types.CallbackQuery, callback_data: dict):
    pprint.pprint(callback_data)
    cost = callback_data["hint2"]
    try:
        async with await psycopg.AsyncConnection.connect(
            "dbname=postgres user=postgres host='localhost' password = 'postgres'"
        ) as aconn:
            async with aconn.cursor() as acur:
                await acur.execute(
                f"""update e_book_library.user
                    set balance = balance - {cost}
                    where user_id = {query.from_user.id};"""
            )
        await bot.edit_message_text(
            "approved",
            query.from_user.id,
            query.message.message_id,
        )
    except Exception as e:
        await bot.edit_message_text(
            "insufficient funds",
            query.from_user.id,
            query.message.message_id,
        )


@dp.callback_query_handler(cb.filter(handle="rate"))
async def genre_selecter_handler(query: types.CallbackQuery, callback_data: dict):
    pprint.pprint(callback_data)
    book_id = callback_data["hint"]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    for i in range(10):
        keyboard.add(
            types.InlineKeyboardButton(
                text=str(i + 1),
                callback_data=cb.new(
                    handle="push_rating", hint=book_id, hint2=str(i + 1)
                ),
            ),
        )

    await bot.edit_message_text(
        f"choose mark",
        query.from_user.id,
        query.message.message_id,
        reply_markup=keyboard,
    )


@dp.callback_query_handler(cb.filter(handle="push_rating"))
async def genre_selecter_handler(query: types.CallbackQuery, callback_data: dict):
    pprint.pprint(callback_data)

    book_id = callback_data["hint"]
    mark = callback_data["hint2"]
    await set_mark(book_id, mark, query.from_user.id)
    await bot.edit_message_text(
        f"mark set",
        query.from_user.id,
        query.message.message_id,
    )


# @dp.message_handler(commands=['delete_account'])
# async def process_login_command(msg: types.Message):
#     # sQl for data removal
#     pass


@dp.message_handler(commands=["register"])
async def process_login_command(msg: types.Message):
    async with await psycopg.AsyncConnection.connect(
        "dbname=postgres user=postgres host='localhost' password = 'postgres'"
    ) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute(
                f"""select *
                    from e_book_library.user
                    where {msg.from_user.id} = user_id;"""
            )
            res = await acur.fetchone()
    if not res is None:
        await msg.reply("You are already registered.")
    else:
        await Form.name.set()
        await msg.reply("Enter your name:")


@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["name"] = message.text
    await Form.next()
    await message.reply("How old are you?")


@dp.message_handler(lambda message: message.text.isdigit(), state=Form.age)
async def process_age(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["age"] = int(message.text)
    async with await psycopg.AsyncConnection.connect(
        "dbname=postgres user=postgres host='localhost' password = 'postgres'"
    ) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute(
                f"""insert into e_book_library.user (user_id, user_name, age, balance)
                                values ({message.from_user.id}, '{data['name']}', {int(message.text)}, 0);"""
            )
    await message.reply("Registration is over")
    await Form.next()


executor.start_polling(dp)
