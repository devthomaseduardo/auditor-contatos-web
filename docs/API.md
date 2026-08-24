# Documentação da API

Referência dos endpoints da API do Auditor de Contatos Web.

Para testar no Postman, use o guia [POSTMAN.md](POSTMAN.md) e os arquivos em `docs/postman/`.

## Base URL

Ambiente local padrão:

```text
http://127.0.0.1:8010
```

Ambiente Docker padrão:

```text
http://localhost:8000
```

Ambiente publicado:

```text
https://sua-api-publica.com
```

Para publicar a API, siga o guia [DEPLOY.md](DEPLOY.md).

## Documentação interativa

A FastAPI gera documentação automática:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

Exemplo:

```bash
curl -s http://127.0.0.1:8010/openapi.json | jq
```

## Autenticação

Esta primeira versão não exige autenticação.

Como o endpoint executa varreduras, use apenas em ambiente controlado e em domínios públicos autorizados.

## Formato das respostas

Todas as respostas são JSON.

Datas são retornadas em formato ISO 8601.

Campos de erro podem ser `null` quando a varredura terminou sem falha.

## Ciclo de vida da varredura

Status possíveis:

| Status | Descrição |
| --- | --- |
| `pendente` | Registro criado e execução agendada em background. |
| `em_andamento` | O processo Scrapy iniciou a varredura. |
| `concluida` | A varredura terminou e pelo menos uma página foi processada. |
| `erro` | A varredura falhou, excedeu timeout ou nenhuma página pública foi processada. |

Fluxo esperado:

```text
POST /varreduras
        |
        v
status: pendente
        |
        v
background task executa Scrapy
        |
        v
status: em_andamento
        |
        v
status: concluida ou erro
```

## Schemas

### Criar varredura

Request:

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `url` | string URL | Sim | URL pública inicial da varredura. |

Exemplo:

```json
{
  "url": "http://127.0.0.1:8765/index.html"
}
```

### Varredura

Response:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | integer | Identificador da varredura. |
| `site` | string | Domínio do site. |
| `url` | string | URL inicial usada naquela varredura. |
| `status` | string | Status atual da varredura. |
| `quantidade_paginas` | integer | Total de páginas processadas. |
| `quantidade_contatos` | integer | Total de contatos únicos salvos. |
| `inicio` | string datetime | Data/hora de criação ou início. |
| `fim` | string datetime ou null | Data/hora de finalização. |
| `erro` | string ou null | Mensagem de erro persistida. |

### Contato

Response:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | integer | Identificador do contato. |
| `tipo` | string | Tipo do contato extraído, como `email`, `telefone`, `whatsapp`, `instagram` ou `linkedin`. |
| `valor` | string | Valor normalizado do contato. |
| `email` | string ou null | E-mail normalizado quando `tipo = email`; `null` para outros tipos. |
| `pagina_origem` | string | Página onde o contato foi encontrado. |

## Endpoints

## `GET /health`

Verifica se a API está online.

### Exemplo

```bash
curl -s http://127.0.0.1:8010/health | jq
```

### Resposta `200`

```json
{
  "status": "ok"
}
```

## `POST /varreduras`

Cria uma nova varredura e agenda a execução em background.

O endpoint retorna `202 Accepted` porque o processamento não termina dentro da própria requisição. Após criar a varredura, consulte `GET /varreduras/{id}` até o status ser `concluida` ou `erro`.

### Exemplo

```bash
curl -s -X POST http://127.0.0.1:8010/varreduras \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8765/index.html"}' | jq
```

### Resposta `202`

```json
{
  "id": 1,
  "site": "127.0.0.1",
  "url": "http://127.0.0.1:8765/index.html",
  "status": "pendente",
  "mensagem": "Varredura adicionada para processamento"
}
```

### Erros possíveis

#### `422 Unprocessable Entity`

Ocorre quando a URL não passa na validação do Pydantic.

Exemplo de request inválido:

```json
{
  "url": "site-sem-protocolo.com"
}
```

#### `400 Bad Request`

Ocorre se a URL passar pela validação inicial, mas não tiver domínio interpretável.

## `GET /varreduras`

Lista o histórico de varreduras, ordenado da mais recente para a mais antiga.

### Exemplo

```bash
curl -s http://127.0.0.1:8010/varreduras | jq
```

### Resposta `200`

