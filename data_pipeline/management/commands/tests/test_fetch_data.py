from datetime import date

import pytest
import responses
from data_pipeline.models import Article
from data_pipeline.services.enums import PubMedURLs
from data_pipeline.services.pubmed_client import PubMedClient
from django.core.management import call_command


@pytest.mark.django_db
@responses.activate
def test_fetch_creates_articles() -> None:
    """Test that fetch_data creates Article objects for each PMID."""
    # Arrange
    PubMedClient.fetch.retry.wait = None
    PubMedClient.fetch.retry.wait = None

    # Stub ESearch → return three PMIDs
    ids = ["1", "2", "3"]
    responses.add(
        responses.GET,
        PubMedURLs.ESEARCH_URL,
        json={"esearchresult": {"idlist": ids}},
        status=200,
    )

    # Stub EFetch → return minimal XML for each PMID
    # TODO: put this into a pytest fixture
    articles_xml = ""
    for id in ids:
        articles_xml += f"""
        <PubmedArticle>
          <MedlineCitation>
            <PMID>{id}</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2020</Year>
                    <Month>01</Month>
                    <Day>0{id}</Day>
                  </PubDate>
                </JournalIssue>
              </Journal>
              <ArticleTitle>Title {id}</ArticleTitle>
              <Abstract>
                <AbstractText>Abstract text {id}</AbstractText>
              </Abstract>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
    full_xml = f"<PubmedArticleSet>{articles_xml}</PubmedArticleSet>"
    responses.add(
        responses.GET,
        PubMedURLs.EFETCH_URL,
        body=full_xml,
        status=200,
        content_type="application/xml",
    )

    # Act
    # Run the command (MONTH_RANGE=2 → only month=1)
    call_command("fetch_data", month_range=2)

    # Assert
    articles = Article.objects.all()
    assert articles.count() == 3

    # Check fields
    for article in articles:
        idx = int(article.pmid)
        assert article.title == f"Title {idx}"
        assert article.abstract == f"Abstract text {idx}"
        assert article.pub_date == date(2020, 1, idx)


@pytest.mark.django_db
@responses.activate
def test_fetch_updates_existing_article() -> None:
    """Test that fetch_data updates an existing article."""
    # Arrange
    responses.add(
        responses.GET,
        PubMedURLs.ESEARCH_URL,
        json={"esearchresult": {"idlist": ["100"]}},
        status=200,
    )
    # TODO: put this into a pytest fixture
    xml1 = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>100</PMID>
          <Article>
            <Journal>
              <JournalIssue>
                <PubDate>
                  <Year>2020</Year>
                  <Month>01</Month>
                  <Day>05</Day>
                </PubDate>
              </JournalIssue>
            </Journal>
            <ArticleTitle>Title A</ArticleTitle>
            <Abstract><AbstractText>Abstract A</AbstractText></Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""
    responses.add(responses.GET, PubMedURLs.EFETCH_URL, body=xml1, status=200, content_type="application/xml")

    # Act and Assert
    # First run → creates
    call_command("fetch_data")
    article = Article.objects.get(pmid="100")
    assert article.title == "Title A"

    # Round 2
    # Arrange
    responses.add(
        responses.GET,
        PubMedURLs.ESEARCH_URL,
        json={"esearchresult": {"idlist": ["100"]}},
        status=200,
    )
    # TODO: put this into a pytest fixture
    xml2 = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>100</PMID>
          <Article>
            <Journal>
              <JournalIssue>
                <PubDate>
                  <Year>2020</Year>
                  <Month>01</Month>
                  <Day>05</Day>
                </PubDate>
              </JournalIssue>
            </Journal>
            <ArticleTitle>Title B</ArticleTitle>
            <Abstract><AbstractText>Abstract B</AbstractText></Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""
    responses.add(responses.GET, PubMedURLs.EFETCH_URL, body=xml2, status=200, content_type="application/xml")

    # Act and Assert
    # Second run → updates
    call_command("fetch_data")
    article.refresh_from_db()
    assert article.title == "Title B"


@pytest.mark.django_db
@responses.activate
def test_fetch_handles_api_error(caplog):
    """Test that fetch_data handles API errors gracefully."""
    # Arrange
    responses.add(responses.GET, PubMedURLs.ESEARCH_URL, status=500)
    caplog.set_level("ERROR")

    # Act
    call_command("fetch_data")

    # Assert
    # No articles created
    assert Article.objects.count() == 0
    # Error should be logged
    assert "Error processing month 2020-01" in caplog.text
