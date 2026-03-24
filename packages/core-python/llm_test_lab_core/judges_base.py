from typing import Protocol, List, Dict


class JudgeClient(Protocol):
    async def score(
        self,
        question: str,
        answer: str,
        context_docs: List[str],
        rubric: str,
    ) -> Dict:
        """
        Return a dict like:
        {
          "score": float between 0 and 1,
          "reason": str,
          "raw": optional raw model text
        }
        """
        ...
