import pytest
from data_pipeline.models import Article, Summary
from data_pipeline.services.llm_orchestrator.agent import LLMOrchestrator
from django.core.management import call_command


@pytest.mark.django_db
def test_summarize_creates_summaries(monkeypatch):
    """
    Given three unsummarized Articles, the summarize command should
    create exactly three Summary objects with the text returned by LLMOrchestrator.summarize.
    """
    # Arrange: create 3 articles
    [
        Article.objects.create(
            pmid=str(i), title=f"Title{i}", abstract=f"Abstract{i}", pub_date="2020-01-0" + str(i), raw_json={}
        )
        for i in range(1, 4)
    ]

    # Stub out the orchestrator to return a predictable summary
    def fake_summarize(self, abstract):
        return f"Summary of '{abstract}'"

    monkeypatch.setattr(LLMOrchestrator, "summarize", fake_summarize)

    # Act
    call_command("summarize")

    # Assert: one Summary per Article
    all_summaries = Summary.objects.order_by("article__pmid")
    assert all_summaries.count() == 3
    for i, summary in enumerate(all_summaries, start=1):
        assert summary.article.pmid == str(i)
        assert summary.text == f"Summary of 'Abstract{i}'"


@pytest.mark.django_db
def test_summarize_skips_already_summarized(monkeypatch):
    """
    Articles that already have a Summary should be ignored.
    Running the command should not create duplicate summaries.
    """
    # Arrange: one article with existing summary, one without
    art1 = Article.objects.create(pmid="100", title="Title", abstract="Abstract", pub_date="2020-01-01", raw_json={})
    Summary.objects.create(article=art1, text="Existing summary")

    art2 = Article.objects.create(pmid="101", title="Title2", abstract="AbstractB", pub_date="2020-01-02", raw_json={})

    # Stub LLM
    monkeypatch.setattr(LLMOrchestrator, "summarize", lambda self, abstract: "New summary")

    # Act
    call_command("summarize")

    # Assert
    assert Summary.objects.filter(article=art1).count() == 1  # untouched
    summaries_for_art2 = Summary.objects.filter(article=art2)
    assert summaries_for_art2.count() == 1
    assert summaries_for_art2.first().text == "New summary"


@pytest.mark.django_db
def test_summarize_continues_on_error(monkeypatch, caplog):
    """
    If the orchestrator raises on one article, the command should log an error
    and still process the remaining articles.
    """
    # Arrange: two articles
    art1 = Article.objects.create(pmid="200", title="Title1", abstract="Abstract1", pub_date="2020-01-01", raw_json={})
    art2 = Article.objects.create(pmid="201", title="Title2", abstract="Abstract2", pub_date="2020-01-02", raw_json={})

    # First call raises, second returns normally
    def flaky_summarize(self, abstract):
        if abstract == "Abstract1":
            raise RuntimeError("LLM service down")
        return "OK"

    monkeypatch.setattr(LLMOrchestrator, "summarize", flaky_summarize)
    caplog.set_level("ERROR")

    # Act
    call_command("summarize")

    # Assert: only one summary created
    assert Summary.objects.count() == 1
    # The error should have been logged
    assert "Error summarizing PMID=200: LLM service down" in caplog.text
    # And the second article should succeed
    summary = Summary.objects.get(article=art2)
    assert summary.text == "OK"
