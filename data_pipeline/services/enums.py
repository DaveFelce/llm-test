from datetime import date

from pydantic import BaseModel, Field


class ArticleData(BaseModel):
    pmid: str
    title: str
    abstract: str
    pub_date: date
    raw_json: dict = Field(default_factory=dict)


class PubMedURLs:
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    EINFO_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"
