from django.core.management.base import BaseCommand
from django.db import transaction

from data_pipeline.models import Article, Summary
from data_pipeline.services.llm_orchestrator.agent import LLMOrchestrator


class Command(BaseCommand):
    help = "Generate layperson summaries for all unsummarized Articles"

    def handle(self, *args, **options):
        orchestrator = LLMOrchestrator()

        # Select articles that have no summary yet
        articles = Article.objects.filter(summary__isnull=True).order_by("pub_date")
        total = articles.count()
        self.stdout.write(f"Found {total} articles to summarize")

        for idx, article in enumerate(articles, start=1):
            self.stdout.write(f"[{idx}/{total}] Summarizing PMID={article.pmid}…")

            # Generate the summary
            try:
                summary_text = orchestrator.summarize(article.abstract)
            except Exception as e:  # TODO: Be more specific with exceptions
                self.stderr.write(f"Error summarizing PMID={article.pmid}: {e}")
                continue

            # Persist the summary
            with transaction.atomic():
                Summary.objects.create(
                    article=article,
                    text=summary_text,
                )

            self.stdout.write(f"Saved summary for PMID={article.pmid}")

        self.stdout.write(self.style.SUCCESS("All summaries generated"))