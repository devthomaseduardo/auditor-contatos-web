from types import SimpleNamespace

import pytest
from scrapy.exceptions import DropItem


class LoggerFake:
    def info(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass


def criar_spider_fake(
    varredura_id,
    paginas_visitadas=None,
    erros_varredura=None,
):
    return SimpleNamespace(
        varredura_id=varredura_id,
        allowed_domains=["example.com"],
        start_urls=["https://example.com"],
        paginas_visitadas=paginas_visitadas or set(),
        erros_varredura=erros_varredura or [],
        logger=LoggerFake(),
    )


def criar_varredura(api, SessionLocal):
    with SessionLocal() as sessao:
        site = api.Site(
            dominio="example.com",
            url="https://example.com",
        )
        sessao.add(site)
        sessao.commit()
        sessao.refresh(site)

        varredura = api.Varredura(
            site_id=site.id,
            status="pendente",
            url_inicial="https://example.com",
        )
        sessao.add(varredura)
        sessao.commit()
        sessao.refresh(varredura)

        return varredura.id


def test_pipeline_salva_email_normalizado_e_ignora_duplicado(
    api_context,
):
    api, _client, SessionLocal = api_context
    from auditor.pipelines import AuditorPipeline

    varredura_id = criar_varredura(
        api,
        SessionLocal,
    )
    spider = criar_spider_fake(
        varredura_id,
        paginas_visitadas={
            "https://example.com/contato",
        },
    )
    pipeline = AuditorPipeline.from_crawler(
        SimpleNamespace(spider=spider)
    )

    pipeline.open_spider()
    item = pipeline.process_item(
        {
            "email": "Contato@Example.com",
            "pagina_origem": (
                "https://example.com/contato"
            ),
        }
    )

    assert item["email"] == "contato@example.com"

    with pytest.raises(DropItem):
        pipeline.process_item(
            {
                "email": "contato@example.com",
                "pagina_origem": (
                    "https://example.com/sobre"
                ),
            }
        )

    pipeline.close_spider()

    with SessionLocal() as sessao:
        varredura = sessao.get(
            api.Varredura,
            varredura_id,
        )
        contatos = sessao.query(api.Contato).all()

        assert varredura.status == "concluida"
        assert varredura.quantidade_paginas == 1
        assert varredura.quantidade_contatos == 1
        assert contatos[0].email == "contato@example.com"
        assert contatos[0].tipo == "email"
        assert contatos[0].valor == "contato@example.com"


def test_pipeline_salva_telefone_e_rede_social(
    api_context,
):
    api, _client, SessionLocal = api_context
    from auditor.pipelines import AuditorPipeline

    varredura_id = criar_varredura(
        api,
        SessionLocal,
    )
    spider = criar_spider_fake(
        varredura_id,
        paginas_visitadas={
            "https://example.com/contato",
        },
    )
    pipeline = AuditorPipeline.from_crawler(
        SimpleNamespace(spider=spider)
    )

    pipeline.open_spider()

    telefone = pipeline.process_item(
        {
            "tipo": "telefone",
            "valor": "+5511912345678",
            "pagina_origem": (
                "https://example.com/contato"
            ),
        }
    )
    instagram = pipeline.process_item(
        {
            "tipo": "instagram",
            "valor": (
                "https://instagram.com/empresa"
            ),
            "pagina_origem": (
                "https://example.com/contato"
            ),
        }
    )

    assert telefone["tipo"] == "telefone"
    assert "email" not in telefone
    assert instagram["tipo"] == "instagram"

    with pytest.raises(DropItem):
        pipeline.process_item(
            {
                "tipo": "telefone",
                "valor": "+5511912345678",
                "pagina_origem": (
                    "https://example.com/sobre"
                ),
            }
        )

    pipeline.close_spider()

    with SessionLocal() as sessao:
        varredura = sessao.get(
            api.Varredura,
            varredura_id,
        )
        contatos = (
            sessao.query(api.Contato)
            .order_by(api.Contato.id)
            .all()
        )

        assert varredura.status == "concluida"
        assert varredura.quantidade_contatos == 2
        assert [
            (
                contato.tipo,
                contato.valor,
            )
            for contato in contatos
        ] == [
            (
                "telefone",
                "+5511912345678",
            ),
            (
                "instagram",
                "https://instagram.com/empresa",
            ),
        ]
        assert contatos[0].email.startswith(
            "telefone:"
        )


def test_pipeline_marca_erro_quando_nenhuma_pagina_foi_processada(
    api_context,
):
    api, _client, SessionLocal = api_context
    from auditor.pipelines import AuditorPipeline

    varredura_id = criar_varredura(
        api,
        SessionLocal,
    )
    spider = criar_spider_fake(
        varredura_id,
        erros_varredura=[
            "Falha ao acessar https://example.invalid"
        ],
    )
    pipeline = AuditorPipeline.from_crawler(
        SimpleNamespace(spider=spider)
    )

    pipeline.open_spider()
    pipeline.close_spider()

    with SessionLocal() as sessao:
        varredura = sessao.get(
            api.Varredura,
            varredura_id,
        )

        assert varredura.status == "erro"
        assert "Falha ao acessar" in varredura.erro
        assert varredura.fim is not None
