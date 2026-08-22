import re
import scrapy

from urllib.parse import urlparse

from auditor.relatorio import RelatorioVarredura


class ContatosSpider(scrapy.Spider):
    name = "contatos"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1,
        "HTTPERROR_ALLOW_ALL": True,
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

        dominio = urlparse(url)
        hostname = dominio.hostname

        if not hostname:
            raise ValueError(
                "URL inválida para iniciar a análise"
            )

        self.start_urls = [url]

        self.allowed_domains = [hostname]

        self.varredura_id = (
            int(varredura_id)
            if varredura_id
            else None
        )

        self.emails_encontrados = set()
        self.paginas_visitadas = set()
        self.erros_varredura = []

        self.relatorio = RelatorioVarredura(
            hostname
        )

    @classmethod
    def extrair_emails(cls, texto):
        return {
            email.lower()
            for email in cls.padrao_email.findall(
                texto or ""
            )
        }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=self.registrar_erro,
                dont_filter=True,
            )

    def parse(self, response):
        if self.resposta_com_erro(response):
            return

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
                    errback=self.registrar_erro,
                )

    def analisar_pagina_importante(
        self,
        response,
    ):
        if self.resposta_com_erro(response):
            return

        yield from self.processar_pagina(
            response
        )

    def resposta_com_erro(self, response):
        if response.status < 400:
            return False

        self.adicionar_erro(
            (
                f"HTTP {response.status} ao acessar "
                f"{response.url}"
            )
        )

        return True

    def registrar_erro(self, failure):
        request = failure.request

        self.adicionar_erro(
            (
                f"Falha ao acessar {request.url}: "
                f"{failure.getErrorMessage()}"
            )
        )

    def adicionar_erro(self, mensagem):
        if mensagem in self.erros_varredura:
            return

        self.erros_varredura.append(mensagem)

        self.logger.warning(mensagem)

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

        emails_da_pagina = self.extrair_emails(
            response.text
        )

        for email in emails_da_pagina:
            if (
                email
                in self.emails_encontrados
            ):
                continue

            self.emails_encontrados.add(
                email
            )

            self.relatorio.adicionar_email(
                email
            )

            yield {
                "email": email,
                "pagina_origem": response.url,
            }

    def closed(self, reason):
        self.relatorio.finalizar()
        self.relatorio.salvar()

        self.logger.info(
            "Relatório da varredura salvo "
            "em relatorio.json"
        )
