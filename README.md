# Auditor de Contatos Web

API backend para auditar páginas públicas de um domínio, localizar e-mails de contato e registrar o histórico das varreduras em banco de dados.

Este projeto foi criado como MVP técnico de portfólio para demonstrar um fluxo real de crawler, API, persistência, execução em background, tratamento de erro, Docker e testes automatizados.

## Demo online

- API: <https://auditor-contatos-web.onrender.com>
- Swagger: <https://auditor-contatos-web.onrender.com/docs>
- Healthcheck: <https://auditor-contatos-web.onrender.com/health>
- Histórico de varreduras: <https://auditor-contatos-web.onrender.com/varreduras>
- Coleção Postman: [`docs/postman/auditor-contatos-web.postman_collection.json`](docs/postman/auditor-contatos-web.postman_collection.json)

Observação: a API está hospedada no plano gratuito do Render. Depois de alguns minutos sem uso, a primeira requisição pode demorar um pouco porque o serviço precisa iniciar novamente.

## O que o projeto faz

O Auditor de Contatos Web recebe uma URL pública, executa uma varredura controlada no mesmo domínio e procura e-mails visíveis no HTML das páginas. Ele prioriza páginas comuns de contato, como `contato`, `contact`, `sobre`, `about`, `suporte` e `support`.

Ao final da execução, a API permite consultar:

- histórico das varreduras;
- status de cada varredura;
- quantidade de páginas processadas;
- quantidade de contatos encontrados;
- mensagens de erro;
- lista de e-mails encontrados e a página de origem.

O projeto não tem frontend próprio nesta versão. A documentação interativa da FastAPI em `/docs` já é suficiente para demonstrar o backend.

Documentação técnica dos endpoints: [docs/API.md](docs/API.md).

Coleção e guia do Postman: [docs/POSTMAN.md](docs/POSTMAN.md).

Guia para deixar a API online: [docs/DEPLOY.md](docs/DEPLOY.md).

## Como funciona

Fluxo principal:

1. A API recebe uma URL em `POST /varreduras`.
2. Um registro é criado no banco com status `pendente`.
3. A FastAPI agenda a execução em background.
4. O background executa o spider Scrapy em subprocesso.
5. O spider visita a URL inicial e busca links importantes dentro do mesmo domínio.
6. O pipeline normaliza e deduplica os e-mails encontrados.
7. O banco guarda sites, varreduras, contatos, datas, status e erro.
8. A API expõe os resultados por endpoints REST.

Ao acessar a raiz da API, `GET /`, o usuário é redirecionado para `/docs`, facilitando a demonstração pública do projeto.

Status possíveis:

- `pendente`: varredura criada e aguardando execução.
- `em_andamento`: Scrapy iniciou o processamento.
- `concluida`: pelo menos uma página foi processada e o fluxo terminou.
- `erro`: a URL falhou, retornou erro HTTP, excedeu timeout ou nenhuma página pública foi processada.

## Stack

- Python 3.14
- FastAPI
- Scrapy
- SQLAlchemy
- PostgreSQL
- Psycopg 3
- Pytest
- Docker e Docker Compose

## Uso responsável

Este projeto deve ser usado apenas em páginas públicas e domínios em que exista autorização para varredura.

Configurações importantes:

- `ROBOTSTXT_OBEY = True`
- `DOWNLOAD_DELAY = 1`
- `CONCURRENT_REQUESTS_PER_DOMAIN = 1`
- limite interno de 10 páginas por varredura

Não use para spam, coleta abusiva, áreas privadas, páginas autenticadas ou domínios de terceiros sem autorização.

## Requisitos

Para rodar localmente:

- Python 3.14
- `pip`
- `curl`
- `jq` para formatar JSON no terminal

Para rodar com Docker:

- Docker
- Docker Compose

## Configuração

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Exemplo usando PostgreSQL local:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/auditor_contatos
```

Exemplo usando SQLite para teste rápido:

```bash
export DATABASE_URL=sqlite+pysqlite:///auditor_demo.db
```

SQLite é útil para demonstração local. PostgreSQL é o caminho recomendado para apresentar o projeto como backend mais próximo de produção.

## Rodando com Docker

Suba API e PostgreSQL:

```bash
docker compose up --build
```

Acesse:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

O `docker-compose.yml` cria dois serviços:

- `api`: FastAPI + Scrapy
- `db`: PostgreSQL

## Deploy

Para deixar a API no ar, o caminho mais simples para portfólio é publicar pelo GitHub usando **Render** ou **Railway** com o `Dockerfile` da raiz e um PostgreSQL gerenciado.

Variáveis mínimas no ambiente de produção:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/banco
PORT=8000
```

