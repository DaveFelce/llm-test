import logging
from datetime import date
import xml.etree.ElementTree as ET
from datetime import date

import requests
from data_pipeline.services.enums import ArticleData, PubMedURLs
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class PubMedClient:
    """
    Fetches PubMed abstracts via NCBI E-utilities.
    """

    @staticmethod
    def parse_publication_date(pubmed_article_element) -> date | None:
        """
        Attempt to extract a publication date from several possible XML locations,
        falling back in this order:
          1) MedlineCitation/DateCreated
          2) JournalIssue/PubDate
          3) MedlineCitation/DateRevised
          4) PubmedData/History PubMedPubDate[@PubStatus="pubmed"]
        """

        # Look for the original creation date
        date_created_node = pubmed_article_element.find(
            ".//MedlineCitation/DateCreated"
        )
        if date_created_node is not None:
            year_text = date_created_node.findtext("Year")
            month_text = date_created_node.findtext("Month")
            day_text = date_created_node.findtext("Day")
            return date(int(year_text), int(month_text), int(day_text))

        # Next, try the journal’s publication date
        journal_pub_date_node = pubmed_article_element.find(
            ".//JournalIssue/PubDate"
        )
        if journal_pub_date_node is not None and journal_pub_date_node.findtext("Year"):
            year_text = journal_pub_date_node.findtext("Year")
            # default to January 1 if Month/Day are missing
            month_text = journal_pub_date_node.findtext("Month") or "1"
            day_text = journal_pub_date_node.findtext("Day") or "1"
            return date(int(year_text), int(month_text), int(day_text))

        # Then, the last‐revised date
        date_revised_node = pubmed_article_element.find(
            ".//MedlineCitation/DateRevised"
        )
        if date_revised_node is not None:
            year_text = date_revised_node.findtext("Year")
            month_text = date_revised_node.findtext("Month")
            day_text = date_revised_node.findtext("Day")
            return date(int(year_text), int(month_text), int(day_text))

        # Finally, the PubMed “pubmed” history date
        pubmed_history_date_node = pubmed_article_element.find(
            './/PubmedData/History/PubMedPubDate[@PubStatus="pubmed"]'
        )
        if pubmed_history_date_node is not None:
            year_text = pubmed_history_date_node.findtext("Year")
            month_text = pubmed_history_date_node.findtext("Month") or "1"
            day_text = pubmed_history_date_node.findtext("Day") or "1"
            return date(int(year_text), int(month_text), int(day_text))

        # If no date was found, return None
        return None

    @retry(
        stop=stop_after_attempt(1),  # TODO: Increase this for production
        wait=wait_exponential(multiplier=2, min=1, max=64),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.INFO),
    )
    def fetch(self, query: str, start_date: date, end_date: date, limit: int = 30) -> list[ArticleData]:
        """Fetches articles from PubMed based on a query and date range."""

        # TODO: batch requests if limit is high
        # Two stage process: first query ESearch to get PMIDs
        esearch_params = {
            "db": "pubmed",
            "term": query,
            "datetype": "pdat",
            "mindate": start_date.isoformat(),
            "maxdate": end_date.isoformat(),
            "retmax": limit,
            "retmode": "json",
        }

        logger.info(f"Fetching articles for query: {query} from {start_date} to {end_date}")

        resp = requests.get(PubMedURLs.ESEARCH_URL, params=esearch_params)
        logger.debug(f"ESearch response: {resp.status_code} {resp.text}")
        resp.raise_for_status()

        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            logger.info(f"No PubMed IDs found in response: {resp.text}")
            return []

        # Then query EFetch to retrieve full records (XML)
        efetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
        }
        resp = requests.get(PubMedURLs.EFETCH_URL, params=efetch_params)
        logger.debug(f"EFetch response: {resp.status_code} {resp.text}")
        resp.raise_for_status()

        # Parse XML
        root = ET.fromstring(resp.text)
        results: list[ArticleData] = []
        for article in root.findall(".//PubmedArticle"):
            med = article.find("MedlineCitation")
            pmid = med.findtext("PMID") or ""
            article = med.find("Article")
            title = article.findtext("ArticleTitle") or ""
            abs_node = article.find("Abstract")
            abstract = (
                " ".join([t.text or "" for t in abs_node.findall("AbstractText")]) if abs_node is not None else ""
            )
            # Publication date
            pub_date = self.parse_publication_date(article)

            results.append(
                ArticleData(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    pub_date=pub_date,
                    raw_json={},
                )
            )
        logger.info(f"Fetched {len(results)} articles for query: {query}")

        return results
