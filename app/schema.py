from contextlib import asynccontextmanager
from functools import partial
import strawberry
from strawberry.types import Info
from fastapi import FastAPI
from strawberry.fastapi import BaseContext, GraphQLRouter
from databases import Database

from settings import Settings


class Context(BaseContext):
    db: Database

    def __init__(
        self,
        db: Database,
    ) -> None:
        self.db = db



@strawberry.type
class Author:
    id: int
    name: str


@strawberry.type
class Book:
    id: int
    title: str
    author: Author


@strawberry.type
class Query:
    @strawberry.field
    async def books(
        self,
        info: Info[Context, None],
        author_ids: list[int] | None = [],
        search: str | None = None,
        limit: int | None = None,
    ) -> list[Book]:
        print(f"{info=}, {author_ids=}, {search=}, {limit=}")
        try:
            query = "SELECT b.id, b.title, a.id AS author_id, a.name AS author_name FROM books b JOIN authors a ON b.author_id = a.id"
            if author_ids:
                query += f" WHERE b.author_id IN ({', '.join(str(author_id) for author_id in author_ids)})"
            if search:
                if author_ids:
                    query += " AND"
                else:
                    query += " WHERE"
                query += f" b.title ILIKE '%{search}%'"
            if limit:
                query += f" LIMIT {limit}"

            result = await info.context.db.fetch_all(query)
            print(f"raw query {result=}")

            # as Book objects
            books = []
            for row in result:
                author = Author(id=row['author_id'], name=row['author_name'])
                book = Book(id=row['id'], title=row['title'], author=author)
                books.append(book)

            return books
        except Exception as e:
            print(f"Error retrieving books: {e}")
            return []


CONN_TEMPLATE = "postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
settings = Settings()  # type: ignore
db = Database(
    CONN_TEMPLATE.format(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        port=settings.DB_PORT,
        host=settings.DB_SERVER,
        name=settings.DB_NAME,
    ),
)

@asynccontextmanager
async def lifespan(
    app: FastAPI,
    db: Database,
):
    async with db:
        yield
    await db.disconnect()

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(  # type: ignore
    schema,
    context_getter=partial(Context, db),
)

app = FastAPI(lifespan=partial(lifespan, db=db))
app.include_router(graphql_app, prefix="/graphql")