Depois do deploy, valide:

```bash
curl -s https://sua-api-publica.com/health
```

Abra também:

```text
https://sua-api-publica.com/docs
```

O passo a passo completo está em [docs/DEPLOY.md](docs/DEPLOY.md).

Deploy atual:

```text
https://auditor-contatos-web.onrender.com
```

## Rodando localmente sem Docker

Crie e ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure o banco para teste rápido com SQLite:

```bash
export DATABASE_URL=sqlite+pysqlite:///auditor_demo.db
```

Crie as tabelas:

```bash
python -m auditor.criar_banco
```

Suba a API:

```bash
uvicorn auditor.api:app --reload --port 8010
```

Acesse:

- API: `http://127.0.0.1:8010`
- Swagger: `http://127.0.0.1:8010/docs`

Se a porta `8010` estiver ocupada, use outra porta:

```bash
uvicorn auditor.api:app --reload --port 8020
```

## Teste controlado local

O diretório `teste/` contém páginas HTML simples para demonstrar o crawler sem depender de uma empresa real.

Esse teste mostra:

- URL inicial processada;
- descoberta de link para página de contato;
- extração de e-mails;
- deduplicação de e-mail repetido;
- gravação no banco;
- consulta via API.

Terminal 1: suba o site de teste.

```bash
python -m http.server 8765 -d teste
```

Terminal 2: suba a API.

```bash
source .venv/bin/activate
export DATABASE_URL=sqlite+pysqlite:///auditor_demo.db
python -m auditor.criar_banco
uvicorn auditor.api:app --reload --port 8010
```

Terminal 3: execute a varredura pela API.

```bash
VARREDURA_ID=$(curl -s -X POST http://127.0.0.1:8010/varreduras \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8765/index.html"}' | jq -r '.id')

echo "Varredura criada: $VARREDURA_ID"
```

Aguarde alguns segundos e consulte o resultado:

```bash
sleep 4

curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID" | jq
```

Consulte os contatos encontrados:

```bash
curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID/contatos" | jq
```

Resultado esperado no teste local:

```json
{
  "status": "concluida",
  "quantidade_paginas": 2,
  "quantidade_contatos": 3,
  "erro": null
}
```

Contatos esperados:

```json
[
  {
    "email": "contato@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/index.html"
  },
  {
    "email": "suporte@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  },
  {
    "email": "comercial@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  }
]
```

## Teste de erro

Use uma página inexistente no site local:

```bash
ERRO_ID=$(curl -s -X POST http://127.0.0.1:8010/varreduras \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8765/nao-existe.html"}' | jq -r '.id')

sleep 3

curl -s "http://127.0.0.1:8010/varreduras/$ERRO_ID" | jq
```

Resultado esperado:

```json
{
  "status": "erro",
  "quantidade_paginas": 0,
  "quantidade_contatos": 0,
  "erro": "HTTP 404 ao acessar http://127.0.0.1:8765/nao-existe.html"
}
```

Esse teste comprova que falhas não ficam silenciosas: a varredura termina com `status = erro` e mensagem persistida no banco.

## Teste com domínio real autorizado

Use apenas um domínio próprio, de cliente ou com autorização explícita.

Exemplo usando a API online:

```bash
BASE_URL=https://auditor-contatos-web.onrender.com

VARREDURA_ID=$(curl -s -X POST "$BASE_URL/varreduras" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://thomaseduardo.com.br"}' | jq -r '.id')

echo "Varredura criada: $VARREDURA_ID"

sleep 8

curl -s "$BASE_URL/varreduras/$VARREDURA_ID" | jq
curl -s "$BASE_URL/varreduras/$VARREDURA_ID/contatos" | jq
```

Exemplo usando a API local:

```bash
VARREDURA_ID=$(curl -s -X POST http://127.0.0.1:8010/varreduras \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://thomaseduardo.com.br"}' | jq -r '.id')

echo "Varredura criada: $VARREDURA_ID"

sleep 8

curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID" | jq
curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID/contatos" | jq
```

O resultado pode variar conforme o site, `robots.txt`, redirecionamentos e disponibilidade do domínio.

## Endpoints

### `GET /health`

Verifica se a API está online.

```bash
curl -s http://127.0.0.1:8010/health | jq
```

Resposta:

```json
{
  "status": "ok"
}
```

### `POST /varreduras`

Cria uma nova varredura.

```bash
curl -s -X POST http://127.0.0.1:8010/varreduras \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8765/index.html"}' | jq
```

Resposta:

