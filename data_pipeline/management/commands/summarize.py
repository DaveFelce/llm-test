import argparse
import logging

from data_pipeline.models import Article, Summary
from data_pipeline.services.llm_orchestrator.agent import LLMOrchestrator
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate layperson summaries for all unsummarized Articles"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of articles to process in each batch",
        )

    def process_article(self, orchestrator: LLMOrchestrator, article: str) -> bool:
        """Process a single article and generate its summary."""
        try:
            summary_text = orchestrator.summarize(article.abstract)
            with transaction.atomic():
                Summary.objects.create(
                    article=article,
                    text=summary_text,
                )
            logger.info("Saved summary for PMID=%s", article.pmid)
            return True
        except Exception as e:  # TODO: Be more specific with exceptions
            logger.error("Error summarizing PMID=%s: %s", article.pmid, str(e))
            return False

    def handle(self, *args, **options):
        orchestrator = LLMOrchestrator()
        batch_size = options["batch_size"]

        # Select articles that have no summary yet
        articles = Article.objects.filter(summary__isnull=True).order_by("pub_date")
        total = articles.count()

        if not total:
            logger.info("No articles found requiring summarization")
            return

        logger.info("Found %s articles to summarize", total)
        successful = 0

        # Process articles with progress bar
        with tqdm(total=total, desc="Generating summaries") as pbar:
            for article in articles.iterator(chunk_size=batch_size):
                if self.process_article(orchestrator, article):
                    successful += 1
                pbar.update(1)

        logger.info("Completed summarization. Success: %s/%s", successful, total)
        self.stdout.write(self.style.SUCCESS(f"Generated {successful} summaries out of {total}"))
