from typing import List

from django.conf import settings
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate


class LLMOrchestrator:
    """
    Service for orchestrating LLM-powered summaries and trend synthesis.
    """

    def __init__(self):
        self.llm = OpenAI(
            model_name=getattr(settings, "OPENAI_MODEL", "gpt-4"),
            temperature=getattr(settings, "OPENAI_TEMPERATURE", 0.7),
            openai_api_key=settings.OPENAI_API_KEY,
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
        self.summary_chain = LLMChain(llm=self.llm, prompt=self.summary_prompt)

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
        self.trend_chain = LLMChain(llm=self.llm, prompt=self.trend_prompt)

    def summarize(self, abstract: str) -> str:
        return self.summary_chain.run({"abstract": abstract}).strip()

    def synthesize_trends(self, summaries: List[str]) -> str:
        combined = "\n\n".join(summaries)
        return self.trend_chain.run({"summaries": combined}).strip()