```json
{
  "id": 1,
  "site": "127.0.0.1",
  "url": "http://127.0.0.1:8765/index.html",
  "status": "pendente",
  "mensagem": "Varredura adicionada para processamento"
}
```

### `GET /varreduras`

Lista o histórico das varreduras.

```bash
curl -s http://127.0.0.1:8010/varreduras | jq
```

### `GET /varreduras/{id}`

Consulta uma varredura específica.

```bash
curl -s http://127.0.0.1:8010/varreduras/1 | jq
```

Exemplo:

```json
{
  "id": 1,
  "site": "127.0.0.1",
  "url": "http://127.0.0.1:8765/index.html",
  "status": "concluida",
  "quantidade_paginas": 2,
  "quantidade_contatos": 3,
  "inicio": "2026-08-22T22:02:52.822812",
  "fim": "2026-08-22T22:02:56.709928",
  "erro": null
}
```

### `GET /varreduras/{id}/contatos`

Lista os contatos encontrados em uma varredura.

```bash
curl -s http://127.0.0.1:8010/varreduras/1/contatos | jq
```

Exemplo:

```json
[
  {
    "id": 1,
    "email": "contato@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/index.html"
  }
]
```

## Rodando testes automatizados

```bash
pytest
```

A suíte cobre:

- extração e normalização de e-mails;
- deduplicação no spider;
- deduplicação no pipeline;
- criação de varredura;
- consulta de varredura;
- listagem de contatos;
- preservação da URL inicial por varredura;
- falha de execução com `status = erro` e mensagem salva.

## Testando o spider diretamente

Também é possível rodar o Scrapy sem passar pela API:

```bash
export DATABASE_URL=sqlite+pysqlite:///auditor_demo.db
python -m auditor.criar_banco
scrapy crawl contatos -a url=http://127.0.0.1:8765/index.html
```

Esse modo é útil para depurar o crawler, mas a demonstração principal do projeto deve passar pela API, porque ela mostra histórico, background task e endpoints.

## Estrutura do projeto

```text
auditor/
  api.py              # Endpoints FastAPI e execução em background
  database.py         # Engine, sessão e criação de tabelas
  models.py           # Modelos SQLAlchemy
  pipelines.py        # Deduplicação e persistência dos contatos
  relatorio.py        # Relatório JSON local gerado pela spider
  settings.py         # Configurações do Scrapy
  spiders/
    contatos.py       # Spider de varredura e extração de e-mails
tests/
  conftest.py
  test_api.py
  test_pipeline.py
  test_spider.py
teste/
  index.html          # Página local para demonstração
  contato.html        # Página de contato local
docker-compose.yml
Dockerfile
requirements.txt
```

## Como apresentar no portfólio

Título sugerido:

```text
Auditor de Contatos Web
```

Descrição curta:

```text
API backend em Python que recebe uma URL autorizada, executa uma varredura com Scrapy, extrai e-mails públicos, deduplica contatos, salva histórico em PostgreSQL e expõe os resultados por endpoints REST com FastAPI.
```

Pontos fortes para demonstrar:

- API REST com documentação automática em `/docs`;
- crawler com Scrapy respeitando `robots.txt`;
- execução assíncrona com `BackgroundTasks`;
- histórico de varreduras;
- tratamento de sucesso e falha;
- PostgreSQL com SQLAlchemy;
- Docker Compose para API + banco;
- testes automatizados cobrindo fluxo principal;
- deploy online no Render;
- coleção Postman para demonstração;
- uso responsável em páginas públicas e domínios autorizados.

Links para apresentação:

- API online: <https://auditor-contatos-web.onrender.com>
- Swagger: <https://auditor-contatos-web.onrender.com/docs>
- Healthcheck: <https://auditor-contatos-web.onrender.com/health>
- Documentação dos endpoints: [`docs/API.md`](docs/API.md)
- Guia Postman: [`docs/POSTMAN.md`](docs/POSTMAN.md)
- Guia de deploy: [`docs/DEPLOY.md`](docs/DEPLOY.md)

Stack para destacar:

```text
Python, FastAPI, Scrapy, SQLAlchemy, PostgreSQL, Docker, Pytest e Render.
```

Resumo curto:

> Backend em Python que recebe uma URL autorizada, executa uma varredura com Scrapy, extrai e-mails públicos, deduplica contatos, salva histórico em banco e expõe os resultados por API FastAPI.

## Status do MVP

O MVP entrega o núcleo funcional para portfólio backend. A próxima evolução natural seria adicionar autenticação, fila real de jobs, painel frontend ou exportação CSV, mas a primeira versão já demonstra crawler, API, persistência, testes e Docker.
