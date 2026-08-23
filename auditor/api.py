import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
)
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select

from auditor.database import SessionLocal, criar_tabelas
from auditor.models import Contato, Site, Varredura


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(
    title="Auditor de Contatos Web",
    version="1.0.0",
    lifespan=lifespan,
)


class CriarVarreduraRequest(BaseModel):
    url: HttpUrl


def obter_url_varredura(
    varredura: Varredura,
    site: Site,
) -> str:
    return varredura.url_inicial or site.url


def limitar_mensagem_erro(
    mensagem: str,
    limite: int = 4000,
) -> str:
    mensagem_limpa = mensagem.strip()

    if not mensagem_limpa:
        return "Erro desconhecido durante a varredura."

    if len(mensagem_limpa) <= limite:
        return mensagem_limpa

    return mensagem_limpa[-limite:]


def marcar_varredura_em_andamento(
    varredura_id: int,
):
    with SessionLocal() as sessao:
        varredura = sessao.get(
            Varredura,
            varredura_id,
        )

        if not varredura:
            return

        varredura.status = "em_andamento"
        varredura.erro = None

        sessao.commit()


def marcar_varredura_com_erro(
    varredura_id: int,
    mensagem: str,
):
    with SessionLocal() as sessao:
        varredura = sessao.get(
            Varredura,
            varredura_id,
        )

        if not varredura:
            return

        varredura.status = "erro"
        varredura.erro = limitar_mensagem_erro(
            mensagem
        )
        varredura.fim = datetime.now(
            timezone.utc
        )

        sessao.commit()


def executar_varredura(
    varredura_id: int,
    url: str,
):
    marcar_varredura_em_andamento(
        varredura_id
    )

    comando = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "contatos",
        "-a",
        f"url={url}",
        "-a",
        f"varredura_id={varredura_id}",
    ]

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if resultado.returncode != 0:
            mensagem_erro = limitar_mensagem_erro(
                resultado.stderr.strip()
                or resultado.stdout.strip()
            )

            marcar_varredura_com_erro(
                varredura_id,
                mensagem_erro,
            )

    except subprocess.TimeoutExpired:
        marcar_varredura_com_erro(
            varredura_id,
            (
                "A varredura excedeu o tempo "
                "máximo de 120 segundos."
            ),
        )

    except Exception as erro:
        marcar_varredura_com_erro(
            varredura_id,
            str(erro),
        )


def executar_varredura_background(
    varredura_id: int,
    url: str,
):
    try:
        executar_varredura(
            varredura_id,
            url,
        )
    except Exception as erro:
        marcar_varredura_com_erro(
            varredura_id,
            str(erro),
        )


@app.get("/", include_in_schema=False)
def redirecionar_para_docs():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.get("/varreduras")
def listar_varreduras():
    with SessionLocal() as sessao:
        consulta = (
            select(Varredura, Site)
            .join(
                Site,
                Varredura.site_id == Site.id,
            )
            .order_by(
                Varredura.id.desc()
            )
        )

        resultados = sessao.execute(
            consulta
        ).all()

        return [
            {
                "id": varredura.id,
                "site": site.dominio,
                "url": obter_url_varredura(
                    varredura,
                    site,
                ),
                "status": varredura.status,
                "quantidade_paginas": (
                    varredura.quantidade_paginas
                ),
                "quantidade_contatos": (
                    varredura.quantidade_contatos
                ),
                "inicio": varredura.inicio,
                "fim": varredura.fim,
                "erro": varredura.erro,
            }
            for varredura, site in resultados
        ]


@app.get("/varreduras/{varredura_id}")
def buscar_varredura(
    varredura_id: int,
):
    with SessionLocal() as sessao:
        varredura = sessao.get(
            Varredura,
            varredura_id,
        )

        if not varredura:
            raise HTTPException(
                status_code=404,
                detail="Varredura não encontrada",
            )

        site = sessao.get(
            Site,
            varredura.site_id,
        )

        return {
            "id": varredura.id,
            "site": site.dominio,
            "url": obter_url_varredura(
                varredura,
                site,
            ),
            "status": varredura.status,
            "quantidade_paginas": (
                varredura.quantidade_paginas
            ),
            "quantidade_contatos": (
                varredura.quantidade_contatos
            ),
            "inicio": varredura.inicio,
            "fim": varredura.fim,
            "erro": varredura.erro,
        }


@app.get(
    "/varreduras/{varredura_id}/contatos"
)
def listar_contatos(
    varredura_id: int,
):
    with SessionLocal() as sessao:
        varredura = sessao.get(
            Varredura,
            varredura_id,
        )

        if not varredura:
            raise HTTPException(
                status_code=404,
                detail="Varredura não encontrada",
            )

        consulta = (
            select(Contato)
            .where(
                Contato.varredura_id
                == varredura_id
            )
            .order_by(
                Contato.id
            )
        )

        contatos = sessao.scalars(
            consulta
        ).all()

        return [
            {
                "id": contato.id,
                "email": contato.email,
                "pagina_origem": (
                    contato.pagina_origem
                ),
            }
            for contato in contatos
        ]


@app.post(
    "/varreduras",
    status_code=202,
)
def criar_varredura(
    dados: CriarVarreduraRequest,
    background_tasks: BackgroundTasks,
):
    url = str(dados.url)

    dominio = urlparse(
        url
    ).hostname

    if not dominio:
        raise HTTPException(
            status_code=400,
            detail="URL inválida",
        )

    with SessionLocal() as sessao:
        consulta = select(Site).where(
            Site.dominio == dominio
        )

        site = sessao.scalar(
            consulta
        )

        if not site:
            site = Site(
                dominio=dominio,
                url=url,
            )

            sessao.add(site)
            sessao.commit()
            sessao.refresh(site)

        varredura = Varredura(
            site_id=site.id,
            status="pendente",
            url_inicial=url,
            erro=None,
        )

        sessao.add(varredura)
        sessao.commit()
        sessao.refresh(varredura)

        varredura_id = varredura.id

    background_tasks.add_task(
        executar_varredura_background,
        varredura_id,
        url,
    )

    return {
        "id": varredura_id,
        "site": dominio,
        "url": url,
        "status": "pendente",
        "mensagem": (
            "Varredura adicionada "
            "para processamento"
        ),
    }
