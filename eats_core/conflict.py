# conflict.py - Conflict Detection and Resolution
"""
Multi-agent conflict detection and resolution system.

Architecture:
- ConflictDetector: Analyze outputs for contradictions (heuristic + LLM)
- ConflictResolver: Arbitrate conflicts using meta-agent reasoning
- Integration: Seamless with ResultPipeline

Design Principles:
- Separation of Concerns: Detection ≠ Resolution
- Dependency Injection: Pluggable LLM providers
- Incremental: Fast heuristics first, LLM fallback
- Observable: Events for monitoring
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from .pipeline import FusedOutput
from .judge import LLMJudge, Fitness
from .events import EventBus, EventType


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConflictType(str, Enum):
    """Types of conflicts between outputs."""
    FACTUAL = "factual"          # Contradictory facts/data
    APPROACH = "approach"        # Incompatible methods
    OPINION = "opinion"          # Differing viewpoints
    NUMERICAL = "numerical"      # Divergent numbers
    BOOLEAN = "boolean"          # Yes vs No
    NONE = "none"                # No conflict


@dataclass
class Conflict:
    """
    A detected conflict between agent outputs.

    Attributes:
        outputs: The conflicting outputs
        conflict_type: Type of conflict
        severity: 0-1 score (0=minor, 1=severe)
        description: Human-readable explanation
        evidence: Supporting data for the conflict
    """
    outputs: List[FusedOutput]
    conflict_type: ConflictType
    severity: float
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.conflict_type.value,
            "severity": round(self.severity, 3),
            "description": self.description,
            "sources": [o.agent_id for o in self.outputs],
            "evidence": self.evidence,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Conflict Detector
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConflictDetector:
    """
    Detect conflicts between agent outputs.

    Strategy:
    1. Fast heuristic checks (keyword contradictions, numerical divergence)
    2. LLM-enhanced semantic analysis (optional, for ambiguous cases)

    Usage:
        detector = ConflictDetector()
        outputs = [output1, output2, output3]
        conflicts = detector.detect(outputs)
    """

    def __init__(
        self,
        llm_judge: Optional[LLMJudge] = None,
        use_llm: bool = False,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize detector.

        Args:
            llm_judge: Optional LLM for semantic analysis
            use_llm: Whether to use LLM for detection (slower but more accurate)
            event_bus: Optional event bus for observability
        """
        self.llm_judge = llm_judge
        self.use_llm = use_llm
        self.event_bus = event_bus

        # Contradiction patterns
        self.boolean_pairs = [
            ("yes", "no"),
            ("true", "false"),
            ("correct", "incorrect"),
            ("valid", "invalid"),
            ("possible", "impossible"),
        ]

    def detect(self, outputs: List[FusedOutput]) -> List[Conflict]:
        """
        Detect conflicts between outputs.

        Args:
            outputs: List of agent outputs to analyze

        Returns:
            List of detected conflicts (empty if none)
        """
        if len(outputs) < 2:
            return []

        conflicts = []

        # Pairwise comparison
        for i, out_a in enumerate(outputs):
            for out_b in outputs[i+1:]:
                conflict = self._compare_pair(out_a, out_b)
                if conflict.conflict_type != ConflictType.NONE:
                    conflicts.append(conflict)
                    self._emit_event(conflict)

        return conflicts

    def _compare_pair(
        self,
        a: FusedOutput,
        b: FusedOutput,
    ) -> Conflict:
        """Compare two outputs for conflicts."""
        # Fast heuristic checks first
        conflict = self._heuristic_check(a, b)

        # If ambiguous and LLM available, do semantic analysis
        if conflict.conflict_type == ConflictType.NONE and self.use_llm and self.llm_judge:
            conflict = self._llm_check(a, b)

        return conflict

    def _heuristic_check(self, a: FusedOutput, b: FusedOutput) -> Conflict:
        """Fast heuristic conflict detection."""
        text_a = a.content.lower()
        text_b = b.content.lower()

        # Check 1: Boolean contradictions
        boolean_conflict = self._check_boolean_contradiction(text_a, text_b)
        if boolean_conflict:
            return Conflict(
                outputs=[a, b],
                conflict_type=ConflictType.BOOLEAN,
                severity=0.8,
                description=f"Boolean contradiction detected: {boolean_conflict}",
                evidence={"pattern": boolean_conflict},
            )

        # Check 2: Numerical divergence
        nums_a = self._extract_numbers(text_a)
        nums_b = self._extract_numbers(text_b)
        if nums_a and nums_b:
            divergence = self._numerical_divergence(nums_a, nums_b)
            if divergence >= 0.4:  # >=40% difference
                return Conflict(
                    outputs=[a, b],
                    conflict_type=ConflictType.NUMERICAL,
                    severity=min(1.0, divergence),
                    description=f"Numerical divergence: {divergence:.1%}",
                    evidence={"divergence": divergence, "nums_a": nums_a[:3], "nums_b": nums_b[:3]},
                )

        # Check 3: Fitness gap (indirect indicator)
        fitness_gap = abs(a.fitness - b.fitness)
        if fitness_gap > 5.0:  # Large quality difference
            return Conflict(
                outputs=[a, b],
                conflict_type=ConflictType.OPINION,
                severity=min(1.0, fitness_gap / 10.0),
                description=f"Large fitness gap: {fitness_gap:.1f}",
                evidence={"fitness_a": a.fitness, "fitness_b": b.fitness},
            )

        # No conflict detected
        return Conflict(
            outputs=[a, b],
            conflict_type=ConflictType.NONE,
            severity=0.0,
            description="No conflict detected",
        )

    def _check_boolean_contradiction(self, text_a: str, text_b: str) -> Optional[str]:
        """Check for boolean contradictions (yes/no, true/false, etc.)."""
        for pos, neg in self.boolean_pairs:
            # Look for clear statements
            if (f" {pos} " in text_a or f" {pos}." in text_a) and \
               (f" {neg} " in text_b or f" {neg}." in text_b):
                return f"{pos} vs {neg}"
            if (f" {neg} " in text_a or f" {neg}." in text_a) and \
               (f" {pos} " in text_b or f" {pos}." in text_b):
                return f"{neg} vs {pos}"
        return None

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numerical values from text."""
        # Match integers and floats
        pattern = r'\b\d+(?:\.\d+)?\b'
        matches = re.findall(pattern, text)
        return [float(m) for m in matches]

    def _numerical_divergence(self, nums_a: List[float], nums_b: List[float]) -> float:
        """Calculate divergence between two number sets."""
        if not nums_a or not nums_b:
            return 0.0

        # Simple: compare first number (often the main result)
        a, b = nums_a[0], nums_b[0]
        if a == 0 and b == 0:
            return 0.0

        # Relative difference
        diff = abs(a - b) / max(abs(a), abs(b))
        return diff

    def _llm_check(self, a: FusedOutput, b: FusedOutput) -> Conflict:
        """LLM-enhanced semantic conflict detection."""
        if not self.llm_judge:
            return Conflict(
                outputs=[a, b],
                conflict_type=ConflictType.NONE,
                severity=0.0,
                description="LLM not available",
            )

        prompt = f"""Analyze these two outputs for contradictions:

