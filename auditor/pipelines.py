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
        )

        self.sessao.add(self.varredura)
        self.sessao.commit()
        self.sessao.refresh(
            self.varredura
        )

    def process_item(self, item):
        spider = self.crawler.spider

        email = item.get("email")
        pagina_origem = item.get(
            "pagina_origem"
        )

        if not email:
            return item

        email = email.strip().lower()

        if email in self.emails_processados:
            spider.logger.info(
                f"E-mail duplicado ignorado: "
                f"{email}"
            )

            raise DropItem(
                f"E-mail duplicado: {email}"
            )

        self.emails_processados.add(email)

        contato = Contato(
            varredura_id=self.varredura.id,
            email=email,
            pagina_origem=pagina_origem,
        )

        self.sessao.add(contato)

        try:
            self.sessao.commit()
        except IntegrityError as erro:
            self.sessao.rollback()

            raise DropItem(
                f"E-mail duplicado no banco: {email}"
            ) from erro

        item["email"] = email

        spider.logger.info(
            f"E-mail salvo no banco: {email}"
        )

        return item

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
            len(self.emails_processados)
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
            f"{len(self.emails_processados)} "
            f"contatos salvos"
        )

        self.sessao.close()
