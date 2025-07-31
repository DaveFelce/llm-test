import json
from django.conf import settings
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import List, Tuple


class FactChecker:
    """
    Uses an LLM to compare a layperson summary against its source abstract,
    identifying unsupported statements and computing a hallucination score.
    """

    def __init__(self):
        self.llm = OpenAI(
            model_name=getattr(settings, "OPENAI_MODEL", "gpt-4"),
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.prompt = PromptTemplate(
            input_variables=["abstract", "summary"],
            template=(
                "You are a fact-checking assistant. "
                "Given the following article abstract and a layperson summary, identify any statements in the summary that are NOT supported by the abstract. "
                "Respond with a JSON object containing two fields:\n"
                "  score: the number of unsupported statements,\n"
                "  issues: a list of the unsupported statements.\n\n"
                "Abstract:\n{abstract}\n\nSummary:\n{summary}"
            ),
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def score(self, summary: str, abstract: str) -> Tuple[int, List[str]]:
        response = self.chain.run({"abstract": abstract, "summary": summary})
        data = json.loads(response)
        return data.get("score", 0), data.get("issues", [])
