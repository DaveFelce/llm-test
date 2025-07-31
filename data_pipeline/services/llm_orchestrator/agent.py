from typing import List

from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


class LLMOrchestrator:
    """
    Service for orchestrating LLM-powered summaries and trend synthesis.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature= 0.7,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=settings.OPENAI_API_KEY,
        )

        self.summary_prompt = PromptTemplate(
            input_variables=["abstract"],
            template=(
                "You are a helpful assistant tasked with summarizing PubMed abstracts in plain English. "
                "Write a single paragraph summary for a general audience. "
                "Cover epidemiology, risk factors, diagnostics, progression, and prevention. "
                "Define any technical terms.\n\n"
                "Abstract:\n{abstract}\n"
            ),
        )
        self.summary_chain = self.summary_prompt | self.llm | StrOutputParser()

        self.trend_prompt = PromptTemplate(
            input_variables=["summaries"],
            template=(
                "You are a research analyst. Given the following layperson summaries of Covid-19 research abstracts from 2020, "
                "write a 'Trends in Covid Research in 2020' article suitable for a general audience. "
                "Highlight key similarities, differences, and patterns over time. "
                "Ground every claim in these summaries.\n\n"
                "Summaries:\n{summaries}\n"
            ),
        )
        self.trend_chain = self.trend_prompt | self.llm | StrOutputParser()

    def summarize(self, abstract: str) -> str:
        return self.summary_chain.invoke({"abstract": abstract}).strip()

    def synthesize_trends(self, summaries: List[str]) -> str:
        combined = "\n\n".join(summaries)
        return self.trend_chain.invoke({"summaries": combined}).strip()
