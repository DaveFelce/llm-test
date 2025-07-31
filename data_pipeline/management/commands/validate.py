from django.core.management.base import BaseCommand
from django.db import transaction
from data_pipeline.models import Summary, Validation
from data_pipeline.services.fact_checker.agent import FactChecker

class Command(BaseCommand):
    help = "Validate summaries for hallucinations and record scores"

    def handle(self, *args, **options):
        checker = FactChecker()
        pending = Summary.objects.filter(validation__isnull=True)
        total = pending.count()
        self.stdout.write(f"Found {total} summaries to validate")

        for summary in pending:
            self.stdout.write(f"Validating PMID={summary.article.pmid}")
            score, issues = checker.score(summary.text, summary.article.abstract)
            with transaction.atomic():
                Validation.objects.create(
                    summary=summary,
                    hallucination_score=score,
                    issues=issues,
                )
            self.stdout.write(
                f"  Score={score}, Issues={len(issues)}"
            )

        self.stdout.write(self.style.SUCCESS("✅ Validation complete"))