```json
[
  {
    "id": 2,
    "site": "127.0.0.1",
    "url": "http://127.0.0.1:8765/nao-existe.html",
    "status": "erro",
    "quantidade_paginas": 0,
    "quantidade_contatos": 0,
    "inicio": "2026-08-22T22:03:02.843215",
    "fim": "2026-08-22T22:03:04.553873",
    "erro": "HTTP 404 ao acessar http://127.0.0.1:8765/nao-existe.html"
  },
  {
    "id": 1,
    "site": "127.0.0.1",
    "url": "http://127.0.0.1:8765/index.html",
    "status": "concluida",
    "quantidade_paginas": 2,
    "quantidade_contatos": 8,
    "inicio": "2026-08-22T22:02:52.822812",
    "fim": "2026-08-22T22:02:56.709928",
    "erro": null
  }
]
```

## `GET /varreduras/{varredura_id}`

Busca uma varredura específica por ID.

### Exemplo

```bash
curl -s http://127.0.0.1:8010/varreduras/1 | jq
```

### Resposta `200`

```json
{
  "id": 1,
  "site": "127.0.0.1",
  "url": "http://127.0.0.1:8765/index.html",
  "status": "concluida",
  "quantidade_paginas": 2,
  "quantidade_contatos": 8,
  "inicio": "2026-08-22T22:02:52.822812",
  "fim": "2026-08-22T22:02:56.709928",
  "erro": null
}
```

### Resposta `404`

```json
{
  "detail": "Varredura não encontrada"
}
```

## `GET /varreduras/{varredura_id}/contatos`

Lista os contatos encontrados em uma varredura.

### Exemplo

```bash
curl -s http://127.0.0.1:8010/varreduras/1/contatos | jq
```

### Resposta `200`

```json
[
  {
    "id": 1,
    "tipo": "email",
    "valor": "contato@empresateste.com.br",
    "email": "contato@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/index.html"
  },
  {
    "id": 2,
    "tipo": "telefone",
    "valor": "+551140028922",
    "email": null,
    "pagina_origem": "http://127.0.0.1:8765/index.html"
  },
  {
    "id": 3,
    "tipo": "instagram",
    "valor": "https://www.instagram.com/empresa.teste",
    "email": null,
    "pagina_origem": "http://127.0.0.1:8765/index.html"
  },
  {
    "id": 4,
    "tipo": "email",
    "valor": "comercial@empresateste.com.br",
    "email": "comercial@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  },
  {
    "id": 5,
    "tipo": "email",
    "valor": "suporte@empresateste.com.br",
    "email": "suporte@empresateste.com.br",
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  },
  {
    "id": 6,
    "tipo": "telefone",
    "valor": "+5511912345678",
    "email": null,
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  },
  {
    "id": 7,
    "tipo": "whatsapp",
    "valor": "+5511912345678",
    "email": null,
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  },
  {
    "id": 8,
    "tipo": "linkedin",
    "valor": "https://www.linkedin.com/company/empresa-teste",
    "email": null,
    "pagina_origem": "http://127.0.0.1:8765/contato.html"
  }
]
```

### Resposta `404`

```json
{
  "detail": "Varredura não encontrada"
}
```

## Exemplo completo no terminal

Crie a varredura:

```bash
VARREDURA_ID=$(curl -s -X POST http://127.0.0.1:8010/varreduras \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8765/index.html"}' | jq -r '.id')
```

Aguarde o background:

```bash
sleep 4
```

Consulte o status:

```bash
curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID" | jq
```

Liste os contatos:

```bash
curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID/contatos" | jq
```

## Polling recomendado

Para acompanhar até terminar:

```bash
while true; do
  RESPOSTA=$(curl -s "http://127.0.0.1:8010/varreduras/$VARREDURA_ID")
  STATUS=$(echo "$RESPOSTA" | jq -r '.status')

  echo "$RESPOSTA" | jq

  if [ "$STATUS" = "concluida" ] || [ "$STATUS" = "erro" ]; then
    break
  fi

  sleep 2
done
```

## Observações de comportamento

- E-mails são normalizados para minúsculas.
- Telefones brasileiros são normalizados com código do país, por exemplo `+5511912345678`.
- Links sociais são salvos sem parâmetros de rastreamento.
- Contatos duplicados na mesma varredura são ignorados por `tipo` e `valor`.
- A URL inicial fica salva na própria varredura.
- A entidade `Site` representa o domínio.
- A entidade `Varredura` representa uma execução específica.
- A entidade `Contato` representa um dado público encontrado em uma varredura.
- O subprocesso do Scrapy tem timeout de 120 segundos.
- Mensagens de erro longas são limitadas antes de serem persistidas.

## Boas práticas de uso

- Teste primeiro com o domínio local em `teste/`.
- Use domínio real apenas quando houver autorização.
- Evite executar muitas varreduras seguidas no mesmo domínio.
- Mantenha `ROBOTSTXT_OBEY = True`.
- Para demonstração técnica, mostre o Swagger e depois o fluxo com `curl`.
