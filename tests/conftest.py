import sys

import pytest
from fastapi.testclient import TestClient


MODULOS_BANCO = (
    "auditor.api",
    "auditor.pipelines",
    "auditor.models",
    "auditor.database",
)


@pytest.fixture()
def api_context(tmp_path, monkeypatch):
    database_url = (
        f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        database_url,
    )

    pacote_auditor = sys.modules.get(
        "auditor"
    )

    for modulo in MODULOS_BANCO:
        sys.modules.pop(modulo, None)

        if pacote_auditor:
            nome_atributo = modulo.rsplit(
                ".",
                1,
            )[-1]
            if hasattr(
                pacote_auditor,
                nome_atributo,
            ):
                delattr(
                    pacote_auditor,
                    nome_atributo,
                )

    import auditor.api as api
    from auditor.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)

    with TestClient(api.app) as client:
        yield api, client, SessionLocal

    Base.metadata.drop_all(bind=engine)
