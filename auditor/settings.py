# Configurações do projeto Auditor de Contatos Web

BOT_NAME = "auditor"

SPIDER_MODULES = ["auditor.spiders"]
NEWSPIDER_MODULE = "auditor.spiders"


# Respeita o robots.txt dos sites.
# No teste local deixamos False.
# Quando começarmos a testar sites reais, vamos revisar esta configuração.
ROBOTSTXT_OBEY = False


# Tempo de espera entre as requisições para o mesmo domínio.
# Evita fazer várias requisições seguidas.
DOWNLOAD_DELAY = 1


# Limita a quantidade de requisições simultâneas
# realizadas para o mesmo domínio.
CONCURRENT_REQUESTS_PER_DOMAIN = 1


# Pipeline responsável pelo tratamento dos dados
# encontrados pela spider.
ITEM_PIPELINES = {
    "auditor.pipelines.AuditorPipeline": 300,
}


# Codificação utilizada na exportação dos resultados.
FEED_EXPORT_ENCODING = "utf-8"


# Cabeçalho enviado durante as requisições.
# Identifica nosso crawler de maneira simples.
USER_AGENT = "AuditorContatosWeb/1.0"


# Desabilita cookies, pois não precisamos deles
# nesta primeira versão do projeto.
COOKIES_ENABLED = False


# Impede o Scrapy de repetir requisições automaticamente
# muitas vezes quando uma página apresenta erro.
RETRY_TIMES = 2


# Tempo máximo de espera por uma resposta.
DOWNLOAD_TIMEOUT = 15
