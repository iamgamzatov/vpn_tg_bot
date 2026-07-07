import aiosqlite
DB_GamziVPN = 'usersGamzi.db'

async def init_bd():
    async with aiosqlite.connect(DB_GamziVPN) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                username TEXT,
                used_promo INTEGER DEFAULT 0
            )
        """)
        cursor = await db.execute('PRAGMA table_info(users)')
        columns = [column[1] for column in await cursor.fetchall()]

        if 'sub_id' not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN sub_id TEXT")
            print("✅ База данных обновлена: добавлен столбец sub_id")

        await db.commit()

# ---------------------------------------------------------
async def save_sub_id(tg_id, sub_id):
    async with aiosqlite.connect(DB_GamziVPN) as db:
        await db.execute("UPDATE users SET sub_id = ? WHERE tg_id = ?", (sub_id, tg_id))
        await db.commit()

async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_GamziVPN) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def get_user_data(tg_id: int):
    async with aiosqlite.connect(DB_GamziVPN) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row) # <--- ВАЖНО: принудительно делаем словарь
            return None


async def get_users() -> list:
    async with aiosqlite.connect(DB_GamziVPN) as db:
        cursor = await db.execute('SELECT id, tg_id, username FROM users')
        result = await cursor.fetchall()
        return list(result)

async def get_user_internal_id(user_id: int) -> int | None:
    async with aiosqlite.connect(DB_GamziVPN) as db:
        cursor = await db.execute('SELECT id FROM users WHERE tg_id = ?', (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def check_if_promo_used(tg_id: int) -> bool:
    """
    Проверяет, активировал ли пользователь промокод ранее.
    Возвращает True, если использовал (1), и False, если нет (0) или если юзера нет в базе.
    """
    async with aiosqlite.connect(DB_GamziVPN) as db:
        # Получаем значение колонки used_promo для конкретного tg_id
        async with db.execute("SELECT used_promo FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                # row[0] вернет либо 1, либо 0.
                # bool(1) станет True, bool(0) станет False.
                return bool(row[0])
            return False  # Если пользователя почему-то вообще нет в базе данных


async def mark_promo_as_used(tg_id: int) -> None:
    """
    Помечает в базе данных, что пользователь успешно использовал промокод.
    """
    async with aiosqlite.connect(DB_GamziVPN) as db:
        # Тот самый прикольный UPDATE, который ставит флаг в 1
        await db.execute("UPDATE users SET used_promo = 1 WHERE tg_id = ?", (tg_id,))
        # КРИТИЧЕСКИ ВАЖНО для UPDATE/INSERT запросов делать commit, чтобы изменения сохранились в файл!
        await db.commit()