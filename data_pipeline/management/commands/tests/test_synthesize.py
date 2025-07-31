import pytest
from data_pipeline.models import Article, Summary, TrendReport
from data_pipeline.services.fact_checker.agent import FactChecker
from data_pipeline.services.llm_orchestrator.agent import LLMOrchestrator
from django.core.management import call_command


@pytest.mark.django_db
def test_synthesize_creates_trendreport(monkeypatch, capsys):
    # Arrange: three Articles with raw_json, each with a linked Summary
    for idx, text in enumerate(["sum1", "sum2", "sum3"], start=1):
        article = Article.objects.create(
            pmid=str(idx),
            title=f"Title {idx}",
            abstract=f"Abstract {idx}",
            pub_date=f"2020-01-{idx:02d}",
            raw_json={"pmid": str(idx), "foo": idx},
        )
        Summary.objects.create(article=article, text=text)

    # Stub out the LLM and fact-checker
    fake_trend_text = "Consolidated trends article."
    fake_score = 5
    fake_issues = ["issue1", "issue2", "issue3", "issue4", "issue5"]

    monkeypatch.setattr(LLMOrchestrator, "synthesize_trends", lambda self, summaries: fake_trend_text)
    monkeypatch.setattr(FactChecker, "score", lambda self, article_text, joined_summaries: (fake_score, fake_issues))

    # Act
    call_command("synthesize", min_summaries=3, max_score=10)

    # Assert: exactly one TrendReport
    reports = TrendReport.objects.all()
    assert reports.count() == 1
    report = reports.first()
    assert report.text == fake_trend_text
    assert report.issues == fake_issues

    # Check that output messages mention the correct summary count and score
    captured = capsys.readouterr().out
    assert "Generating trends article from 3 summaries" in captured
    assert "Fact-checking article" in captured
    assert f"TrendReport #{report.pk} saved (hallucination score: {5:.2f})" in captured


@pytest.mark.django_db
def test_synthesize_with_no_summaries(monkeypatch, capsys):
    # No Summary rows in the DB

    # Stub LLM to return an empty-report placeholder
    monkeypatch.setattr(LLMOrchestrator, "synthesize_trends", lambda self, summaries: "No summaries available.")
    # Stub fact-checker to return a zero score
    monkeypatch.setattr(FactChecker, "score", lambda self, article_text, joined_summaries: (0, []))

    # Act
    call_command("synthesize")

    out = capsys.readouterr().out
    assert "Insufficient summaries" in out
