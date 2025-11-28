# llm_judge.py
"""
LLM-as-Judge Fitness Evaluation.

Implements sophisticated fitness evaluation using LLM judgment:
- Quality scoring via structured prompts
- Multi-criteria evaluation
- Inter-agent cooperation assessment
- Comparison-based ranking
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable

from .agents import AgentSession
from .config_models import TaskSpec
from .evolution_engine import FitnessResult


@dataclass
class JudgeCriteria:
    """Criteria for LLM judgment."""
    name: str
    description: str
    weight: float = 1.0
    max_score: float = 10.0


DEFAULT_CRITERIA = [
    JudgeCriteria(
        name="correctness",
        description="Is the response factually correct and technically accurate?",
        weight=2.0,
    ),
    JudgeCriteria(
        name="completeness",
        description="Does the response fully address all aspects of the task?",
        weight=1.5,
    ),
    JudgeCriteria(
        name="clarity",
        description="Is the response clear, well-organized, and easy to understand?",
        weight=1.0,
    ),
    JudgeCriteria(
        name="efficiency",
        description="Is the solution efficient and well-optimized?",
        weight=1.0,
    ),
    JudgeCriteria(
        name="creativity",
        description="Does the response show creative problem-solving?",
        weight=0.5,
    ),
]


# ─────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────

JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator assessing the quality of an AI agent's response.

TASK DESCRIPTION:
{task_description}

AGENT RESPONSE:
{response}

Please evaluate this response on the following criteria. For each criterion, provide a score from 0-10 and a brief justification.

{criteria_list}

Respond in JSON format:
{{
    "scores": {{
        "criterion_name": {{"score": X, "justification": "..."}},
        ...
    }},
    "overall_assessment": "Brief overall assessment",
    "suggestions": ["improvement suggestion 1", ...]
}}
"""

COMPARISON_PROMPT_TEMPLATE = """You are comparing multiple AI agent responses to determine which is best.

TASK DESCRIPTION:
{task_description}

CANDIDATE RESPONSES:
{candidates}

Rank these responses from best to worst. Consider:
- Correctness and accuracy
- Completeness of solution
- Code quality (if applicable)
- Clarity of explanation

Respond in JSON format:
{{
    "ranking": ["agent_id_1", "agent_id_2", ...],  // best to worst
    "scores": {{"agent_id": score, ...}},  // 0-10 scores
    "analysis": "Brief comparison analysis"
}}
"""

COOPERATION_PROMPT_TEMPLATE = """Evaluate how well this agent's output builds on and cooperates with previous agent outputs.

PREVIOUS AGENT OUTPUT:
{previous_output}

CURRENT AGENT OUTPUT:
{current_output}

TASK:
{task_description}

Evaluate cooperation on:
1. Context awareness: Does it acknowledge/use information from previous output?
2. Complementarity: Does it add value rather than duplicate?
3. Consistency: Is it consistent with previous decisions/approaches?

Respond in JSON format:
{{
    "context_awareness": {{"score": X, "note": "..."}},
    "complementarity": {{"score": X, "note": "..."}},
    "consistency": {{"score": X, "note": "..."}},
    "cooperation_score": X,  // 0-10 overall
    "assessment": "Brief assessment"
}}
"""


