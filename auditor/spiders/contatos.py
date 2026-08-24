import re
import scrapy

from urllib.parse import (
    parse_qs,
    unquote,
    urlparse,
    urlunparse,
)

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

    padrao_telefone = re.compile(
        (
            r"(?<!\d)"
            r"(?:(?:\+|00)?55[\s().-]*)?"
            r"(?:\(?\d{2}\)?[\s().-]*)?"
            r"(?:9[\s().-]*)?"
            r"\d{4}[\s().-]*\d{4}"
            r"(?!\d)"
        )
    )

    dominios_redes_sociais = {
        "instagram.com": "instagram",
        "linkedin.com": "linkedin",
        "facebook.com": "facebook",
        "youtube.com": "youtube",
        "x.com": "x",
        "twitter.com": "x",
        "tiktok.com": "tiktok",
    }

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
        self.contatos_encontrados = set()
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

    @classmethod
    def normalizar_telefone(cls, telefone):
        digitos = re.sub(
            r"\D",
            "",
            telefone or "",
        )

        if digitos.startswith("00"):
            digitos = digitos[2:]

        if len(digitos) in {
            10,
            11,
        }:
            digitos = f"55{digitos}"

        if (
            len(digitos)
            in {
                12,
                13,
            }
            and digitos.startswith("55")
        ):
            return f"+{digitos}"

        return None

    @classmethod
    def extrair_telefones(cls, texto):
        telefones = set()

        for telefone in cls.padrao_telefone.findall(
            texto or ""
        ):
            telefone_normalizado = (
                cls.normalizar_telefone(telefone)
            )

            if telefone_normalizado:
                telefones.add(
                    telefone_normalizado
                )

        return telefones

    @classmethod
    def normalizar_url_publica(cls, url):
        partes = urlparse(url)

        return urlunparse(
            (
                partes.scheme.lower() or "https",
                partes.netloc.lower(),
                partes.path.rstrip("/"),
                "",
                "",
                "",
            )
        )

    @classmethod
    def identificar_rede_social(cls, url):
        hostname = (
            urlparse(url).hostname or ""
        ).lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        for dominio, tipo in (
            cls.dominios_redes_sociais.items()
        ):
            if (
                hostname == dominio
                or hostname.endswith(
                    f".{dominio}"
                )
            ):
                return tipo

        return None

    @classmethod
    def extrair_whatsapp(cls, url):
        partes = urlparse(url)
        hostname = (
            partes.hostname or ""
        ).lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        if not (
            hostname == "wa.me"
            or hostname.endswith(
                ".whatsapp.com"
            )
            or hostname == "whatsapp.com"
        ):
            return None

        parametros = parse_qs(
            partes.query
        )
        telefone = (
            parametros.get("phone", [None])[0]
            or partes.path.strip("/").split("/")[0]
        )
        telefone_normalizado = cls.normalizar_telefone(
            unquote(telefone or "")
        )

        return (
            telefone_normalizado
            or cls.normalizar_url_publica(url)
        )

    def extrair_contatos_de_links(
        self,
        response,
    ):
        for href in response.css(
            "a::attr(href)"
        ).getall():
            href = href.strip()

            if not href:
                continue

            href_lower = href.lower()

            if href_lower.startswith("mailto:"):
                email = unquote(
                    href.split(":", 1)[1]
                ).split("?", 1)[0]

                for email_extraido in self.extrair_emails(
                    email
                ):
                    yield (
                        "email",
                        email_extraido,
                    )

                continue

            if href_lower.startswith("tel:"):
                telefone = self.normalizar_telefone(
                    href.split(":", 1)[1]
                )

                if telefone:
                    yield (
                        "telefone",
                        telefone,
                    )

                continue

            url_completa = response.urljoin(href)

            whatsapp = self.extrair_whatsapp(
                url_completa
            )

            if whatsapp:
                yield (
                    "whatsapp",
                    whatsapp,
                )
                continue

            tipo_rede_social = (
                self.identificar_rede_social(
                    url_completa
                )
            )

            if tipo_rede_social:
                yield (
                    tipo_rede_social,
                    self.normalizar_url_publica(
                        url_completa
                    ),
                )

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
            item = self.criar_item_contato(
                "email",
                email,
                response.url,
            )

            if item:
                yield item

        texto_visivel = " ".join(
            response.css("body ::text").getall()
        )

        telefones_da_pagina = self.extrair_telefones(
            texto_visivel
        )

        for telefone in telefones_da_pagina:
            item = self.criar_item_contato(
                "telefone",
                telefone,
                response.url,
            )

            if item:
                yield item

        for tipo, valor in self.extrair_contatos_de_links(
            response
        ):
            item = self.criar_item_contato(
                tipo,
                valor,
                response.url,
            )

            if item:
                yield item

    def criar_item_contato(
        self,
        tipo,
        valor,
        pagina_origem,
    ):
        chave = (
            tipo,
            valor,
        )

        if chave in self.contatos_encontrados:
            return None

        self.contatos_encontrados.add(chave)

        if tipo == "email":
            self.emails_encontrados.add(valor)
            self.relatorio.adicionar_email(valor)
        else:
            self.relatorio.adicionar_contato(
                tipo,
                valor,
            )

        return {
            "tipo": tipo,
            "valor": valor,
            "email": (
                valor
                if tipo == "email"
                else None
            ),
            "pagina_origem": pagina_origem,
        }

    def closed(self, reason):
        self.relatorio.finalizar()
        self.relatorio.salvar()

        self.logger.info(
            "Relatório da varredura salvo "
            "em relatorio.json"
        )
