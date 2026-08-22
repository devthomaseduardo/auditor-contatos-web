from auditor.database import criar_tabelas as criar_tabelas_no_banco
from auditor.models import Site, Varredura, Contato


def criar_tabelas():
    _ = (Site, Varredura, Contato)

    criar_tabelas_no_banco()

    print("Tabelas criadas com sucesso.")


if __name__ == "__main__":
    criar_tabelas()
