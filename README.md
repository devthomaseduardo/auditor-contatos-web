# Auditor de Contatos Web

API backend para auditar páginas públicas de um domínio, localizar e-mails de contato e registrar o histórico das varreduras em banco de dados.

O projeto foi criado como MVP técnico de portfólio para demonstrar crawler com Scrapy, API com FastAPI, persistência com SQLAlchemy/PostgreSQL, execução em background, tratamento de erros e testes automatizados.

## Objetivo

Automatizar uma tarefa comum em operações comerciais e suporte: visitar um site autorizado, priorizar páginas relevantes como contato, sobre e suporte, extrair e-mails públicos, remover duplicidades e gerar um histórico consultável por API.

O projeto não deve ser usado para coleta abusiva, spam, scraping de áreas privadas ou varredura de domínios sem autorização.

## Arquitetura

Fluxo principal:

1. A API recebe uma URL em `POST /varreduras`.
2. Um registro de varredura é criado com status `pendente`.
3. A FastAPI agenda a execução em background.
4. O background executa o spider Scrapy em subprocesso.
5. A spider visita a URL inicial e páginas importantes encontradas no mesmo domínio.
6. O pipeline normaliza e deduplica e-mails.
7. O PostgreSQL guarda sites, varreduras, contatos, status, datas e mensagens de erro.
8. A API expõe histórico, detalhe da varredura e contatos encontrados.

## Stack

- Python 3.14
- FastAPI
- Scrapy
- SQLAlchemy
- PostgreSQL
- Psycopg 3
- Pytest
- Docker e Docker Compose

## Uso responsável do crawler

Por padrão, o projeto usa:

- `ROBOTSTXT_OBEY = True`
- `DOWNLOAD_DELAY = 1`
- `CONCURRENT_REQUESTS_PER_DOMAIN = 1`
- limite interno de 10 páginas por varredura

Use apenas em páginas públicas e em domínios próprios, de clientes ou com autorização explícita.

## Variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Exemplo:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/auditor_contatos
```

Para testes locais sem PostgreSQL, também é possível apontar para SQLite:

```bash
DATABASE_URL=sqlite+pysqlite:///auditor_local.db
```

## Rodando com Docker

```bash
docker compose up --build
```

A API ficará disponível em:

- `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m auditor.criar_banco
uvicorn auditor.api:app --reload
```

## Endpoints

### Healthcheck

```http
GET /health
```

Resposta:

```json
{
  "status": "ok"
}
```

### Criar varredura

```http
POST /varreduras
Content-Type: application/json

{
  "url": "https://example.com"
}
```

Resposta:

```json
{
  "id": 1,
  "site": "example.com",
  "url": "https://example.com/",
  "status": "pendente",
  "mensagem": "Varredura adicionada para processamento"
}
```

### Listar varreduras

```http
GET /varreduras
```

Resposta:

```json
[
  {
    "id": 1,
    "site": "example.com",
    "url": "https://example.com/",
    "status": "concluida",
    "quantidade_paginas": 2,
    "quantidade_contatos": 1,
    "inicio": "2026-08-22T18:00:00Z",
    "fim": "2026-08-22T18:00:05Z",
    "erro": null
  }
]
```

### Detalhar varredura

```http
GET /varreduras/1
```

### Listar contatos encontrados

```http
GET /varreduras/1/contatos
```

Resposta:

```json
[
  {
    "id": 1,
    "email": "contato@example.com",
    "pagina_origem": "https://example.com/contato"
  }
]
```

## Tratamento de erro

Quando o Scrapy falha, a varredura é marcada como `erro` e a mensagem fica salva no campo `erro`.

Exemplo:

```json
{
  "id": 2,
  "site": "example.invalid",
  "url": "https://example.invalid/",
  "status": "erro",
  "quantidade_paginas": 0,
  "quantidade_contatos": 0,
  "inicio": "2026-08-22T18:10:00Z",
  "fim": "2026-08-22T18:10:02Z",
  "erro": "Falha ao acessar https://example.invalid/: DNS lookup failed"
}
```

## Testes

```bash
pytest
```

A suíte cobre:

- extração e normalização de e-mails
- deduplicação no spider e no pipeline
- criação e consulta de varreduras
- listagem de contatos
- falha de subprocesso com `status = erro` e mensagem salva

## Teste controlado local

O diretório `teste/` contém páginas HTML simples para uma varredura segura em ambiente local.

Em um terminal:

```bash
python -m http.server 8765 -d teste
```

Em outro terminal:

```bash
DATABASE_URL=sqlite+pysqlite:///auditor_local.db python -m auditor.criar_banco
DATABASE_URL=sqlite+pysqlite:///auditor_local.db scrapy crawl contatos -a url=http://127.0.0.1:8765/index.html
```

Depois consulte o banco ou use a API com a mesma `DATABASE_URL`.

## Estrutura

```text
auditor/
  api.py
  database.py
  models.py
  pipelines.py
  relatorio.py
  settings.py
  spiders/
    contatos.py
tests/
  test_api.py
  test_pipeline.py
  test_spider.py
docker-compose.yml
Dockerfile
requirements.txt
```

## Status do MVP

Este MVP entrega backend funcional com crawler, API, persistência, execução em background, histórico, tratamento de erro, Docker e testes. O frontend não faz parte desta primeira versão, porque a FastAPI já fornece documentação interativa em `/docs`.
