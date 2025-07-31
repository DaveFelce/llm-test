import logging

import pytest
from data_pipeline.models import Article, Summary, Validation
from data_pipeline.services.fact_checker.agent import FactChecker
from django.core.management import call_command


@pytest.mark.django_db
def test_validate_creates_validations(monkeypatch, capsys):
    """
    Given two unsatisfied Summaries, the validate command should
    create two Validation records and print the correct progress.
    """
    # Arrange: create two Articles + Summaries (no Validation yet)
    for i, text in enumerate(["Text A", "Text B"], start=1):
        article = Article.objects.create(
            pmid=str(i),
            title=f"T{i}",
            abstract=f"Abstract {i}",
            pub_date=f"2020-01-0{i}",
            raw_json={"pmid": str(i)},
        )
        Summary.objects.create(article=article, text=text)

    # Stub FactChecker.score to always return zero errors
    monkeypatch.setattr(
        FactChecker,
        "score",
        lambda self, summary_text, source: (0, []),
    )

    # Act
    call_command("validate")

    # Assert: two Validation rows created
    assert Validation.objects.count() == 2

    # Check stdout
    out = capsys.readouterr().out
    assert "Validating 2 summaries..." in out
    assert "Validation complete: 2/2 summaries processed" in out


@pytest.mark.django_db
def test_validate_warns_on_high_score(monkeypatch, caplog):
    """
    If the hallucination_score exceeds max_score, a warning should be logged,
    but Validation should still be created.
    """
    # Arrange: one summary
    article = Article.objects.create(
        pmid="X1",
        title="T1",
        abstract="Abstract X1",
        pub_date="2020-01-01",
        raw_json={"pmid": "X1"},
    )
    Summary.objects.create(article=article, text="Problematic summary")

    # Stub score to return a high value and one issue
    monkeypatch.setattr(
        FactChecker,
        "score",
        lambda self, summary_text, source: (0.5, ["issue1"]),
    )

    caplog.set_level(logging.WARNING)
    # Use a low max-score threshold
    call_command("validate", max_score=0.3)

    # Validation still created
    val = Validation.objects.get()
    assert val.hallucination_score == 0.5
    assert val.issues == ["issue1"]

    # Warning logged
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("High hallucination score for PMID=X1" in r.getMessage() for r in warnings)


@pytest.mark.django_db
def test_validate_continues_on_error(monkeypatch, capsys):
    """
    If FactChecker.score raises for one summary, the command should log an error
    for that PMID and continue with the others.
    """
    # Arrange: two summaries
    article1 = Article.objects.create(
        pmid="E1",
        title="T1",
        abstract="A1",
        pub_date="2020-01-01",
        raw_json={"pmid": "E1"},
    )
    Summary.objects.create(article=article1, text="bad summary")
    article2 = Article.objects.create(
        pmid="E2",
        title="T2",
        abstract="A2",
        pub_date="2020-01-02",
        raw_json={"pmid": "E2"},
    )
    summ2 = Summary.objects.create(article=article2, text="good summary")

    # Stub score: first raises, second succeeds
    def flaky_score(self, summary_text, source):
        if summary_text == "bad summary":
            raise RuntimeError("checker failure")
        return (0, [])

    monkeypatch.setattr(FactChecker, "score", flaky_score)

    # Act
    call_command("validate")

    # Only one Validation created
    assert Validation.objects.count() == 1
    assert Validation.objects.filter(summary=summ2).exists()

    # Check stdout contains error line and final summary
    out = capsys.readouterr().out
    assert "Failed on PMID=E1: checker failure" in out
    assert "Validation complete: 1/2 summaries processed" in out
