import hashlib

from datetime import datetime, timezone

from scrapy.exceptions import DropItem
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from auditor.database import SessionLocal
from auditor.models import (
    Site,
    Varredura,
    Contato,
)


class AuditorPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        instancia = cls()

        instancia.crawler = crawler
        instancia.emails_processados = set()
        instancia.contatos_processados = set()
        instancia.sessao = None
        instancia.site = None
        instancia.varredura = None

        return instancia

    def open_spider(self):
        spider = self.crawler.spider

        spider.logger.info(
            "Pipeline iniciado"
        )

        self.sessao = SessionLocal()

        if spider.varredura_id:
            self.varredura = self.sessao.get(
                Varredura,
                spider.varredura_id,
            )

            if not self.varredura:
                raise ValueError(
                    "Varredura não encontrada"
                )

            self.varredura.status = (
                "em_andamento"
            )
            self.varredura.erro = None

            self.sessao.commit()

            spider.logger.info(
                f"Varredura "
                f"{self.varredura.id} "
                f"iniciada"
            )

            return

        dominio = spider.allowed_domains[0]
        url_inicial = spider.start_urls[0]

        consulta = select(Site).where(
            Site.dominio == dominio
        )

        self.site = self.sessao.scalar(
            consulta
        )

        if not self.site:
            self.site = Site(
                dominio=dominio,
                url=url_inicial,
            )

            self.sessao.add(self.site)
            self.sessao.commit()
            self.sessao.refresh(self.site)

        self.varredura = Varredura(
            site_id=self.site.id,
            status="em_andamento",
            url_inicial=url_inicial,
        )

        self.sessao.add(self.varredura)
        self.sessao.commit()
        self.sessao.refresh(
            self.varredura
        )

    def process_item(self, item):
        spider = self.crawler.spider

        tipo = (
            item.get("tipo")
            or (
                "email"
                if item.get("email")
                else None
            )
        )
        valor = (
            item.get("valor")
            or item.get("email")
        )
        pagina_origem = item.get(
            "pagina_origem"
        )

        if not tipo or not valor:
            return item

        tipo = tipo.strip().lower()
        valor = valor.strip()

        if tipo == "email":
            valor = valor.lower()

        chave = (
            tipo,
            valor,
        )

        if chave in self.contatos_processados:
            spider.logger.info(
                f"Contato duplicado ignorado: "
                f"{tipo} {valor}"
            )

            raise DropItem(
                f"Contato duplicado: {tipo} {valor}"
            )

        self.contatos_processados.add(chave)

        if tipo == "email":
            self.emails_processados.add(valor)

        email_legado = self.gerar_email_legado(
            tipo,
            valor,
        )

        contato = Contato(
            varredura_id=self.varredura.id,
            email=email_legado,
            tipo=tipo,
            valor=valor,
            pagina_origem=pagina_origem,
        )

        self.sessao.add(contato)

        try:
            self.sessao.commit()
        except IntegrityError as erro:
            self.sessao.rollback()

            raise DropItem(
                (
                    "Contato duplicado no banco: "
                    f"{tipo} {valor}"
                )
            ) from erro

        item["tipo"] = tipo
        item["valor"] = valor

        if tipo == "email":
            item["email"] = valor
        else:
            item.pop("email", None)

        spider.logger.info(
            f"Contato salvo no banco: {tipo} {valor}"
        )

        return item

    @staticmethod
    def gerar_email_legado(tipo, valor):
        if tipo == "email":
            return valor

        digest = hashlib.sha256(
            f"{tipo}:{valor}".encode("utf-8")
        ).hexdigest()[:32]

        return f"{tipo}:{digest}"

    def close_spider(self):
        spider = self.crawler.spider

        if not self.varredura:
            if self.sessao:
                self.sessao.close()

            return

        quantidade_paginas = len(
            spider.paginas_visitadas
        )
        erros = getattr(
            spider,
            "erros_varredura",
            [],
        )

        self.varredura.quantidade_paginas = (
            quantidade_paginas
        )
        self.varredura.quantidade_contatos = (
            len(self.contatos_processados)
        )
        self.varredura.fim = datetime.now(
            timezone.utc
        )

        if quantidade_paginas == 0:
            self.varredura.status = "erro"
            self.varredura.erro = (
                "; ".join(erros[:3])
                if erros
                else (
                    "Nenhuma página pública foi "
                    "processada. Verifique se o "
                    "domínio é acessível e autorizado."
                )
            )
        else:
            self.varredura.status = "concluida"
            self.varredura.erro = None

        self.sessao.commit()

        spider.logger.info(
            f"Varredura "
            f"{self.varredura.id} "
            f"finalizada com status "
            f"{self.varredura.status}"
        )

        spider.logger.info(
            f"{len(self.contatos_processados)} "
            f"contatos salvos"
        )

        self.sessao.close()
