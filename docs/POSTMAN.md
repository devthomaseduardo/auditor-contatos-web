# Guia Postman

Este guia mostra como importar e testar a API do Auditor de Contatos Web no Postman.

## Arquivos

Importe estes dois arquivos:

- `docs/postman/auditor-contatos-web.postman_collection.json`
- `docs/postman/auditor-contatos-local.postman_environment.json`

## Preparar ambiente local

Terminal 1: suba o site local de teste.

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

Confirme que a API está online:

```bash
curl -s http://127.0.0.1:8010/health | jq
```

## Importar no Postman

1. Abra o Postman.
2. Clique em `Import`.
3. Selecione `docs/postman/auditor-contatos-web.postman_collection.json`.
4. Clique novamente em `Import`.
5. Selecione `docs/postman/auditor-contatos-local.postman_environment.json`.
6. No canto superior direito, selecione o environment `Auditor de Contatos Web - Local`.

## Variáveis do environment

| Variável | Valor padrão | Uso |
| --- | --- | --- |
| `base_url` | `http://127.0.0.1:8010` | URL da API local. |
| `local_site_url` | `http://127.0.0.1:8765` | URL do site local de teste. |
| `url_real_autorizada` | `https://thomaseduardo.com.br` | Domínio real autorizado para teste. |
| `varredura_id` | vazio | Preenchida automaticamente após criar uma varredura. |
| `erro_id` | vazio | Preenchida automaticamente após criar uma varredura de erro. |
| `ultima_url_varredura` | vazio | Preenchida automaticamente para validar URL inicial. |
| `ultima_url_erro` | vazio | Preenchida automaticamente para validar URL de erro. |

Se usar outra porta na API, altere `base_url`.

Se usar outro site local, altere `local_site_url`.

## Ordem recomendada para demonstrar

Use a pasta `Health e documentação`:

1. `Healthcheck`
2. `OpenAPI JSON`
3. `Swagger UI`

Use a pasta `Demonstração local`:

1. `Criar varredura local`
2. Aguarde 3 a 5 segundos.
3. `Consultar varredura local`
4. Se ainda estiver `em_andamento`, aguarde e envie novamente.
5. `Listar contatos da varredura local`
6. `Criar varredura local com erro 404`
7. Aguarde 2 a 4 segundos.
8. `Consultar varredura local com erro`

Resultado esperado na varredura local:

```json
{
  "status": "concluida",
  "quantidade_paginas": 2,
  "quantidade_contatos": 3,
  "erro": null
}
```

Resultado esperado no erro 404:

```json
{
  "status": "erro",
  "quantidade_paginas": 0,
  "quantidade_contatos": 0,
  "erro": "HTTP 404 ao acessar http://127.0.0.1:8765/nao-existe.html"
}
```

## Teste com domínio real autorizado

Use a pasta `Varreduras`.

1. Confirme ou altere a variável `url_real_autorizada`.
2. Envie `Criar varredura em domínio real autorizado`.
3. Aguarde alguns segundos.
4. Envie `Consultar varredura por ID`.
5. Envie `Listar contatos por varredura`.

Use apenas domínio próprio, de cliente ou com autorização explícita.

## Validações incluídas

A coleção tem testes automáticos para:

- healthcheck online;
- contrato OpenAPI disponível;
- criação de varredura com `202`;
- gravação automática de `varredura_id`;
- resposta de histórico em array;
- consulta por ID;
- listagem de contatos;
- erro `422` para URL inválida;
- erro `404` para varredura inexistente;
- preservação da URL inicial por varredura.

## Observação sobre background

O `POST /varreduras` não espera o Scrapy terminar. Ele retorna rápido com `status = pendente`.

Por isso, após criar uma varredura, consulte o detalhe algumas vezes até o status ser:

- `concluida`; ou
- `erro`.

Esse comportamento é intencional e demonstra execução em background.
