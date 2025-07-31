from django.core.management.base import BaseCommand
from django.db import transaction
from data_pipeline.models import Summary, TrendReport
from data_pipeline.services.llm_orchestrator.agent import LLMOrchestrator
from data_pipeline.services.fact_checker.agent import FactChecker

class Command(BaseCommand):
    help = 'Create "Trends in Covid Research in 2020" article and validate it'

    def handle(self, *args, **options):
        orchestrator = LLMOrchestrator()
        checker = FactChecker()

        # 1. Gather all layperson summaries
        summaries = list(Summary.objects.order_by("article__pub_date").values_list("text", flat=True))
        self.stdout.write(f"Generating trends article from {len(summaries)} summaries")

        # 2. Synthesize trends
        article_text = orchestrator.synthesize_trends(summaries)
        self.stdout.write("  Trends article generated")

        # 3. Fact-check the trends article
        score, issues = checker.score(article_text, "\n\n".join(summaries))
        self.stdout.write(f"  Hallucination score for article: {score}")

        # 4. Persist the report
        with transaction.atomic():
            report = TrendReport.objects.create(
                text=article_text,
                issues=issues,
            )
        self.stdout.write(self.style.SUCCESS(f"✅ TrendReport #{report.pk} saved"))