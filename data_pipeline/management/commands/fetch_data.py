import argparse
import logging
from calendar import monthrange
from datetime import date

from data_pipeline.models import Article
from data_pipeline.services.enums import ArticleData
from data_pipeline.services.pubmed_client import PubMedClient
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

logger = logging.getLogger(__name__)

DEFAULT_MONTH_RANGE = 2
DEFAULT_NUMBER_OF_ARTICLES_TO_FETCH = 25


class Command(BaseCommand):
    help = "Fetch Covid-19 abstracts from PubMed for each month of 2020"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--per-month",
            type=int,
            default=DEFAULT_NUMBER_OF_ARTICLES_TO_FETCH,
            help="Number of abstracts to fetch per month",
        )
        parser.add_argument(
            "--month-range",
            type=int,
            default=DEFAULT_MONTH_RANGE,
            help="Number of months to process (starting from January)",
        )

    def process_month(self, client: PubMedClient, month: int, per_month: int) -> int:
        """Process a single month's worth of abstracts."""
        start = date(2020, month, 1)
        _, last_day = monthrange(2020, month)
        end = date(2020, month, last_day)

        try:
            articles: list[ArticleData] = client.fetch(
                query="Covid-19[Title] AND 2020[Date - Publication]",
                start_date=start,
                end_date=end,
                limit=per_month,
            )

            with transaction.atomic():
                for article_data in articles:
                    article, created = Article.objects.update_or_create(
                        pmid=article_data.pmid,
                        defaults={
                            "title": article_data.title,
                            "abstract": article_data.abstract,
                            "pub_date": article_data.pub_date,
                            "raw_json": article_data.model_dump_json(),
                        },
                    )
                    verb = "Created" if created else "Updated"
                    logger.info(f"{verb} Article PMID={article.pmid}")

            return len(articles)
        except Exception as e:  # TODO: Be more specific with exceptions
            logger.error(f"Error processing month {start:%Y-%m}: {str(e)}")
            return 0

    def handle(self, *args, **options):
        client = PubMedClient()
        per_month = options["per_month"]

        total_processed = 0
        for month in tqdm(range(1, DEFAULT_MONTH_RANGE), desc="Processing months"):
            logger.info(f"Processing month {month}/2020")  # TODO: Use month name, don't hardcode year
            processed: int = self.process_month(client, month, per_month)
            total_processed += processed

        logger.info(f"Fetch complete. Processed {total_processed} articles")
        self.stdout.write(self.style.SUCCESS("Fetch complete"))
