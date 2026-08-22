import re
import scrapy

from urllib.parse import urlparse

from auditor.relatorio import RelatorioVarredura


class ContatosSpider(scrapy.Spider):
    name = "contatos"

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 1,
    }

    padrao_email = re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    paginas_importantes = {
        "contact",
        "contato",
        "about",
        "sobre",
        "team",
        "equipe",
        "support",
        "suporte",
    }

    limite_paginas = 10

    def __init__(
        self,
        url=None,
        varredura_id=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if not url:
            raise ValueError(
                "Informe uma URL para iniciar a análise"
            )

        self.start_urls = [url]

        dominio = urlparse(url)

        self.allowed_domains = [dominio.hostname]

        self.varredura_id = (
            int(varredura_id)
            if varredura_id
            else None
        )

        self.emails_encontrados = set()
        self.paginas_visitadas = set()

        self.relatorio = RelatorioVarredura(
            dominio.hostname
        )

    def parse(self, response):
        yield from self.processar_pagina(response)

        for link in response.css(
            "a::attr(href)"
        ).getall():
            if (
                len(self.paginas_visitadas)
                >= self.limite_paginas
            ):
                break

            if link.startswith(
                (
                    "mailto:",
                    "tel:",
                    "javascript:",
                    "#",
                )
            ):
                continue

            url_completa = response.urljoin(link)
            url_normalizada = url_completa.lower()

            if any(
                palavra in url_normalizada
                for palavra in self.paginas_importantes
            ):
                yield scrapy.Request(
                    url_completa,
                    callback=self.analisar_pagina_importante,
                )

    def analisar_pagina_importante(
        self,
        response,
    ):
        yield from self.processar_pagina(
            response
        )

    def processar_pagina(self, response):
        if response.url in self.paginas_visitadas:
            return

        self.paginas_visitadas.add(
            response.url
        )

        self.relatorio.adicionar_pagina(
            response.url
        )

        self.logger.info(
            f"Analisando página: {response.url}"
        )

        emails_da_pagina = set(
            self.padrao_email.findall(
                response.text
            )
        )

        for email in emails_da_pagina:
            email_normalizado = email.lower()

            if (
                email_normalizado
                in self.emails_encontrados
            ):
                continue

            self.emails_encontrados.add(
                email_normalizado
            )

            self.relatorio.adicionar_email(
                email_normalizado
            )

            yield {
                "email": email_normalizado,
                "pagina_origem": response.url,
            }

    def closed(self, reason):
        self.relatorio.finalizar()
        self.relatorio.salvar()

        self.logger.info(
            "Relatório da varredura salvo "
            "em relatorio.json"
        )
