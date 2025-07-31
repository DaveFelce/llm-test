from datetime import date

import pytest
import responses
from data_pipeline.models import Article
from data_pipeline.services.enums import PubMedURLs
from django.core.management import call_command


@pytest.mark.django_db
@responses.activate
def test_fetch_creates_articles() -> None:
    # 1) Stub ESearch → return three PMIDs
    ids = ["1", "2", "3"]
    responses.add(
        responses.GET,
        PubMedURLs.ESEARCH_URL,
        json={"esearchresult": {"idlist": ids}},
        status=200,
    )

    # 2) Stub EFetch → return minimal XML for each PMID
    # TODO: put this into a pytest fixture
    articles_xml = ""
    for id in ids:
        articles_xml += f"""
        <PubmedArticle>
          <MedlineCitation>
            <PMID>{id}</PMID>
            <Article>
              <ArticleTitle>Title {id}</ArticleTitle>
              <Abstract>
                <AbstractText>Abstract text {id}</AbstractText>
              </Abstract>
            </Article>
            <DateCreated>
              <Year>2020</Year><Month>1</Month><Day>{id}</Day>
            </DateCreated>
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

    # Run the command (TQDM_RANGE=2 → only month=1)
    call_command("fetch_data")

    # Assert three articles were created
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
            <ArticleTitle>Title A</ArticleTitle>
            <Abstract><AbstractText>Abstract A</AbstractText></Abstract>
          </Article>
          <DateCreated><Year>2020</Year><Month>1</Month><Day>1</Day></DateCreated>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""
    responses.add(responses.GET, PubMedURLs.EFETCH_URL, body=xml1, status=200, content_type="application/xml")

    # Act and Assert
    # First run → creates
    call_command("fetch_data")
    art = Article.objects.get(pmid="100")
    assert art.title == "Title A"

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
            <ArticleTitle>Title B</ArticleTitle>
            <Abstract><AbstractText>Abstract B</AbstractText></Abstract>
          </Article>
          <DateCreated><Year>2020</Year><Month>1</Month><Day>1</Day></DateCreated>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""
    responses.add(responses.GET, PubMedURLs.EFETCH_URL, body=xml2, status=200, content_type="application/xml")

    # Act and Assert
    # Second run → updates
    call_command("fetch_data")
    art.refresh_from_db()
    assert art.title == "Title B"


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
