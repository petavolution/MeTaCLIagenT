# judge.py - LLM-as-Judge Fitness Evaluation
"""
Optimized LLM-based fitness evaluation system.

Based on research best practices:
- Multi-criteria evaluation (correctness, completeness, clarity, efficiency)
- Pairwise comparison for ranking
- Hybrid scoring (LLM + heuristic fallback)
- Position bias mitigation
"""

from __future__ import annotations
import json
import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fitness Result
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Fitness:
    """
    Fitness evaluation result.

    Attributes:
        score: Overall fitness (0-10 scale)
        criteria: Individual criterion scores
        justification: Brief explanation
        method: Evaluation method used
    """
    score: float
    criteria: Dict[str, float] = field(default_factory=dict)
    justification: str = ""
    method: str = "heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "criteria": {k: round(v, 2) for k, v in self.criteria.items()},
            "justification": self.justification,
            "method": self.method,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Evaluation Criteria
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Criterion:
    """A single evaluation criterion."""
    name: str
    description: str
    weight: float = 1.0
    max_score: float = 10.0


DEFAULT_CRITERIA = [
    Criterion("correctness", "Factually and technically accurate", weight=2.0),
    Criterion("completeness", "Fully addresses all aspects", weight=1.5),
    Criterion("clarity", "Clear, well-organized, easy to understand", weight=1.0),
    Criterion("efficiency", "Efficient and well-optimized", weight=1.0),
    Criterion("creativity", "Creative problem-solving approach", weight=0.5),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

JUDGE_PROMPT = """You are an expert evaluator. Rate this AI response.

TASK:
{task}

RESPONSE:
{response}

Rate on these criteria (0-10 each):
{criteria}

Output JSON only:
{{"scores": {{"criterion": score, ...}}, "overall": X, "justification": "brief"}}"""

COMPARE_PROMPT = """Compare these AI responses and rank them.

TASK:
{task}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

Which is better? Output JSON:
{{"winner": "A" or "B", "scores": {{"A": X, "B": Y}}, "reason": "brief"}}"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM Judge
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LLMJudge:
    """
    LLM-as-Judge fitness evaluator.

    Supports multiple evaluation modes:
    - LLM-based (requires judge_fn)
    - Heuristic fallback
    - Hybrid (weighted combination)

    Usage:
        judge = LLMJudge()
        fitness = judge.evaluate(task="Write hello world", response="print('hi')")

        # With LLM:
        judge = LLMJudge(judge_fn=my_llm_call)
        fitness = judge.evaluate(task, response)

        # Pairwise comparison:
        winner = judge.compare(task, response_a, response_b)
    """

    def __init__(
        self,
        judge_fn: Optional[Callable[[str], str]] = None,
        criteria: Optional[List[Criterion]] = None,
        hybrid_weight: float = 0.5,  # LLM weight when hybrid
    ):
        """
        Args:
            judge_fn: Function(prompt) -> response for LLM evaluation
            criteria: Custom evaluation criteria
            hybrid_weight: Weight for LLM score in hybrid mode (0-1)
        """
        self.judge_fn = judge_fn
        self.criteria = criteria or DEFAULT_CRITERIA
        self.hybrid_weight = hybrid_weight
        self._cache: Dict[str, Fitness] = {}

    # ─────────────────────────────────────────────────────
    # Main Evaluation
    # ─────────────────────────────────────────────────────

    def evaluate(
        self,
        task: str,
        response: str,
        use_cache: bool = True,
    ) -> Fitness:
        """
        Evaluate a response's fitness.

        Uses LLM if available, otherwise falls back to heuristics.
        """
        # Check cache
        if use_cache:
            cache_key = self._cache_key(task, response)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Get scores
        if self.judge_fn:
            fitness = self._llm_evaluate(task, response)
        else:
            fitness = self._heuristic_evaluate(response)

        # Cache result
        if use_cache:
            self._cache[cache_key] = fitness

        return fitness

    def evaluate_hybrid(
        self,
        task: str,
        response: str,
    ) -> Fitness:
        """
        Hybrid evaluation combining LLM and heuristic scores.

        Useful when LLM is slow/expensive but you want some LLM signal.
        """
        heuristic = self._heuristic_evaluate(response)

        if not self.judge_fn:
            return heuristic

        llm = self._llm_evaluate(task, response)

        # Weighted combination
        combined_score = (
            llm.score * self.hybrid_weight +
            heuristic.score * (1 - self.hybrid_weight)
        )

        combined_criteria = {}
        for key in set(llm.criteria) | set(heuristic.criteria):
            llm_val = llm.criteria.get(key, 5.0)
            heur_val = heuristic.criteria.get(key, 5.0)
            combined_criteria[key] = (
                llm_val * self.hybrid_weight +
                heur_val * (1 - self.hybrid_weight)
            )

        return Fitness(
            score=combined_score,
            criteria=combined_criteria,
            justification=f"Hybrid: LLM={llm.score:.1f}, Heuristic={heuristic.score:.1f}",
            method="hybrid",
        )

    # ─────────────────────────────────────────────────────
    # LLM Evaluation
    # ─────────────────────────────────────────────────────

    def _llm_evaluate(self, task: str, response: str) -> Fitness:
        """Evaluate using LLM judge."""
        criteria_str = "\n".join(
            f"- {c.name}: {c.description} (weight: {c.weight})"
            for c in self.criteria
        )

        prompt = JUDGE_PROMPT.format(
            task=task[:500],
            response=response[:2000],
            criteria=criteria_str,
        )

        try:
            llm_response = self.judge_fn(prompt)
            return self._parse_llm_response(llm_response)
        except Exception as e:
            # Fallback to heuristic on error
            return self._heuristic_evaluate(response)

    def _parse_llm_response(self, response: str) -> Fitness:
        """Parse LLM JSON response into Fitness."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found")

            data = json.loads(json_match.group())
            scores = data.get("scores", {})

            # Calculate weighted score
            criteria = {}
            weighted_sum = 0.0
            total_weight = 0.0

            for criterion in self.criteria:
                if criterion.name in scores:
                    score = float(scores[criterion.name])
                    criteria[criterion.name] = score
                    weighted_sum += score * criterion.weight
                    total_weight += criterion.weight

            overall = data.get("overall")
            if overall is None and total_weight > 0:
                overall = weighted_sum / total_weight

            return Fitness(
                score=float(overall or 5.0),
                criteria=criteria,
                justification=data.get("justification", ""),
                method="llm",
            )

        except (json.JSONDecodeError, ValueError, KeyError):
            # Try to extract any numbers as fallback
            numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response)
            scores = [float(n) for n in numbers if 0 <= float(n) <= 10]
            if scores:
                return Fitness(
                    score=sum(scores) / len(scores),
                    criteria={"extracted": scores[0]},
                    justification="Extracted from response",
                    method="llm_extracted",
                )

            return Fitness(score=5.0, method="llm_fallback")

    # ─────────────────────────────────────────────────────
    # Heuristic Evaluation
    # ─────────────────────────────────────────────────────

    def _heuristic_evaluate(self, response: str) -> Fitness:
        """
        Heuristic fitness based on response quality indicators.

        Fast fallback when LLM unavailable.
        """
        # Handle empty/whitespace-only responses
        if not response or not response.strip():
            return Fitness(
                score=0.0,
                criteria={c.name: 0.0 for c in self.criteria},
                justification="Empty response",
                method="heuristic",
            )

        criteria = {}

        # Correctness: code structure presence
        correctness = 5.0
        if "def " in response or "class " in response:
            correctness += 2.0
        if "```" in response:
            correctness += 1.0
        if "error" in response.lower() or "exception" in response.lower():
            correctness -= 1.5
        if "import " in response:
            correctness += 0.5
        criteria["correctness"] = min(10, max(0, correctness))

        # Completeness: length-based
        length = len(response)
        if length < 50:
            completeness = 2.0
        elif length < 200:
            completeness = 4.0
        elif length < 500:
            completeness = 6.0
        elif length < 1500:
            completeness = 8.0
        else:
            completeness = 7.0  # Too long might be verbose
        criteria["completeness"] = completeness

        # Clarity: structure indicators
        clarity = 5.0
        structure_markers = ["1.", "2.", "- ", "* ", "```", "##", "**"]
        for marker in structure_markers:
            if marker in response:
                clarity += 0.5
        criteria["clarity"] = min(10, clarity)

        # Efficiency: brevity with substance
        words = len(response.split())
        if 50 < words < 300:
            efficiency = 7.0
        elif words <= 50:
            efficiency = 4.0
        else:
            efficiency = 5.0
        criteria["efficiency"] = efficiency

        # Calculate weighted overall
        weighted_sum = 0.0
        total_weight = 0.0
        for criterion in self.criteria:
            if criterion.name in criteria:
                weighted_sum += criteria[criterion.name] * criterion.weight
                total_weight += criterion.weight

        overall = weighted_sum / total_weight if total_weight > 0 else 5.0

        return Fitness(
            score=overall,
            criteria=criteria,
            justification="Heuristic evaluation",
            method="heuristic",
        )

    # ─────────────────────────────────────────────────────
    # Pairwise Comparison
    # ─────────────────────────────────────────────────────

    def compare(
        self,
        task: str,
        response_a: str,
        response_b: str,
    ) -> Dict[str, Any]:
        """
        Compare two responses and determine winner.

        Returns dict with winner ("A" or "B"), scores, and reason.
        Mitigates position bias by evaluating in both orders.
        """
        if not self.judge_fn:
            # Heuristic comparison
            fit_a = self._heuristic_evaluate(response_a)
            fit_b = self._heuristic_evaluate(response_b)
            winner = "A" if fit_a.score >= fit_b.score else "B"
            return {
                "winner": winner,
                "scores": {"A": fit_a.score, "B": fit_b.score},
                "reason": "Heuristic comparison",
            }

        # LLM comparison with position bias mitigation
        # Evaluate A vs B
        result_ab = self._llm_compare(task, response_a, response_b, "A", "B")

        # Evaluate B vs A (swapped order)
        result_ba = self._llm_compare(task, response_b, response_a, "B", "A")

        # Average the scores
        score_a = (result_ab["scores"].get("A", 5) + result_ba["scores"].get("A", 5)) / 2
        score_b = (result_ab["scores"].get("B", 5) + result_ba["scores"].get("B", 5)) / 2

        winner = "A" if score_a >= score_b else "B"

        return {
            "winner": winner,
            "scores": {"A": score_a, "B": score_b},
            "reason": f"Position-debiased: A={score_a:.1f}, B={score_b:.1f}",
        }

    def _llm_compare(
        self,
        task: str,
        resp_first: str,
        resp_second: str,
        label_first: str,
        label_second: str,
    ) -> Dict[str, Any]:
        """Single LLM comparison call."""
        prompt = COMPARE_PROMPT.format(
            task=task[:500],
            response_a=resp_first[:1000],
            response_b=resp_second[:1000],
        )

        try:
            response = self.judge_fn(prompt)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                # Map back to original labels
                winner_raw = data.get("winner", "A")
                winner = label_first if winner_raw == "A" else label_second
                scores_raw = data.get("scores", {"A": 5, "B": 5})
                scores = {
                    label_first: scores_raw.get("A", 5),
                    label_second: scores_raw.get("B", 5),
                }
                return {"winner": winner, "scores": scores, "reason": data.get("reason", "")}
        except Exception:
            pass

        return {"winner": label_first, "scores": {label_first: 5, label_second: 5}, "reason": "Parse error"}

    # ─────────────────────────────────────────────────────
    # Batch & Tournament
    # ─────────────────────────────────────────────────────

    def rank_responses(
        self,
        task: str,
        responses: Dict[str, str],
    ) -> List[tuple[str, float]]:
        """
        Rank multiple responses by fitness.

        Returns list of (agent_id, score) sorted by score descending.
        """
        results = []
        for agent_id, response in responses.items():
            fitness = self.evaluate(task, response)
            results.append((agent_id, fitness.score))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def tournament(
        self,
        task: str,
        responses: Dict[str, str],
    ) -> str:
        """
        Tournament-style selection via pairwise comparisons.

        Returns the winning agent_id.
        """
        if not responses:
            raise ValueError("No responses to compare")

        if len(responses) == 1:
            return list(responses.keys())[0]

        agents = list(responses.keys())

        # Simple single-elimination
        while len(agents) > 1:
            next_round = []
            for i in range(0, len(agents) - 1, 2):
                result = self.compare(
                    task,
                    responses[agents[i]],
                    responses[agents[i + 1]],
                )
                winner = agents[i] if result["winner"] == "A" else agents[i + 1]
                next_round.append(winner)

            # Handle odd number
            if len(agents) % 2 == 1:
                next_round.append(agents[-1])

            agents = next_round

        return agents[0]

    # ─────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────

    def _cache_key(self, task: str, response: str) -> str:
        """Create cache key from task+response."""
        combined = f"{task[:100]}::{response[:500]}"
        return hashlib.md5(combined.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear evaluation cache."""
        self._cache.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fitness Function Factories
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_fitness_fn(
    judge: Optional[LLMJudge] = None,
    task: Optional[str] = None,
) -> Callable:
    """
    Create a fitness function for use with Evolution.

    Compatible with Evolution.run(fitness_fn=...)
    """
    j = judge or LLMJudge()

    def fitness_fn(agent, task_prompt: str, response: str) -> float:
        actual_task = task or task_prompt
        fitness = j.evaluate(actual_task, response)
        return fitness.score

    return fitness_fn


def create_keyword_fitness(keywords: Dict[str, float]) -> Callable:
    """
    Create keyword-based fitness function.

    Args:
        keywords: Dict mapping keyword -> score weight
    """
    def fitness_fn(agent, task: str, response: str) -> float:
        score = 0.0
        response_lower = response.lower()
        for kw, weight in keywords.items():
            if kw.lower() in response_lower:
                count = response_lower.count(kw.lower())
                score += min(count * weight, weight * 3)
        return min(10.0, score)

    return fitness_fn


def create_code_fitness() -> Callable:
    """Create fitness function optimized for code evaluation."""
    def fitness_fn(agent, task: str, response: str) -> float:
        score = 0.0

        # Code block presence
        if "```" in response:
            score += 3.0

        # Python syntax
        python_markers = ["def ", "class ", "import ", "return ", "if ", "for ", "while "]
        for marker in python_markers:
            if marker in response:
                score += 0.5

        # Docstrings
        if '"""' in response or "'''" in response:
            score += 1.0

        # Type hints
        if "->" in response or ": str" in response or ": int" in response:
            score += 1.0

        # Error handling
        if "try:" in response or "except" in response:
            score += 1.0

        # Length sanity
        if 100 < len(response) < 2000:
            score += 1.5

        return min(10.0, score)

    return fitness_fn
