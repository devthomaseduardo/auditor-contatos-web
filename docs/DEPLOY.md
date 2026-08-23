# Deploy da API

Este guia mostra como deixar a API do Auditor de Contatos Web no ar.

## Recomendação

Para este projeto, não use uma hospedagem pensada só para funções serverless simples.

A API executa:

- FastAPI;
- Scrapy em subprocesso;
- tarefas em background;
- PostgreSQL;
- escrita de histórico no banco.

Por isso, as opções mais adequadas são:

1. **Render ou Railway** para publicar rápido com GitHub + Dockerfile + PostgreSQL gerenciado.
2. **VPS com Docker Compose** para ter mais controle, domínio próprio e HTTPS.

Para portfólio, o caminho mais simples é **Render ou Railway**. Para produção controlada, o melhor caminho é **VPS com Docker Compose**.

## Antes do deploy

Confirme que o repositório está atualizado no GitHub:

```bash
git status
git push origin main
```

Confirme que a API sobe localmente:

```bash
docker compose up --build
```

Teste:

```bash
curl -s http://localhost:8000/health
```

Resposta esperada:

```json
{
  "status": "ok"
}
```

Nesta versão, a API cria as tabelas automaticamente ao iniciar. Por isso, depois de configurar `DATABASE_URL`, basta subir o serviço e conferir os logs do primeiro boot.

## Variáveis obrigatórias

| Variável | Exemplo | Descrição |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/db` | URL de conexão com PostgreSQL. |
| `PORT` | `8000` | Porta em que a API deve escutar. |

O projeto aceita URLs começando com:

- `postgresql+psycopg://`
- `postgresql://`
- `postgres://`

Internamente, as duas últimas são normalizadas para `postgresql+psycopg://`.

## Opção 1: Railway

Use quando quiser publicar rápido a partir do GitHub.

Passos:

1. Suba o repositório para o GitHub.
2. Crie um projeto no Railway.
3. Conecte o repositório.
4. Garanta que o Railway detectou o `Dockerfile` na raiz.
5. Adicione um serviço PostgreSQL.
6. Configure `DATABASE_URL` usando a URL interna do PostgreSQL.
7. Configure `PORT=8000` se necessário.
8. Faça o deploy.
9. Abra a URL pública gerada pelo Railway.
10. Teste `/health` e `/docs`.

Endpoints para conferir:

```text
https://sua-api.up.railway.app/health
https://sua-api.up.railway.app/docs
```

## Opção 2: Render

Use quando quiser web service com build por Dockerfile e banco gerenciado.

Passos:

1. Suba o repositório para o GitHub.
2. No Render, crie um novo Web Service.
3. Selecione o repositório.
4. Use deploy via Dockerfile.
5. Crie um banco Render Postgres.
6. Configure `DATABASE_URL` no Web Service.
7. Configure `PORT=8000` se necessário.
8. Faça o deploy.
9. Teste `/health` e `/docs`.

Endpoints para conferir:

```text
https://sua-api.onrender.com/health
https://sua-api.onrender.com/docs
```

## Opção 3: VPS com Docker Compose

Use quando quiser controle total do servidor.

Passos gerais:

1. Crie uma VPS com Ubuntu.
2. Aponte um subdomínio para o IP da VPS, por exemplo `api.seudominio.com.br`.
3. Instale Docker e Docker Compose.
4. Clone o repositório na VPS.
5. Configure as variáveis de ambiente.
6. Suba API e PostgreSQL com Docker Compose.
7. Coloque Caddy ou Nginx na frente para HTTPS.

Exemplo:

```bash
git clone https://github.com/devthomaseduardo/auditor-contatos-web.git
cd auditor-contatos-web
docker compose up -d --build
```

Teste local na VPS:

```bash
curl -s http://127.0.0.1:8000/health
```

Depois configure proxy reverso para expor:

```text
https://api.seudominio.com.br
```

Em produção, não exponha o PostgreSQL publicamente. Remova ou restrinja:

```yaml
ports:
  - "5432:5432"
```

do serviço `db`, a menos que exista um motivo claro para acesso externo.

## Teste depois do deploy

Substitua `BASE_URL` pela URL pública da API.

```bash
BASE_URL=https://sua-api-publica.com

curl -s "$BASE_URL/health"
```

Crie uma varredura controlada:

```bash
VARREDURA_ID=$(curl -s -X POST "$BASE_URL/varreduras" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://thomaseduardo.com.br"}' | jq -r '.id')
```

Consulte o status:

```bash
sleep 8

curl -s "$BASE_URL/varreduras/$VARREDURA_ID" | jq
```

Liste os contatos:

```bash
curl -s "$BASE_URL/varreduras/$VARREDURA_ID/contatos" | jq
```

## Checklist de produção

- [ ] Repositório no GitHub atualizado.
- [ ] `Dockerfile` presente na raiz.
- [ ] PostgreSQL configurado.
- [ ] `DATABASE_URL` configurado no ambiente.
- [ ] API respondendo em `/health`.
- [ ] Swagger abrindo em `/docs`.
- [ ] Domínio real testado apenas com autorização.
- [ ] Logs acompanhados no primeiro deploy.
- [ ] PostgreSQL não exposto publicamente em produção.
- [ ] HTTPS configurado quando usar domínio próprio.

## O que evitar

- Não publique sem banco PostgreSQL persistente.
- Não use domínio de terceiros sem autorização.
- Não rode várias varreduras agressivas em sequência.
- Não deixe credenciais no repositório.
- Não exponha a porta do PostgreSQL para a internet sem necessidade.

## Referências oficiais

- Render Docker: https://render.com/docs/docker
- Render Web Services: https://render.com/docs/web-services
- Railway Dockerfile: https://docs.railway.com/builds/dockerfiles
- Railway Deployments: https://docs.railway.com/deployments/reference
- Fly.io FastAPI: https://fly.io/docs/python/frameworks/fastapi/
- Caddy reverse proxy: https://caddyserver.com/docs/quick-starts/reverse-proxy
