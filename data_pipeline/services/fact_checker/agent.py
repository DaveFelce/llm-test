import json
from django.conf import settings
from langchain.prompts import PromptTemplate
from typing import List, Tuple
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


class FactChecker:
    """
    Uses an LLM to compare a layperson summary against its source abstract,
    identifying unsupported statements and computing a hallucination score.
    """

    # Set temperature to 0 for deterministic outputs
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=settings.OPENAI_API_KEY,
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
        self.chain = self.prompt | self.llm | StrOutputParser()

    def score(self, summary: str, abstract: str) -> Tuple[int, List[str]]:
        response = self.chain.invoke({"abstract": abstract, "summary": summary})
        data = json.loads(response)
        return data.get("score", 0), data.get("issues", [])