class LLMJudge:
    """
    LLM-based fitness evaluator.

    Uses an LLM (via agent session or API) to judge output quality.

    Usage:
        judge = LLMJudge(judge_agent_session)
        result = await judge.evaluate(task, agent_session, response)
    """

    def __init__(
        self,
        judge_session: Optional[AgentSession] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        criteria: Optional[List[JudgeCriteria]] = None,
    ):
        """
        Args:
            judge_session: An AgentSession to use for judging
            judge_fn: Alternative: a function that takes prompt and returns response
            criteria: Custom evaluation criteria
        """
        self.judge_session = judge_session
        self.judge_fn = judge_fn
        self.criteria = criteria or DEFAULT_CRITERIA

        if not judge_session and not judge_fn:
            # Fall back to heuristic evaluation
            self.judge_fn = self._heuristic_judge

    async def evaluate(
        self,
        task: TaskSpec,
        session: AgentSession,
        response: str,
    ) -> FitnessResult:
        """
        Evaluate an agent's response using LLM judgment.

        Returns a FitnessResult with detailed metrics.
        """
        # Build criteria list for prompt
        criteria_list = "\n".join(
            f"- {c.name}: {c.description} (weight: {c.weight})"
            for c in self.criteria
        )

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            task_description=task.description,
            response=response[:3000],  # Truncate very long responses
            criteria_list=criteria_list,
        )

        # Get judgment
        if self.judge_session:
            judge_response = self.judge_session.send_prompt(prompt)
        else:
            judge_response = self.judge_fn(prompt)

        # Parse response
        metrics, overall_score = self._parse_judgment(judge_response)

        return FitnessResult(
            blueprint_id=session.blueprint.id,
            session_id=session.id,
            fitness_score=overall_score,
            metrics=metrics,
            response=response,
        )

    def _parse_judgment(self, response: str) -> tuple[Dict[str, float], float]:
        """Parse the judge's JSON response into metrics and score."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                scores = data.get("scores", {})

                metrics = {}
                weighted_sum = 0.0
                total_weight = 0.0

                for criterion in self.criteria:
                    if criterion.name in scores:
                        score_data = scores[criterion.name]
                        score = score_data.get("score", 5.0) if isinstance(score_data, dict) else float(score_data)
                        metrics[criterion.name] = score
                        weighted_sum += score * criterion.weight
                        total_weight += criterion.weight

                overall = weighted_sum / total_weight if total_weight > 0 else 5.0
                return metrics, overall

        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Fallback: try to extract any numbers
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response)
        if numbers:
            scores = [float(n) for n in numbers if 0 <= float(n) <= 10]
            if scores:
                return {"extracted": sum(scores) / len(scores)}, sum(scores) / len(scores)

        # Default fallback
        return {"default": 5.0}, 5.0

    def _heuristic_judge(self, prompt: str) -> str:
        """
        Fallback heuristic judge when no LLM is available.

        Extracts the response from the prompt and applies heuristics.
        """
        # Extract the response section
        response_match = re.search(r'AGENT RESPONSE:\s*(.*?)(?=Please evaluate|$)', prompt, re.DOTALL)
        response = response_match.group(1).strip() if response_match else ""

        # Apply heuristics
        scores = {}

        # Correctness: presence of code/structure
        correctness = 5.0
        if "def " in response or "class " in response:
            correctness += 2.0
        if "error" in response.lower() or "exception" in response.lower():
            correctness -= 2.0
        scores["correctness"] = min(10.0, max(0.0, correctness))

        # Completeness: length-based
        length = len(response)
        if length < 50:
            completeness = 2.0
        elif length < 200:
            completeness = 5.0
        elif length < 1000:
            completeness = 7.0
        else:
            completeness = 8.0
        scores["completeness"] = completeness

        # Clarity: structure presence
        clarity = 5.0
        if any(marker in response for marker in ["1.", "2.", "- ", "* ", "```"]):
            clarity += 2.0
        scores["clarity"] = clarity

        # Build JSON response
        return json.dumps({
            "scores": {k: {"score": v, "justification": "heuristic"} for k, v in scores.items()},
            "overall_assessment": "Heuristic evaluation",
            "suggestions": [],
        })

    async def compare_responses(
        self,
        task: TaskSpec,
        responses: Dict[str, str],  # agent_id -> response
    ) -> Dict[str, float]:
        """
        Compare multiple responses and return relative scores.

        Useful for tournament-style selection.
        """
        candidates = "\n\n".join(
            f"=== Agent: {aid} ===\n{resp[:1000]}"
            for aid, resp in responses.items()
        )

        prompt = COMPARISON_PROMPT_TEMPLATE.format(
            task_description=task.description,
            candidates=candidates,
        )

        if self.judge_session:
            judge_response = self.judge_session.send_prompt(prompt)
        else:
            judge_response = self.judge_fn(prompt)

        # Parse ranking
        try:
            json_match = re.search(r'\{[\s\S]*\}', judge_response)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("scores", {aid: 5.0 for aid in responses})
        except Exception:
            pass

        # Fallback: equal scores
        return {aid: 5.0 for aid in responses}

    async def evaluate_cooperation(
        self,
        task: TaskSpec,
        previous_output: str,
        current_output: str,
    ) -> float:
        """
        Evaluate how well an agent cooperates with previous outputs.

        Returns a cooperation score (0-10).
        """
        prompt = COOPERATION_PROMPT_TEMPLATE.format(
            task_description=task.description,
            previous_output=previous_output[:1000],
            current_output=current_output[:1000],
        )

        if self.judge_session:
            judge_response = self.judge_session.send_prompt(prompt)
        else:
            judge_response = self.judge_fn(prompt)

        try:
            json_match = re.search(r'\{[\s\S]*\}', judge_response)
            if json_match:
                data = json.loads(json_match.group())
                return float(data.get("cooperation_score", 5.0))
        except Exception:
            pass

        return 5.0


# ─────────────────────────────────────────────────────────
# Fitness Function Factory
# ─────────────────────────────────────────────────────────

def create_llm_judge_fitness(
    judge_session: Optional[AgentSession] = None,
) -> Callable:
    """
    Create a fitness function that uses LLM-as-judge.

    Can be passed to EvolutionEngine.run_evolution().
    """
    judge = LLMJudge(judge_session=judge_session)

    def fitness_fn(task: TaskSpec, session: AgentSession, response: str) -> FitnessResult:
        import asyncio
        # Run async evaluation in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(judge.evaluate(task, session, response))
            return result
        finally:
            loop.close()

    return fitness_fn


def create_hybrid_fitness(
    llm_weight: float = 0.6,
    heuristic_weight: float = 0.4,
) -> Callable:
    """
    Create a hybrid fitness function combining LLM and heuristic evaluation.

    Useful when LLM judge is expensive or slow.
    """
    from .evolution_engine import combined_fitness

    judge = LLMJudge()  # Will use heuristic fallback

    def fitness_fn(task: TaskSpec, session: AgentSession, response: str) -> FitnessResult:
        # Get heuristic score
        heuristic_result = combined_fitness(task, session, response)

        # Get LLM-style score (using heuristic judge)
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            llm_result = loop.run_until_complete(judge.evaluate(task, session, response))
        finally:
            loop.close()

        # Combine scores
        combined_score = (
            llm_result.fitness_score * llm_weight +
            heuristic_result.fitness_score * heuristic_weight
        )

        return FitnessResult(
            blueprint_id=session.blueprint.id,
            session_id=session.id,
            fitness_score=combined_score,
            metrics={
                **heuristic_result.metrics,
                "llm_score": llm_result.fitness_score,
                "heuristic_score": heuristic_result.fitness_score,
            },
            response=response,
        )

    return fitness_fn
