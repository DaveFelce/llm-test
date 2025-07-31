import logging
from calendar import monthrange
from datetime import date, timedelta

from data_pipeline.models import Article
from data_pipeline.services.pubmed_client import PubMedClient
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch Covid-19 abstracts from PubMed for each month of 2020"

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-month",
            type=int,
            default=30,
            help="Number of abstracts to fetch per month",
        )

    def process_month(self, client, month, per_month):
        """Process a single month's worth of abstracts."""
        start = date(2020, month, 1)
        _, last_day = monthrange(2020, month)
        end = date(2020, month, last_day)

        try:
            abstracts = client.fetch(
                query="Covid-19[Title] AND 2020[Date - Publication]",
                start_date=start,
                end_date=end,
                limit=per_month,
            )

            with transaction.atomic():
                for raw in abstracts:
                    article, created = Article.objects.update_or_create(
                        pmid=raw["pmid"],
                        defaults={
                            "title": raw["title"],
                            "abstract": raw["abstract"],
                            "pub_date": raw["pub_date"],
                            "raw_json": raw,
                        },
                    )
                    verb = "Created" if created else "Updated"
                    logger.info(f"{verb} Article PMID={article.pmid}")

            return len(abstracts)
        except Exception as e:
            logger.error(f"Error processing month {start:%Y-%m}: {str(e)}")
            return 0

    def handle(self, *args, **options):
        client = PubMedClient()
        per_month = options["per_month"]

        total_processed = 0
        for month in tqdm(range(1, 13), desc="Processing months"):
            logger.info(f"Processing month {month}/2020")
            processed = self.process_month(client, month, per_month)
            total_processed += processed

        logger.info(f"✅ Fetch complete. Processed {total_processed} articles")
        self.stdout.write(self.style.SUCCESS("✅ Fetch complete"))
