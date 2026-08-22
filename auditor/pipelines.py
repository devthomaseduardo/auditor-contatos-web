class AuditorPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        instancia = cls()

        instancia.crawler = crawler
        instancia.emails_processados = set()

        return instancia

    def open_spider(self):
        spider = self.crawler.spider

        spider.logger.info("Pipeline iniciado")

    def process_item(self, item):
        spider = self.crawler.spider

        email = item.get("email")

        if not email:
            return item

        email = email.strip().lower()

        if email in self.emails_processados:
            spider.logger.info(
                f"E-mail duplicado ignorado: {email}"
            )

            return None

        self.emails_processados.add(email)

        item["email"] = email

        spider.logger.info(
            f"E-mail validado: {email}"
        )

        return item

    def close_spider(self):
        spider = self.crawler.spider

        spider.logger.info(
            f"Pipeline finalizado com "
            f"{len(self.emails_processados)} e-mails únicos"
        )
