from scrapy.http import HtmlResponse, Request

from auditor.spiders.contatos import ContatosSpider


def criar_response(
    url: str,
    corpo: str,
    status: int = 200,
):
    request = Request(url=url)

    return HtmlResponse(
        url=url,
        request=request,
        body=corpo.encode("utf-8"),
        encoding="utf-8",
        status=status,
    )


def test_extrai_emails_normalizados_e_sem_repetir():
    spider = ContatosSpider(
        url="https://example.com"
    )
    response = criar_response(
        "https://example.com/contato",
        """
        <a href="mailto:Contato@Example.com">Contato</a>
        <p>financeiro@example.com</p>
        <p>CONTATO@example.com</p>
        """,
    )

    itens = list(
        spider.processar_pagina(response)
    )

    assert {
        item["valor"]
        for item in itens
        if item["tipo"] == "email"
    } == {
        "contato@example.com",
        "financeiro@example.com",
    }
    assert list(
        spider.processar_pagina(response)
    ) == []


def test_extrai_telefones_whatsapp_e_redes_sociais():
    spider = ContatosSpider(
        url="https://example.com"
    )
    response = criar_response(
        "https://example.com/contato",
        """
        <p>Telefone comercial: (11) 91234-5678</p>
        <a href="tel:+551140028922">Ligar</a>
        <a href="https://wa.me/5511999998888">WhatsApp</a>
        <a href="https://www.instagram.com/empresa.teste/?utm_source=site">
            Instagram
        </a>
        <a href="https://linkedin.com/company/empresa-teste/">
            LinkedIn
        </a>
        """,
    )

    itens = list(
        spider.processar_pagina(response)
    )

    assert {
        (
            item["tipo"],
            item["valor"],
        )
        for item in itens
    } == {
        (
            "telefone",
            "+5511912345678",
        ),
        (
            "telefone",
            "+551140028922",
        ),
        (
            "whatsapp",
            "+5511999998888",
        ),
        (
            "instagram",
            "https://www.instagram.com/empresa.teste",
        ),
        (
            "linkedin",
            "https://linkedin.com/company/empresa-teste",
        ),
    }


def test_registra_http_com_erro_sem_processar_pagina():
    spider = ContatosSpider(
        url="https://example.com"
    )
    response = criar_response(
        "https://example.com/nao-existe",
        "Nao encontrado",
        status=404,
    )

    assert spider.resposta_com_erro(response) is True
    assert spider.paginas_visitadas == set()
    assert "HTTP 404" in spider.erros_varredura[0]
