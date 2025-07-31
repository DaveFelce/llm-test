from django.core.management.base import BaseCommand
from django.db import transaction
from data_pipeline.models import Article
from data_pipeline.services.pubmed_client import PubMedClient
from datetime import date, timedelta

class Command(BaseCommand):
    help = "Fetch Covid-19 abstracts from PubMed for each month of 2020"

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-month",
            type=int,
            default=30,
            help="Number of abstracts to fetch per month",
        )

    def handle(self, *args, **options):
        client = PubMedClient()
        per_month = options["per_month"]

        # Loop through each month in 2020
        for month in range(1, 13):
            start = date(2020, month, 1)
            # rough end-of-month
            end = (start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            self.stdout.write(f"Fetching {per_month} abstracts for {start:%Y-%m}")
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
                    self.stdout.write(f"  {verb} Article PMID={article.pmid}")
        self.stdout.write(self.style.SUCCESS("✅ Fetch complete"))