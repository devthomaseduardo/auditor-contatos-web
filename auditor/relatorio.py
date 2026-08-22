import json
from datetime import datetime, timezone


class RelatorioVarredura:
    def __init__(self, dominio):
        self.dominio = dominio
        self.inicio = datetime.now(timezone.utc)
        self.fim = None

        self.paginas_visitadas = set()
        self.emails_encontrados = set()

    def adicionar_pagina(self, url):
        self.paginas_visitadas.add(url)

    def adicionar_email(self, email):
        self.emails_encontrados.add(email)

    def finalizar(self):
        self.fim = datetime.now(timezone.utc)

    def gerar_dados(self):
        return {
            "dominio": self.dominio,
            "quantidade_paginas": len(
                self.paginas_visitadas
            ),
            "quantidade_emails": len(
                self.emails_encontrados
            ),
            "paginas_visitadas": sorted(
                self.paginas_visitadas
            ),
            "emails_encontrados": sorted(
                self.emails_encontrados
            ),
            "inicio": self.inicio.isoformat(),
            "fim": (
                self.fim.isoformat()
                if self.fim
                else None
            ),
        }

    def salvar(self, caminho="relatorio.json"):
        dados = self.gerar_dados()

        with open(
            caminho,
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )
