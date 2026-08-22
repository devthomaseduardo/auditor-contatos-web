import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres"
    "@localhost:5432/auditor_contatos"
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    DEFAULT_DATABASE_URL,
)


def criar_engine(database_url: str) -> Engine:
    argumentos = {}

    if database_url.startswith("sqlite"):
        argumentos["connect_args"] = {
            "check_same_thread": False,
        }

    return create_engine(
        database_url,
        echo=False,
        **argumentos,
    )


engine = criar_engine(DATABASE_URL)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def criar_tabelas():
    Base.metadata.create_all(bind=engine)

    inspetor = inspect(engine)

    if "varreduras" not in inspetor.get_table_names():
        return

    colunas = {
        coluna["name"]
        for coluna in inspetor.get_columns(
            "varreduras"
        )
    }

    if "url_inicial" not in colunas:
        with engine.begin() as conexao:
            conexao.execute(
                text(
                    "ALTER TABLE varreduras "
                    "ADD COLUMN url_inicial VARCHAR(500)"
                )
            )
            conexao.execute(
                text(
                    "UPDATE varreduras "
                    "SET url_inicial = ("
                    "SELECT sites.url FROM sites "
                    "WHERE sites.id = varreduras.site_id"
                    ") "
                    "WHERE url_inicial IS NULL"
                )
            )
