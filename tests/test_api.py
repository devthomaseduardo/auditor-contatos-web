from datetime import datetime, timezone
from types import SimpleNamespace


def criar_varredura(api, SessionLocal):
    with SessionLocal() as sessao:
        site = api.Site(
            dominio="example.invalid",
            url="https://example.invalid",
        )
        sessao.add(site)
        sessao.commit()
        sessao.refresh(site)

        varredura = api.Varredura(
            site_id=site.id,
            status="pendente",
            url_inicial="https://example.invalid",
        )
        sessao.add(varredura)
        sessao.commit()
        sessao.refresh(varredura)

        return varredura.id


def test_health(api_context):
    _api, client, _SessionLocal = api_context

    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "status": "ok",
    }


def test_raiz_redireciona_para_docs(api_context):
    _api, client, _SessionLocal = api_context

    resposta = client.get(
        "/",
        follow_redirects=False,
    )

    assert resposta.status_code == 307
    assert resposta.headers["location"] == "/docs"


def test_criar_varredura_agenda_execucao_em_background(
    api_context,
    monkeypatch,
):
    api, client, SessionLocal = api_context
    chamadas = []

    def background_fake(varredura_id, url):
        chamadas.append(
            {
                "varredura_id": varredura_id,
                "url": url,
            }
        )

        with SessionLocal() as sessao:
            varredura = sessao.get(
                api.Varredura,
                varredura_id,
            )
            varredura.status = "concluida"
            varredura.fim = datetime.now(
                timezone.utc
            )
            sessao.commit()

    monkeypatch.setattr(
        api,
        "executar_varredura_background",
        background_fake,
    )

    resposta = client.post(
        "/varreduras",
        json={
            "url": "https://example.com",
        },
    )

    dados = resposta.json()

    assert resposta.status_code == 202
    assert dados["status"] == "pendente"
    assert chamadas == [
        {
            "varredura_id": dados["id"],
            "url": "https://example.com/",
        }
    ]

    detalhe = client.get(
        f"/varreduras/{dados['id']}"
    ).json()

    assert detalhe["status"] == "concluida"
    assert detalhe["url"] == "https://example.com/"


def test_varreduras_preservam_url_inicial_por_execucao(
    api_context,
    monkeypatch,
):
    api, client, _SessionLocal = api_context

    monkeypatch.setattr(
        api,
        "executar_varredura_background",
        lambda *_args: None,
    )

    primeira = client.post(
        "/varreduras",
        json={
            "url": "https://example.com/index.html",
        },
    ).json()
    segunda = client.post(
        "/varreduras",
        json={
            "url": "https://example.com/nao-existe.html",
        },
    ).json()

    detalhe_primeira = client.get(
        f"/varreduras/{primeira['id']}"
    ).json()
    detalhe_segunda = client.get(
        f"/varreduras/{segunda['id']}"
    ).json()

    assert detalhe_primeira["url"] == (
        "https://example.com/index.html"
    )
    assert detalhe_segunda["url"] == (
        "https://example.com/nao-existe.html"
    )


def test_executar_varredura_salva_erro_quando_scrapy_falha(
    api_context,
    monkeypatch,
):
    api, _client, SessionLocal = api_context
    varredura_id = criar_varredura(
        api,
        SessionLocal,
    )

    def run_fake(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=(
                "Falha DNS controlada para "
                "https://example.invalid"
            ),
        )

    monkeypatch.setattr(
        api.subprocess,
        "run",
        run_fake,
    )

    api.executar_varredura(
        varredura_id,
        "https://example.invalid",
    )

    with SessionLocal() as sessao:
        varredura = sessao.get(
            api.Varredura,
            varredura_id,
        )

        assert varredura.status == "erro"
        assert "Falha DNS controlada" in varredura.erro
        assert varredura.fim is not None


def test_listar_contatos_da_varredura(api_context):
    api, client, SessionLocal = api_context
    varredura_id = criar_varredura(
        api,
        SessionLocal,
    )

    with SessionLocal() as sessao:
        contato = api.Contato(
            varredura_id=varredura_id,
            email="contato@example.invalid",
            pagina_origem=(
                "https://example.invalid/contato"
            ),
        )
        sessao.add(contato)
        sessao.commit()

    resposta = client.get(
        f"/varreduras/{varredura_id}/contatos"
    )

    assert resposta.status_code == 200
    assert resposta.json() == [
        {
            "id": 1,
            "email": "contato@example.invalid",
            "pagina_origem": (
                "https://example.invalid/contato"
            ),
        }
    ]
