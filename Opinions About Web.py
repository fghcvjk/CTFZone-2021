import os
import asyncio
from contextlib import suppress
import uuid

from databases import Database
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import tartiflette
import tartiflette_asgi
import pydantic
import databases
import sqlalchemy
from celery import Celery

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)


ADMIN_COOKIE = os.getenv('ADMIN_COOKIE')
assert ADMIN_COOKIE is not None

DATABASE_URL = os.getenv('DB_URL')
assert DATABASE_URL is not None

REDIS_URL = os.getenv('REDIS_URL')
assert DATABASE_URL is not None

FLAG = os.getenv('FLAG')
assert FLAG is not None
FLAG_FIRST_PART = FLAG[:len(FLAG) // 2]
FLAG_SECOND_PART = FLAG[len(FLAG) // 2:]


user_app = FastAPI()
user_app.state.limiter = limiter
user_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

admin_app = FastAPI()


admin_app.add_middleware(
    CORSMiddleware,
    allow_origins=[]
)


def is_admin(request) -> bool:
    admin_cookie = request.cookies.get('admin')
    return admin_cookie is not None and admin_cookie == ADMIN_COOKIE


@admin_app.middleware("http")
async def only_admin(request: Request, call_next):
    is_root = request.base_url.path == '/'
    if is_root or is_admin:
        return await call_next(request)
    else:
        return Response(status_code=401)


@admin_app.on_event('startup')
@user_app.on_event('startup')
async def connect_to_db_on_startup():
    if not database.is_connected:
        await database.connect()


@admin_app.get("/")
async def _blank():
    return HTMLResponse(
        status_code=200,
        media_type='text/plain',
        content='ADMIN APP'
    )
  

@user_app.get("/")
async def opinion_form():
    with open('index.html') as f:
        return HTMLResponse(
            status_code=200,
            content=f.read()
        )


@user_app.get("/_src")
async def _src():
    with open('main.py') as f:
        return Response(
            status_code=200,
            media_type='text/plain',
            content=f.read()
        )


class OpinionMsg(pydantic.BaseModel):
    name: str
    text: str


@user_app.post("/opinion")
@limiter.limit("15/minute")
async def post_opinion(msg: OpinionMsg, request: Request, response: Response):
    op_id = uuid.uuid4().hex
    await database.execute(
        opinions.insert().values(id=op_id, name=msg.name, text=msg.text)
    )
    notify_admin(op_id)
    return {'op_id': op_id}


@user_app.get("/opinion/{op_id}")
async def view_opinion(request: Request, op_id):
    if not is_admin(request):
        return Response(status_code=401)

    res = await database.fetch_one(
        opinions.select().where(opinions.c.id == op_id)
    )
    if res is None:
        return Response(status_code=404)
    _, name, text = res.values()

    return HTMLResponse(
        status_code=200,
        content=f"""
            <html lang="en">
            <head>
                <title>Opinion</title>
            </head>
            <body>
                {name}: {text}
            </body>
            </html>
        """
    )


@admin_app.websocket("/server_status")
async def server_status(ws: WebSocket):
    if not is_admin(ws):
        await ws.close()
        return

    await ws.accept()

    async def send_status():
        with suppress(Exception):
            while True:
                await ws.send_json(dict(
                    flag_part2=FLAG_SECOND_PART
                ))
                await asyncio.sleep(5)

    sender = asyncio.create_task(send_status())
    with suppress(WebSocketDisconnect):
        await ws.receive_text()
    sender.cancel()


monitoring_app = tartiflette_asgi.TartifletteApp(
    graphiql=tartiflette_asgi.GraphiQL(path="/ide"),
    sdl="""
        schema {
          query: Query
        }

        type Event {
          title: String
          description: String
          happenedAt: String
        }

        type Query {
          lastEvents(after: String): [Event]
        }
    """
)


@tartiflette.Resolver("Query.lastEvents")
async def last_events(parent, args, context, info):
    if not is_admin(context['req']):
        raise RuntimeError('Not authorized')
    after = args.get('after', '1970-01-01')
    selected_events = await database.fetch_all(f"SELECT * FROM events WHERE happened_at > '{after}'")
    if selected_events is None:
        return []
    selected_events = (
        d.values()
        for d in selected_events
    )
    return [
        dict(title=title, description=desc, happenedAt=dt)
        for _, title, desc, dt in selected_events
    ]


admin_app.mount('/monitoring', monitoring_app)
admin_app.add_event_handler('startup', monitoring_app.startup)


# DB SETUP
database: Database = databases.Database(DATABASE_URL + "?min_size=1&max_size=1&command_timeout=1.2")
metadata = sqlalchemy.MetaData()

opinions = sqlalchemy.Table(
    'opinions',
    metadata,
    sqlalchemy.Column('id', sqlalchemy.String, primary_key=True),
    sqlalchemy.Column('name', sqlalchemy.Text, nullable=False),
    sqlalchemy.Column('text', sqlalchemy.Text, nullable=False)
)

events = sqlalchemy.Table(
    'events',
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, autoincrement=True, primary_key=True),
    sqlalchemy.Column('title', sqlalchemy.Text, nullable=False),
    sqlalchemy.Column('description', sqlalchemy.Text, nullable=False),
    sqlalchemy.Column('happened_at', sqlalchemy.Text, nullable=False)
)

flag_t = sqlalchemy.Table(
    'flag',
    metadata,
    sqlalchemy.Column('flag_part1', sqlalchemy.Text)
)

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

# Celery SETUP
jobs = Celery('jobs', broker=REDIS_URL)
def notify_admin(op_id):
    jobs.send_task('jobs.visit', (op_id,))
