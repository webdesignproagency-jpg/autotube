import aiosqlite, os
from datetime import datetime
DB_PATH = os.getenv('DB_PATH','./production_vault.db')

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, title TEXT, keywords TEXT, output_path TEXT, thumbnail_path TEXT, youtube_url TEXT, status TEXT DEFAULT "draft", created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        await db.execute('CREATE TABLE IF NOT EXISTS pipeline_runs (id TEXT PRIMARY KEY, topic TEXT, started_at TEXT, finished_at TEXT, status TEXT, layers_completed TEXT)')
        await db.execute('CREATE TABLE IF NOT EXISTS oauth_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, access_token TEXT, refresh_token TEXT, token_expiry TEXT, channel_id TEXT, channel_name TEXT)')
        await db.commit()

async def topic_exists(topic: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT topic FROM videos') as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def save_video(topic, title, keywords, output_path, thumbnail_path):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO videos (topic,title,keywords,output_path,thumbnail_path) VALUES (?,?,?,?,?)',[topic,title,keywords,output_path,thumbnail_path])
        await db.commit()

async def mark_published(topic, youtube_url):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE videos SET status="published", youtube_url=? WHERE topic=?',[youtube_url,topic])
        await db.commit()

async def save_run(run_id, topic, status, layers_done):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR REPLACE INTO pipeline_runs (id,topic,started_at,finished_at,status,layers_completed) VALUES (?,?,?,?,?,?)',[run_id,topic,datetime.utcnow().isoformat(),datetime.utcnow().isoformat(),status,','.join(map(str,layers_done))])
        await db.commit()

async def save_tokens(access, refresh, expiry, channel_id, channel_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM oauth_tokens')
        await db.execute('INSERT INTO oauth_tokens (access_token,refresh_token,token_expiry,channel_id,channel_name) VALUES (?,?,?,?,?)',[access,refresh,expiry,channel_id,channel_name])
        await db.commit()

async def get_tokens():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM oauth_tokens LIMIT 1') as cur:
            return await cur.fetchone()
