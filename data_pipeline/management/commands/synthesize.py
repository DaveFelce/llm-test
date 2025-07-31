import logging

from data_pipeline.models import Summary, TrendReport
from data_pipeline.services.fact_checker.agent import FactChecker
from data_pipeline.services.llm_orchestrator.agent import LLMOrchestrator
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

DEFAULT_MIN_SUMMARIES = 3
DEFAULT_MAX_SCORE = 0.3


class Command(BaseCommand):
    help = 'Create "Trends in Covid Research in 2020" article and validate it'

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-summaries",
            type=int,
            default=DEFAULT_MIN_SUMMARIES,
            help="Minimum number of summaries required to generate trends",
        )
        parser.add_argument(
            "--max-score",
            type=float,
            default=DEFAULT_MAX_SCORE,
            help="Maximum acceptable hallucination score",
        )

    def gather_summaries(self):
        """Gather all layperson summaries from the database."""
        summaries = list(Summary.objects.order_by("article__pub_date").values_list("text", flat=True))
        logger.info("Found %s summaries for analysis", len(summaries))
        return summaries

    def generate_trends(self, orchestrator, summaries):
        """Generate trends article from summaries."""
        try:
            article_text = orchestrator.synthesize_trends(summaries)
            logger.info("Successfully generated trends article")
            return article_text
        except Exception as e:
            logger.error("Failed to generate trends article: %s", str(e))
            raise

    def check_facts(self, checker, article_text, source_text):
        """Validate the generated article against source summaries."""
        try:
            score, issues = checker.score(article_text, source_text)
            logger.info("Fact check completed - Score: %s", score)
            return score, issues
        except Exception as e:
            logger.error("Failed to complete fact checking: %s", str(e))
            raise

    def save_report(self, article_text, issues):
        """Save the trends report to the database."""
        try:
            with transaction.atomic():
                report = TrendReport.objects.create(
                    text=article_text,
                    issues=issues,
                )
            logger.info("Saved TrendReport #%s", report.pk)
            return report
        except Exception as e:
            logger.error("Failed to save trend report: %s", str(e))
            raise

    def handle(self, *args, **options):
        try:
            # Initialize services
            orchestrator = LLMOrchestrator()
            checker = FactChecker()

            # Gather summaries
            summaries = self.gather_summaries()
            if len(summaries) < options["min_summaries"]:
                msg = f"Insufficient summaries: {len(summaries)} < {options['min_summaries']}"
                logger.error(msg)
                self.stdout.write(self.style.ERROR(msg))
                return

            # Generate trends article
            self.stdout.write(f"Generating trends article from {len(summaries)} summaries...")
            article_text = self.generate_trends(orchestrator, summaries)

            # TODO: this needs a specialised prompt to verify the trends article and flag unsuported claims
            # Fact-check the article
            self.stdout.write("Fact-checking article...")
            score, issues = self.check_facts(checker, article_text, "\n\n".join(summaries))

            if score > options["max_score"]:
                msg = f"Hallucination score too high: {score} > {options['max_score']}"
                logger.warning(msg)
                self.stdout.write(self.style.WARNING(msg))

            # Save the report
            report = self.save_report(article_text, issues)

            self.stdout.write(self.style.SUCCESS(f"TrendReport #{report.pk} saved (hallucination score: {score:.2f})"))

        except Exception as e:
            logger.error("Command failed: %s", str(e))
            self.stdout.write(self.style.ERROR(f"Failed: {str(e)}"))
            raise