Output A (from {a.agent_id}, fitness={a.fitness:.1f}):
{a.content[:500]}

Output B (from {b.agent_id}, fitness={b.fitness:.1f}):
{b.content[:500]}

Are there any contradictions? Answer in JSON:
{{
    "has_conflict": true/false,
    "type": "factual/approach/opinion/none",
    "severity": 0.0-1.0,
    "description": "brief explanation"
}}
"""

        try:
            if not self.llm_judge.judge_fn:
                return Conflict(
                    outputs=[a, b],
                    conflict_type=ConflictType.NONE,
                    severity=0.0,
                    description="LLM judge_fn not available",
                )

            response = self.llm_judge.judge_fn(prompt)
            result = self._parse_json_response(response)

            if result.get("has_conflict"):
                conflict_type = ConflictType(result.get("type", "opinion"))
                return Conflict(
                    outputs=[a, b],
                    conflict_type=conflict_type,
                    severity=result.get("severity", 0.5),
                    description=result.get("description", "LLM detected conflict"),
                    evidence={"llm_analysis": result},
                )
        except Exception as e:
            # LLM failed, fallback to no conflict
            pass

        return Conflict(
            outputs=[a, b],
            conflict_type=ConflictType.NONE,
            severity=0.0,
            description="No conflict (LLM analysis)",
        )

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Extract JSON block
        match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}

    def _emit_event(self, conflict: Conflict) -> None:
        """Emit conflict detection event."""
        if self.event_bus:
            # Create custom event type (not in EventType enum yet)
            try:
                from .events import Event
                event = Event(
                    type=EventType.CUSTOM,
                    source="conflict_detector",
                    data={
                        "conflict": conflict.to_dict(),
                    },
                )
                # Note: EventBus.publish is async, skip for now
                # Could use asyncio.create_task if needed
            except:
                pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Conflict Resolver
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConflictResolver:
    """
    Resolve conflicts using meta-agent arbitration.

    Strategy:
    1. Analyze conflicting outputs
    2. Generate synthesis prompt
    3. Use LLM to produce resolution
    4. Score resolution quality

    Usage:
        resolver = ConflictResolver(llm_judge)
        resolution = resolver.resolve(conflict)
    """

    def __init__(
        self,
        llm_judge: Optional[LLMJudge] = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize resolver.

        Args:
            llm_judge: LLM for arbitration (required)
            event_bus: Optional event bus for observability
        """
        self.llm_judge = llm_judge or LLMJudge()
        self.event_bus = event_bus

    def resolve(self, conflict: Conflict) -> FusedOutput:
        """
        Arbitrate a conflict between outputs.

        Args:
            conflict: The conflict to resolve

        Returns:
            Synthesized resolution output
        """
        # Build arbitration prompt
        prompt = self._build_prompt(conflict)

        # Generate resolution
        if self.llm_judge.judge_fn:
            resolution_text = self.llm_judge.judge_fn(prompt)
        else:
            # Fallback: simple synthesis without LLM
            resolution_text = self._fallback_resolution(conflict)

        # Score quality
        fitness = self._score_resolution(resolution_text, conflict)

        # Create fused output
        from .pipeline import FusionMethod
        resolution = FusedOutput(
            agent_id="conflict_resolver",
            content=resolution_text,
            fitness=fitness,
            source_ids=[o.agent_id for o in conflict.outputs],
            fusion_method=FusionMethod.SYNTHESIZE,  # Use SYNTHESIZE as proxy for ARBITRATION
            metadata={
                "conflict_type": conflict.conflict_type.value,
                "conflict_severity": conflict.severity,
                "sources": len(conflict.outputs),
                "arbitration": True,
            },
        )

        self._emit_event(conflict, resolution)
        return resolution

    def _build_prompt(self, conflict: Conflict) -> str:
        """Build arbitration prompt for meta-agent."""
        outputs_text = "\n\n---\n\n".join([
            f"Output {i+1} (from {o.agent_id}, fitness={o.fitness:.1f}):\n{o.content[:600]}"
            for i, o in enumerate(conflict.outputs)
        ])

        # Customize by conflict type
        if conflict.conflict_type == ConflictType.FACTUAL:
            task = """Identify which output contains accurate information. If both have merit,
synthesize them. Cite sources and explain your reasoning."""

        elif conflict.conflict_type == ConflictType.BOOLEAN:
            task = """Determine the correct answer to the yes/no question. Analyze the
evidence in each output and make a clear determination."""

        elif conflict.conflict_type == ConflictType.NUMERICAL:
            task = """Reconcile the numerical discrepancy. Check calculations, explain
the difference, and provide the correct value."""

        elif conflict.conflict_type == ConflictType.APPROACH:
            task = """Evaluate the different approaches. Recommend the best one or
synthesize a hybrid approach. Explain trade-offs."""

        else:  # OPINION
            task = """Synthesize the different viewpoints. Present a balanced perspective
that incorporates insights from both outputs."""

        return f"""You are a meta-agent resolving conflicts between multiple agent outputs.

CONFLICT DETAILS:
Type: {conflict.conflict_type.value}
Severity: {conflict.severity:.2f}
Description: {conflict.description}

CONFLICTING OUTPUTS:
{outputs_text}

TASK:
{task}

Provide a clear, authoritative resolution that:
1. Acknowledges the conflict
2. Analyzes each position
3. Provides synthesis/resolution
4. Explains reasoning

Be concise but thorough. Cite which outputs you drew from (Output 1, Output 2, etc.).
"""

    def _score_resolution(self, resolution: str, conflict: Conflict) -> float:
        """Heuristic fitness for resolution quality."""
        score = 5.0  # Base score

        # Check length (should be substantial)
        length = len(resolution)
        if length < 100:
            score -= 2.0
        elif length > 200:
            score += 1.0

        # Check for reasoning markers
        reasoning_markers = ["because", "since", "therefore", "evidence", "analysis", "due to"]
        if any(m in resolution.lower() for m in reasoning_markers):
            score += 1.5

        # Check for synthesis markers
        synthesis_markers = ["combining", "reconcile", "both", "synthesis", "integrate", "merge"]
        if any(m in resolution.lower() for m in synthesis_markers):
            score += 1.5

        # Check for citations
        if "output 1" in resolution.lower() or "output 2" in resolution.lower():
            score += 1.0

        # Bonus for higher severity conflicts resolved
        score += conflict.severity * 0.5

        return min(10.0, max(0.0, score))

    def _fallback_resolution(self, conflict: Conflict) -> str:
        """
        Fallback resolution when LLM is not available.

        Simple heuristic: choose highest fitness output and note the conflict.
        """
        best = max(conflict.outputs, key=lambda o: o.fitness)
        other_sources = [o.agent_id for o in conflict.outputs if o.agent_id != best.agent_id]

        return f"""Conflict Resolution ({conflict.conflict_type.value}, severity={conflict.severity:.2f}):

Selected Output (from {best.agent_id}, fitness={best.fitness:.1f}):
{best.content[:400]}

Note: This conflicts with outputs from {', '.join(other_sources)}.
Conflict: {conflict.description}

Resolution: Based on fitness scores, accepting the output from {best.agent_id} as primary.
"""

    def _emit_event(self, conflict: Conflict, resolution: FusedOutput) -> None:
        """Emit conflict resolution event."""
        if self.event_bus:
            try:
                from .events import Event
                event = Event(
                    type=EventType.CUSTOM,
                    source="conflict_resolver",
                    data={
                        "conflict": conflict.to_dict(),
                        "resolution": resolution.to_dict(),
                    },
                )
            except:
                pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_conflicts(
    outputs: List[FusedOutput],
    use_llm: bool = False,
    llm_judge: Optional[LLMJudge] = None,
) -> List[Conflict]:
    """
    Convenience function to detect conflicts.

    Args:
        outputs: Outputs to analyze
        use_llm: Whether to use LLM for detection
        llm_judge: Optional LLM judge

    Returns:
        List of conflicts
    """
    detector = ConflictDetector(llm_judge=llm_judge, use_llm=use_llm)
    return detector.detect(outputs)


def resolve_conflict(
    conflict: Conflict,
    llm_judge: Optional[LLMJudge] = None,
) -> FusedOutput:
    """
    Convenience function to resolve a conflict.

    Args:
        conflict: The conflict to resolve
        llm_judge: Optional LLM judge

    Returns:
        Resolution output
    """
    resolver = ConflictResolver(llm_judge=llm_judge)
    return resolver.resolve(conflict)
