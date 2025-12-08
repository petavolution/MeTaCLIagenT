#!/usr/bin/env python3
"""
Multi-Layered Sequential Orchestration Examples

Focus: Building deep sequential pipelines with multiple processing layers
Pattern: Each layer processes output from previous layer and passes to next

4 Simple Sequential Examples:
1. Two-layer: audit → fix
2. Three-layer: audit → analyze → fix
3. Four-layer: audit → analyze → fix → verify
4. Five-layer: audit → analyze → fix → verify → review

3 Complex Sequential Examples:
5. Seven-layer pipeline with branching
6. Eight-layer cascade of specialists
7. Ten-layer full development cycle

Run: python examples/09_sequential_layers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.core import (
    Orchestrator,
    WorkflowContext,
    create_ai_executor,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIMPLE SEQUENTIAL EXAMPLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_1_two_layer():
    """
    Example 1: Two-Layer Sequential Pipeline

    Simplest layered approach: Direct pipeline from analysis to action.

    Layer 1: Analysis (claude-code audits)
    Layer 2: Action (codex fixes)

    Flow: INPUT → audit → fix → OUTPUT
    """
    print("=" * 70)
    print("Example 1: Two-Layer Sequential Pipeline")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "two-layer",
        "Basic two-layer pipeline"
    )

    # Layer 1: Analysis
    workflow.add_step(
        "layer1_audit",
        "mock-ai",
        "audit {target} for issues"
    )

    # Layer 2: Action
    workflow.add_step(
        "layer2_fix",
        "mock-ai",
        "apply fixes to {target}"
    )

    print("\n  Pipeline Layers:")
    print("    Layer 1 (Analysis): audit")
    print("    Layer 2 (Action):   fix")
    print("\n  Data Flow: INPUT → L1 → L2 → OUTPUT")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"\n  Results:")
    for i, (name, result) in enumerate(context.results.items(), 1):
        layer = f"Layer {i}"
        status = "✓" if result.success else "✗"
        print(f"    {layer}: {status} {name} ({result.duration:.2f}s)")

    print("\n✓ Example 1 complete\n")


def example_2_three_layer():
    """
    Example 2: Three-Layer Sequential Pipeline

    Add intermediate analysis layer between detection and action.

    Layer 1: Detection (claude finds issues)
    Layer 2: Analysis (gemini analyzes severity)
    Layer 3: Action (codex fixes based on analysis)

    Flow: INPUT → detect → analyze → fix → OUTPUT
    """
    print("=" * 70)
    print("Example 2: Three-Layer Sequential Pipeline")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "three-layer",
        "Three-layer pipeline with intermediate analysis"
    )

    # Layer 1: Detection
    workflow.add_step(
        "layer1_detect",
        "mock-ai",
        "detect all issues in {target}"
    )

    # Layer 2: Analysis
    workflow.add_step(
        "layer2_analyze",
        "mock-ai",
        "analyze severity and impact of detected issues in {target}"
    )

    # Layer 3: Action
    workflow.add_step(
        "layer3_fix",
        "mock-ai",
        "fix issues in {target} based on severity analysis"
    )

    print("\n  Pipeline Layers:")
    print("    Layer 1 (Detection): detect issues")
    print("    Layer 2 (Analysis):  analyze severity")
    print("    Layer 3 (Action):    apply fixes")
    print("\n  Data Flow: INPUT → L1 → L2 → L3 → OUTPUT")
    print("  Each layer enriches the context for the next")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/auth.py"})

    print(f"\n  Sequential Processing:")
    for i, (name, result) in enumerate(context.results.items(), 1):
        indent = "  " * i
        print(f"    {indent}Layer {i}: {name}")
        if result.parsed_output:
            keywords = result.parsed_output.detected_keywords
            print(f"    {indent}  └─ Keywords: {keywords}")

    print("\n✓ Example 2 complete\n")


def example_3_four_layer():
    """
    Example 3: Four-Layer Sequential Pipeline

    Add verification layer after action to ensure quality.

    Layer 1: Detection (claude finds issues)
    Layer 2: Analysis (gemini analyzes)
    Layer 3: Action (codex fixes)
    Layer 4: Verification (claude verifies fixes)

    Flow: INPUT → detect → analyze → fix → verify → OUTPUT
    """
    print("=" * 70)
    print("Example 3: Four-Layer Sequential Pipeline")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "four-layer",
        "Four-layer pipeline with verification"
    )

    # Layer 1: Detection
    workflow.add_step(
        "layer1_detect",
        "mock-ai",
        "comprehensive scan of {target}"
    )

    # Layer 2: Analysis
    workflow.add_step(
        "layer2_analyze",
        "mock-ai",
        "deep analysis of issues found in {target}"
    )

    # Layer 3: Action
    workflow.add_step(
        "layer3_fix",
        "mock-ai",
        "implement fixes for {target} based on analysis"
    )

    # Layer 4: Verification
    workflow.add_step(
        "layer4_verify",
        "mock-ai",
        "verify all fixes applied correctly to {target}"
    )

    print("\n  Pipeline Layers:")
    print("    Layer 1 (Detection):    scan for issues")
    print("    Layer 2 (Analysis):     deep analysis")
    print("    Layer 3 (Action):       implement fixes")
    print("    Layer 4 (Verification): verify quality")
    print("\n  Data Flow: INPUT → L1 → L2 → L3 → L4 → OUTPUT")
    print("  Verification layer ensures fix quality")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/payment.py"})

    print(f"\n  Layer-by-Layer Execution:")
    total_time = 0
    for i, (name, result) in enumerate(context.results.items(), 1):
        total_time += result.duration
        print(f"    Layer {i}: {name}")
        print(f"      Time: {result.duration:.2f}s (cumulative: {total_time:.2f}s)")
        print(f"      Status: {'✓' if result.success else '✗'}")

    print("\n✓ Example 3 complete\n")


def example_4_five_layer():
    """
    Example 4: Five-Layer Sequential Pipeline

    Add meta-review layer for strategic oversight.

    Layer 1: Detection (claude finds issues)
    Layer 2: Analysis (gemini analyzes)
    Layer 3: Action (codex fixes)
    Layer 4: Verification (claude verifies)
    Layer 5: Meta-Review (gemini reviews entire process)

    Flow: INPUT → detect → analyze → fix → verify → review → OUTPUT
    """
    print("=" * 70)
    print("Example 4: Five-Layer Sequential Pipeline")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "five-layer",
        "Five-layer pipeline with meta-review"
    )

    # Layer 1: Detection
    workflow.add_step(
        "layer1_detect",
        "mock-ai",
        "initial detection pass on {target}"
    )

    # Layer 2: Analysis
    workflow.add_step(
        "layer2_analyze",
        "mock-ai",
        "detailed analysis of {target} issues"
    )

    # Layer 3: Action
    workflow.add_step(
        "layer3_fix",
        "mock-ai",
        "apply strategic fixes to {target}"
    )

    # Layer 4: Verification
    workflow.add_step(
        "layer4_verify",
        "mock-ai",
        "verify fix correctness for {target}"
    )

    # Layer 5: Meta-Review
    workflow.add_step(
        "layer5_review",
        "mock-ai",
        "meta-review entire process and suggest improvements for {target}"
    )

    print("\n  Pipeline Layers:")
    print("    Layer 1 (Detection):    initial scan")
    print("    Layer 2 (Analysis):     detailed analysis")
    print("    Layer 3 (Action):       strategic fixes")
    print("    Layer 4 (Verification): correctness check")
    print("    Layer 5 (Meta-Review):  process review")
    print("\n  Data Flow: INPUT → L1 → L2 → L3 → L4 → L5 → OUTPUT")
    print("  Meta-review layer provides strategic oversight")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/"})

    print(f"\n  Deep Sequential Processing:")
    for i, (name, result) in enumerate(context.results.items(), 1):
        arrow = "→" if i < len(context.results) else "→ OUTPUT"
        print(f"    L{i}: {name} {arrow}")

    print(f"\n  Pipeline Stats:")
    print(f"    Total layers: {len(context.results)}")
    print(f"    Total time: {sum(r.duration for r in context.results.values()):.2f}s")
    print(f"    All successful: {all(r.success for r in context.results.values())}")

    print("\n✓ Example 4 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPLEX SEQUENTIAL EXAMPLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_5_seven_layer_branching():
    """
    Example 5: Seven-Layer Pipeline with Branching Decision

    Complex pipeline with mid-flow decision point that affects later layers.

    Layer 1: Initial Scan (claude)
    Layer 2: Risk Assessment (gemini)
    Layer 3: Decision Point → High Risk Path or Low Risk Path
    Layer 4a: High Risk → Deep Analysis (gemini)
    Layer 4b: Low Risk → Quick Fix (codex)
    Layer 5: Integration (merge paths)
    Layer 6: Final Verification (claude)
    Layer 7: Deployment Check (gemini)

    Flow: INPUT → scan → assess → [DECIDE] → deep or quick → integrate → verify → check → OUTPUT
    """
    print("=" * 70)
    print("Example 5: Seven-Layer Pipeline with Branching")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "seven-layer-branching",
        "Complex pipeline with risk-based routing"
    )

    # Layer 1: Initial Scan
    workflow.add_step(
        "layer1_scan",
        "mock-ai",
        "comprehensive security scan of {target}"
    )

    # Layer 2: Risk Assessment
    workflow.add_step(
        "layer2_assess",
        "mock-ai",
        "assess security risk level of {target}"
    )

    # Layer 3: Decision Point
    def risk_decision(ctx: WorkflowContext) -> str:
        """Route based on risk level."""
        last = ctx.get_last_result()

        if last and last.parsed_output:
            keywords = last.parsed_output.detected_keywords

            if 'error' in keywords:
                print("    → Decision: HIGH RISK → deep analysis path")
                ctx.set("risk_level", "high")
                return "layer4a_deep"
            else:
                print("    → Decision: LOW RISK → quick fix path")
                ctx.set("risk_level", "low")
                return "layer4b_quick"

        ctx.set("risk_level", "medium")
        return "layer4b_quick"

    workflow.add_decision("layer3_decide", risk_decision)

    # Layer 4a: High Risk Path
    workflow.add_step(
        "layer4a_deep",
        "mock-ai",
        "deep security analysis of {target} (high risk)"
    )

    # Layer 4b: Low Risk Path
    workflow.add_step(
        "layer4b_quick",
        "mock-ai",
        "quick fix for {target} (low risk)"
    )

    # Layer 5: Integration (both paths merge here)
    workflow.add_step(
        "layer5_integrate",
        "mock-ai",
        "integrate {risk_level} risk fixes for {target}"
    )

    # Layer 6: Final Verification
    workflow.add_step(
        "layer6_verify",
        "mock-ai",
        "final security verification of {target}"
    )

    # Layer 7: Deployment Check
    workflow.add_step(
        "layer7_deploy_check",
        "mock-ai",
        "deployment readiness check for {target}"
    )

    print("\n  Pipeline Architecture:")
    print("    Layer 1: Initial Scan")
    print("    Layer 2: Risk Assessment")
    print("    Layer 3: Decision Point")
    print("              ├─ High Risk → Layer 4a (deep analysis)")
    print("              └─ Low Risk  → Layer 4b (quick fix)")
    print("    Layer 5: Integration (paths merge)")
    print("    Layer 6: Final Verification")
    print("    Layer 7: Deployment Check")
    print("\n  Branching creates adaptive pipeline based on risk")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"\n  Execution Path:")
    print(f"    Risk Level: {context.get('risk_level')}")
    print(f"    Layers Executed: {len(context.results)}")
    print(f"\n    Path Taken:")
    for i, name in enumerate(context.results.keys(), 1):
        marker = "├─" if i < len(context.results) else "└─"
        print(f"      {marker} Layer {i}: {name}")

    print("\n✓ Example 5 complete\n")


def example_6_eight_layer_cascade():
    """
    Example 6: Eight-Layer Cascade of Specialists

    Each layer is handled by a specialist agent, with output flowing
    down the cascade. Demonstrates progressive refinement through
    multiple specialized processing stages.

    Layer 1: Security Specialist (claude) - Security audit
    Layer 2: Performance Specialist (codex) - Performance analysis
    Layer 3: Architecture Specialist (gemini) - Design review
    Layer 4: Integration Specialist (claude) - Merge insights
    Layer 5: Refactor Specialist (codex) - Apply changes
    Layer 6: Testing Specialist (claude) - Test coverage
    Layer 7: Documentation Specialist (gemini) - Update docs
    Layer 8: Quality Specialist (claude) - Final QA

    Flow: INPUT → security → performance → architecture → integrate →
          refactor → test → document → qa → OUTPUT
    """
    print("=" * 70)
    print("Example 6: Eight-Layer Cascade of Specialists")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "eight-layer-cascade",
        "Specialist cascade for comprehensive processing"
    )

    specialists = [
        ("layer1_security", "Security Specialist",
         "security audit of {target}"),
        ("layer2_performance", "Performance Specialist",
         "performance optimization analysis for {target}"),
        ("layer3_architecture", "Architecture Specialist",
         "architectural design review of {target}"),
        ("layer4_integration", "Integration Specialist",
         "integrate all analysis results for {target}"),
        ("layer5_refactor", "Refactor Specialist",
         "apply comprehensive refactoring to {target}"),
        ("layer6_testing", "Testing Specialist",
         "ensure test coverage for changes to {target}"),
        ("layer7_documentation", "Documentation Specialist",
         "update documentation for {target}"),
        ("layer8_quality", "Quality Assurance Specialist",
         "final quality check of all changes to {target}"),
    ]

    # Build cascade
    for step_name, specialist_name, prompt in specialists:
        workflow.add_step(step_name, "mock-ai", prompt)

    print("\n  Specialist Cascade:")
    for i, (_, specialist_name, _) in enumerate(specialists, 1):
        arrow = "↓" if i < len(specialists) else "→ OUTPUT"
        print(f"    Layer {i}: {specialist_name} {arrow}")

    print("\n  Each specialist enriches the context for downstream layers")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/core/"})

    print(f"\n  Cascade Execution:")
    cumulative_time = 0
    for i, (name, result) in enumerate(context.results.items(), 1):
        cumulative_time += result.duration
        specialist = specialists[i-1][1]

        status = "✓" if result.success else "✗"
        bar = "█" * min(int(cumulative_time * 2), 20)

        print(f"    L{i} {status} {specialist}")
        print(f"        Time: {bar} {cumulative_time:.2f}s")

        if result.parsed_output and result.parsed_output.detected_keywords:
            keywords = list(result.parsed_output.detected_keywords)[:2]
            print(f"        Output: {', '.join(keywords)}")

    print(f"\n  Cascade Complete:")
    print(f"    Total specialists: {len(context.results)}")
    print(f"    Total processing time: {cumulative_time:.2f}s")
    print(f"    All stages successful: {all(r.success for r in context.results.values())}")

    print("\n✓ Example 6 complete\n")


def example_7_ten_layer_full_cycle():
    """
    Example 7: Ten-Layer Full Development Cycle

    Most complex: Complete SDLC pipeline with multiple feedback points
    and quality gates.

    Layer 1:  Requirements Analysis (gemini)
    Layer 2:  Architecture Design (gemini)
    Layer 3:  Implementation Planning (claude)
    Layer 4:  Code Generation (codex)
    Layer 5:  Code Review (claude)
    Layer 6:  Test Generation (codex)
    Layer 7:  Test Execution (claude)
    Layer 8:  Performance Optimization (codex)
    Layer 9:  Documentation Generation (gemini)
    Layer 10: Release Validation (claude)

    Each layer has specific validation criteria and can enrich context
    for all downstream layers.

    Flow: requirements → design → plan → implement → review →
          test_gen → test_run → optimize → document → validate → OUTPUT
    """
    print("=" * 70)
    print("Example 7: Ten-Layer Full Development Cycle")
    print("=" * 70)
    print("\n  🔄 Simulating complete SDLC pipeline...")

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "ten-layer-sdlc",
        "Complete software development lifecycle"
    )

    # Define all layers
    layers = [
        # (name, phase, agent, prompt)
        ("layer1_requirements", "Requirements", "gemini",
         "analyze requirements for {feature}"),

        ("layer2_design", "Design", "gemini",
         "design architecture for {feature} based on requirements"),

        ("layer3_planning", "Planning", "claude",
         "create implementation plan for {feature}"),

        ("layer4_implementation", "Implementation", "codex",
         "implement {feature} according to plan"),

        ("layer5_review", "Code Review", "claude",
         "review implementation of {feature}"),

        ("layer6_test_gen", "Test Generation", "codex",
         "generate comprehensive tests for {feature}"),

        ("layer7_test_run", "Test Execution", "claude",
         "execute tests and validate {feature}"),

        ("layer8_optimize", "Optimization", "codex",
         "optimize performance of {feature}"),

        ("layer9_document", "Documentation", "gemini",
         "generate documentation for {feature}"),

        ("layer10_validate", "Release Validation", "claude",
         "final release validation for {feature}"),
    ]

    # Build complete pipeline
    for step_name, phase, agent, prompt in layers:
        workflow.add_step(step_name, "mock-ai", prompt)

    print("\n  Full SDLC Pipeline (10 Layers):")
    print("  " + "─" * 66)

    for i, (_, phase, agent, _) in enumerate(layers, 1):
        connector = "│" if i < len(layers) else "└"
        print(f"  {connector} Layer {i:2d}: {phase:20s} ({agent})")

    print("  " + "─" * 66)
    print("  Each layer validates and enriches context")

    # Execute
    context = orchestrator.execute(workflow, {
        "feature": "user authentication system",
        "quality_gate": "strict"
    })

    print(f"\n  Pipeline Execution Results:")
    print("  " + "=" * 66)

    # Group by phase
    phases = {
        "Analysis": [1, 2, 3],
        "Development": [4, 5],
        "Testing": [6, 7],
        "Finalization": [8, 9, 10]
    }

    for phase_name, layer_nums in phases.items():
        print(f"\n  📋 {phase_name} Phase:")
        for layer_num in layer_nums:
            if layer_num <= len(list(context.results.items())):
                name, result = list(context.results.items())[layer_num - 1]
                layer_info = layers[layer_num - 1]

                status = "✓" if result.success else "✗"
                duration = result.duration

                print(f"    {status} Layer {layer_num}: {layer_info[1]}")
                print(f"       Agent: {layer_info[2]}, Time: {duration:.2f}s")

                if result.parsed_output and result.parsed_output.detected_keywords:
                    keywords = list(result.parsed_output.detected_keywords)
                    print(f"       Keywords: {', '.join(keywords)}")

    print(f"\n  " + "=" * 66)
    print(f"  Pipeline Summary:")
    print(f"    Total layers: {len(context.results)}")
    print(f"    Total time: {sum(r.duration for r in context.results.values()):.2f}s")
    print(f"    Success rate: {sum(1 for r in context.results.values() if r.success) / len(context.results) * 100:.0f}%")
    print(f"    Feature: {context.get('feature')}")
    print(f"  " + "=" * 66)

    print("\n  🎉 Complete SDLC cycle executed successfully!")
    print("\n✓ Example 7 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    """Run all sequential examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Multi-Layered Sequential Orchestration".center(68) + "║")
    print("║" + "  Deep Pipeline Examples".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    examples = [
        # Simple Sequential
        ("SIMPLE", example_1_two_layer),
        ("SIMPLE", example_2_three_layer),
        ("SIMPLE", example_3_four_layer),
        ("SIMPLE", example_4_five_layer),

        # Complex Sequential
        ("COMPLEX", example_5_seven_layer_branching),
        ("COMPLEX", example_6_eight_layer_cascade),
        ("COMPLEX", example_7_ten_layer_full_cycle),
    ]

    for category, example in examples:
        try:
            if category == "COMPLEX":
                print("\n" + "▼" * 70)
                print("  ENTERING COMPLEX SEQUENTIAL TERRITORY")
                print("▼" * 70 + "\n")

            example()
        except Exception as e:
            print(f"✗ Example failed: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("\n")
    print("=" * 70)
    print("✅ ALL SEQUENTIAL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\n📊 Summary:")
    print("\n  Simple Sequential Examples (4):")
    print("    1. Two-layer:   audit → fix")
    print("    2. Three-layer: audit → analyze → fix")
    print("    3. Four-layer:  audit → analyze → fix → verify")
    print("    4. Five-layer:  audit → analyze → fix → verify → review")
    print("\n  Complex Sequential Examples (3):")
    print("    5. Seven-layer:  branching pipeline with risk routing")
    print("    6. Eight-layer:  cascade of specialist agents")
    print("    7. Ten-layer:    complete SDLC pipeline")
    print("\n🎓 Sequential Patterns Demonstrated:")
    print("    ✓ Linear pipelines (2-5 layers)")
    print("    ✓ Branching decisions (conditional routing)")
    print("    ✓ Specialist cascades (progressive refinement)")
    print("    ✓ Complete workflows (full development cycle)")
    print("    ✓ Context enrichment (each layer adds value)")
    print("    ✓ Quality gates (verification at each stage)")
    print("\n🔄 Layer Composition Patterns:")
    print("    Detection → Analysis → Action → Verification → Review")
    print("    Scan → Assess → Decide → Process → Integrate → Validate")
    print("    Requirements → Design → Implement → Test → Optimize → Release")
    print("\n💡 Key Insights:")
    print("    • More layers = more specialization = higher quality")
    print("    • Each layer should have clear responsibility")
    print("    • Context flows downward, enriching each stage")
    print("    • Verification layers ensure quality")
    print("    • Branching enables adaptive processing")
    print("\n" + "=" * 70)
    print()


if __name__ == "__main__":
    main()
