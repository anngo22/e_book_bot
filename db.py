import contextlib
from typing import List
import psycopg
from psycopg.rows import dict_row

CONNINFO = "dbname=postgres user=postgres host=localhost password=postgres"


def dict_factory(cursor: psycopg.AsyncCursor, row: tuple):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@contextlib.contextmanager
async def get_cursor() -> psycopg.AsyncCursor:
    async with await psycopg.AsyncConnection.connect(CONNINFO) as aconn:
        async with aconn.cursor() as acur:
            yield acur


async def get_all_genres() -> List[str]:
    async with await psycopg.AsyncConnection.connect(CONNINFO) as aconn:
        async with aconn.cursor(row_factory=dict_row) as acur:
            res = await acur.execute("select distinct genre from e_book_library.book")
            res = [item["genre"] async for item in res]
            return res


async def get_books_by_genre(genre: str) -> List[dict]:
    async with await psycopg.AsyncConnection.connect(CONNINFO) as aconn:
        async with aconn.cursor(row_factory=dict_row) as acur:
            res = await acur.execute(
                f"select * from e_book_library.book where genre = '{genre}'"
            )
            res = [item async for item in res]
            return res


async def set_mark(book_id: str, mark: str, user_id: str):
    async with await psycopg.AsyncConnection.connect(CONNINFO) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute(
                f"""insert into e_book_library.user_x_book(book_id, user_id, mark)
                                    values ({book_id}, '{user_id}', {mark});"""
            )
