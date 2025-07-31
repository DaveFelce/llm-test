from datetime import date
from typing import List
import requests
import xml.etree.ElementTree as ET
from pydantic import BaseModel, Field


class ArticleData(BaseModel):
    pmid: str
    title: str
    abstract: str
    pub_date: date
    raw_json: dict = Field(default_factory=dict)


class PubMedClient:
    """
    Fetches PubMed abstracts via NCBI E-utilities.
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def fetch(self, query: str, start_date: date, end_date: date, limit: int = 30) -> List[ArticleData]:
        # 1) ESearch to get PMIDs
        esearch_params = {
            "db": "pubmed",
            "term": query,
            "datetype": "pdat",
            "mindate": start_date.isoformat(),
            "maxdate": end_date.isoformat(),
            "retmax": limit,
            "retmode": "json",
        }
        resp = requests.get(self.ESEARCH_URL, params=esearch_params)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # 2) EFetch to retrieve full records (XML)
        efetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
        }
        resp = requests.get(self.EFETCH_URL, params=efetch_params)
        resp.raise_for_status()

        # 3) Parse XML
        root = ET.fromstring(resp.text)
        results: List[ArticleData] = []
        for art in root.findall(".//PubmedArticle"):
            med = art.find("MedlineCitation")
            pmid = med.findtext("PMID") or ""
            article = med.find("Article")
            title = article.findtext("ArticleTitle") or ""
            abs_node = article.find("Abstract")
            abstract = (
                " ".join([t.text or "" for t in abs_node.findall("AbstractText")]) if abs_node is not None else ""
            )
            # Publication date
            date_node = med.find("DateCreated")
            pub_date = (
                date(
                    int(date_node.findtext("Year")),
                    int(date_node.findtext("Month")),
                    int(date_node.findtext("Day")),
                )
                if date_node is not None
                else None
            )

            results.append(
                ArticleData(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    pub_date=pub_date,
                    raw_json={},
                )
            )
        return results
