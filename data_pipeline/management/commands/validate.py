import argparse
import logging

from data_pipeline.models import Summary, Validation
from data_pipeline.services.fact_checker.agent import FactChecker
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Validate summaries for hallucinations and record scores"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--max-score",
            type=float,
            default=0.3,
            help="Threshold to warn about high hallucination scores",
        )

    def get_pending_summaries(self):
        """Retrieve summaries that haven't been validated yet."""
        try:
            pending = Summary.objects.filter(validation__isnull=True)
            total = pending.count()
            logger.info("Found %d summaries pending validation", total)
            return pending, total
        except Exception as e:
            logger.error("Failed to fetch pending summaries: %s", str(e))
            raise

    def validate_summary(self, checker: FactChecker, summary: Summary) -> Validation:
        """Validate a single summary and save results."""
        try:
            score, issues = checker.score(summary.text, summary.article.abstract)

            with transaction.atomic():
                validation = Validation.objects.create(
                    summary=summary,
                    hallucination_score=score,
                    issues=issues,
                )

            if score > self.max_score:
                logger.warning(
                    "High hallucination score for PMID=%s: %s > %s",
                    summary.article.pmid,
                    score,
                    self.max_score,
                )

            logger.info(
                "Validated PMID=%s: score=%s, issues=%d",
                summary.article.pmid,
                score,
                len(issues),
            )

            return validation

        except Exception as e:
            logger.error(
                "Failed to validate PMID=%s: %s",
                summary.article.pmid,
                str(e),
            )
            raise

    def handle(self, *args, **options):
        try:
            self.max_score = options["max_score"]
            checker = FactChecker()

            # Get pending summaries
            pending, total = self.get_pending_summaries()
            if not total:
                msg = "No summaries found for validation"
                logger.info(msg)
                self.stdout.write(self.style.SUCCESS(msg))
                return

            # Process summaries with progress bar
            self.stdout.write(f"Validating {total} summaries...")
            success_count = 0

            for summary in tqdm(pending, total=total):
                try:
                    self.validate_summary(checker, summary)
                    success_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed on PMID={summary.article.pmid}: {str(e)}"))
                    continue

            # Final status
            self.stdout.write(self.style.SUCCESS(f"Validation complete: {success_count}/{total} summaries processed"))

        except Exception as e:  # TODO: Be more specific with exceptions
            logger.error("Command failed: %s", str(e))
            self.stdout.write(self.style.ERROR(f"Failed: {str(e)}"))
            raise
