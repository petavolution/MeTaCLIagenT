#!/usr/bin/env python3
"""
Keyword-Driven Orchestration with Mock CLI and Database Templates

Demonstrates realistic AI coding agent simulation where:
1. Mock CLI generates output with keywords (identified, error, complete, refactor, optimize)
2. Parser detects keywords in output
3. Database/templates used to construct next prompt
4. Orchestrator routes based on keywords
5. Progressive multi-layer refinement

4 Simple Examples:
1. Two-layer: keyword detection → prompt construction
2. Three-layer: multiple keywords → template selection
3. Four-layer: template database lookup → context enrichment
4. Five-layer: cascading prompts from keywords

3 Complex Examples:
5. Seven-layer: full template library with DB
6. Eight-layer: cascading keyword detection
7. Ten-layer: adaptive learning from keyword patterns

Run: python examples/10_keyword_driven_orchestration.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.core import (
    Orchestrator,
    WorkflowContext,
    create_ai_executor,
)
from metacli.testing import (
    RealisticOutputParser,
    KeywordRouter,
    TemplateLibrary,
    ResponseTemplate,
)
from metacli.testing.templates import MatchStrategy


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIMPLE KEYWORD-DRIVEN EXAMPLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_1_keyword_to_prompt():
    """
    Example 1: Basic Keyword Detection → Prompt Construction

    Simple flow: Mock CLI outputs with keyword, next prompt is constructed
    based on detected keyword.

    Flow:
    Layer 1: Mock CLI audit → detects "error" keyword
    Layer 2: Construct prompt "fix errors" → execute

    Keywords: error, complete, identified
    """
    print("=" * 70)
    print("Example 1: Keyword Detection → Prompt Construction")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "keyword-basic",
        "Basic keyword-driven workflow"
    )

    # Setup parser
    parser = RealisticOutputParser()

    # Layer 1: Initial scan
    workflow.add_step(
        "layer1_scan",
        "mock-ai",
        "audit {target} for issues"
    )

    # Decision: Detect keyword and construct next prompt
    def keyword_to_prompt(ctx: WorkflowContext) -> str:
        """Extract keywords and construct next action."""
        last = ctx.get_last_result()

        if not last or not last.parsed_output:
            return "done"

        keywords = last.parsed_output.detected_keywords
        print(f"\n    🔍 Keywords detected: {keywords}")

        # Keyword → Prompt mapping (simulating DB lookup)
        keyword_prompts = {
            'error': 'fix_errors',
            'identified': 'investigate_issues',
            'complete': 'done',
        }

        # Find first matching keyword
        for keyword in keywords:
            if keyword in keyword_prompts:
                next_step = keyword_prompts[keyword]
                print(f"    → Routing to: {next_step} (based on '{keyword}')")
                ctx.set('detected_keyword', keyword)
                return next_step

        return "done"

    workflow.add_decision("detect_keyword", keyword_to_prompt)

    # Layer 2a: Fix errors
    workflow.add_step(
        "fix_errors",
        "mock-ai",
        "fix errors in {target}"
    )

    # Layer 2b: Investigate
    workflow.add_step(
        "investigate_issues",
        "mock-ai",
        "investigate issues in {target}"
    )

    # Done
    workflow.add_step(
        "done",
        "mock-ai",
        "all clear for {target}"
    )

    print("\n  Workflow Pattern:")
    print("    Layer 1: scan → detect keywords")
    print("    Decision: keywords → database lookup → construct prompt")
    print("    Layer 2: execute with constructed prompt")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"\n  Results:")
    print(f"    Detected keyword: {context.get('detected_keyword')}")
    print(f"    Layers executed: {len(context.results)}")
    print(f"    Execution path: {' → '.join(context.results.keys())}")

    print("\n✓ Example 1 complete\n")


def example_2_template_selection():
    """
    Example 2: Multiple Keywords → Template Selection

    More sophisticated: Multiple keywords detected, template library
    used to select best matching prompt template.

    Flow:
    Layer 1: audit → detects multiple keywords
    Layer 2: Template library selects best match → construct specific prompt
    Layer 3: Execute with context-rich prompt

    Keywords: identified, refactor, optimize
    """
    print("=" * 70)
    print("Example 2: Multiple Keywords → Template Selection")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "template-selection",
        "Template-driven keyword routing"
    )

    # Setup template library (simulating DB)
    template_lib = TemplateLibrary()

    # Add templates for different keyword combinations
    template_lib.add_template(ResponseTemplate(
        name="identified_issues",
        pattern="identified",
        response="load context about identified issues",
        strategy=MatchStrategy.CONTAINS,
        priority=10
    ))

    template_lib.add_template(ResponseTemplate(
        name="needs_refactor",
        pattern="refactor",
        response="create refactoring plan",
        strategy=MatchStrategy.CONTAINS,
        priority=8
    ))

    template_lib.add_template(ResponseTemplate(
        name="can_optimize",
        pattern="optimize",
        response="apply performance optimizations",
        strategy=MatchStrategy.CONTAINS,
        priority=6
    ))

    # Layer 1: Initial analysis
    workflow.add_step(
        "layer1_analyze",
        "mock-ai",
        "comprehensive analysis of {target}"
    )

    # Decision: Use template library
    def template_select(ctx: WorkflowContext) -> str:
        """Select template based on keywords."""
        last = ctx.get_last_result()

        if not last or not last.parsed_output:
            return "done"

        decoded_text = last.parsed_output.decoded_text
        keywords = last.parsed_output.detected_keywords

        print(f"\n    🔍 Keywords: {keywords}")
        print(f"    📚 Searching template library...")

        # Find matching templates (iterate over all categories)
        matching = []
        for category, templates in template_lib.templates.items():
            for template in templates:
                if template.pattern.lower() in decoded_text.lower():
                    matching.append(template)

        if matching:
            # Sort by priority
            best = sorted(matching, key=lambda t: t.priority, reverse=True)[0]
            print(f"    ✓ Best match: {best.name} (priority {best.priority})")
            print(f"    → Action: {best.response}")

            ctx.set('template_used', best.name)
            ctx.set('next_prompt', best.response)

            return "execute_template"

        return "done"

    workflow.add_decision("select_template", template_select)

    # Layer 2: Execute template-based action
    workflow.add_step(
        "execute_template",
        "mock-ai",
        "{next_prompt} for {target}"
    )

    # Layer 3: Verify
    workflow.add_step(
        "verify",
        "mock-ai",
        "verify completion for {target}"
    )

    # Done
    workflow.add_step(
        "done",
        "mock-ai",
        "workflow complete for {target}"
    )

    print("\n  Workflow Pattern:")
    print("    Layer 1: analyze → detect keywords")
    print("    Decision: match keywords → template library")
    print("    Layer 2: execute template-based prompt")
    print("    Layer 3: verify")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/core.py"})

    print(f"\n  Results:")
    print(f"    Template used: {context.get('template_used')}")
    print(f"    Next prompt: {context.get('next_prompt')}")
    print(f"    Execution path: {' → '.join(context.results.keys())}")

    print("\n✓ Example 2 complete\n")


def example_3_database_lookup():
    """
    Example 3: Template Database Lookup with Context Enrichment

    Simulates full database-backed template system where keywords trigger
    database lookup, and results enrich context for downstream layers.

    Flow:
    Layer 1: scan → keywords
    Layer 2: DB lookup → get template → enrich context
    Layer 3: Execute with enriched context
    Layer 4: Verify with context awareness

    Keywords: identified, error, complete
    """
    print("=" * 70)
    print("Example 3: Database Template Lookup + Context Enrichment")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "db-lookup",
        "Database-backed template workflow"
    )

    # Simulate database of templates
    template_database = {
        'identified_security': {
            'keywords': ['identified', 'error'],
            'prompt': 'perform security audit on {target}',
            'context': {'priority': 'high', 'category': 'security'},
            'next_steps': ['fix_security', 'verify_fix']
        },
        'identified_performance': {
            'keywords': ['identified', 'optimize'],
            'prompt': 'analyze performance of {target}',
            'context': {'priority': 'medium', 'category': 'performance'},
            'next_steps': ['optimize', 'benchmark']
        },
        'complete_simple': {
            'keywords': ['complete'],
            'prompt': 'finalize {target}',
            'context': {'priority': 'low', 'category': 'finalization'},
            'next_steps': ['done']
        }
    }

    # Layer 1: Initial scan
    workflow.add_step(
        "layer1_scan",
        "mock-ai",
        "deep scan of {target}"
    )

    # Decision: Database lookup
    def database_lookup(ctx: WorkflowContext) -> str:
        """Look up template in database based on keywords."""
        last = ctx.get_last_result()

        if not last or not last.parsed_output:
            return "done"

        keywords = last.parsed_output.detected_keywords
        print(f"\n    🔍 Keywords: {keywords}")
        print(f"    💾 Querying template database...")

        # Find best matching template
        best_match = None
        best_score = 0

        for template_name, template_data in template_database.items():
            # Calculate match score
            template_keywords = set(template_data['keywords'])
            overlap = keywords & template_keywords
            score = len(overlap)

            if score > best_score:
                best_score = score
                best_match = (template_name, template_data)

        if best_match:
            name, data = best_match
            print(f"    ✓ Match found: {name} (score: {best_score})")
            print(f"    → Prompt: {data['prompt']}")
            print(f"    → Context: {data['context']}")

            # Enrich context
            ctx.set('template_name', name)
            ctx.set('priority', data['context']['priority'])
            ctx.set('category', data['context']['category'])
            ctx.set('action_prompt', data['prompt'])
            ctx.set('next_steps', data['next_steps'])

            return "execute_action"

        return "done"

    workflow.add_decision("db_lookup", database_lookup)

    # Layer 2: Execute action from DB
    workflow.add_step(
        "execute_action",
        "mock-ai",
        "{action_prompt}"
    )

    # Layer 3: Context-aware follow-up
    workflow.add_step(
        "followup",
        "mock-ai",
        "followup on {category} changes to {target} (priority: {priority})"
    )

    # Layer 4: Verify with context
    workflow.add_step(
        "verify",
        "mock-ai",
        "verify {category} improvements to {target}"
    )

    # Done
    workflow.add_step(
        "done",
        "mock-ai",
        "complete"
    )

    print("\n  Workflow Pattern:")
    print("    Layer 1: scan → detect keywords")
    print("    Decision: keywords → database query → match template")
    print("    Layer 2: execute DB-provided prompt")
    print("    Layer 3: context-aware follow-up")
    print("    Layer 4: context-aware verification")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/auth.py"})

    print(f"\n  Results:")
    print(f"    Template: {context.get('template_name')}")
    print(f"    Category: {context.get('category')}")
    print(f"    Priority: {context.get('priority')}")
    print(f"    Execution path: {' → '.join(context.results.keys())}")

    print("\n✓ Example 3 complete\n")


def example_4_cascading_prompts():
    """
    Example 4: Cascading Prompt Construction from Keywords

    Each layer's keywords inform the next layer's prompt construction.
    Demonstrates progressive refinement through keyword cascading.

    Flow:
    L1: scan → keywords1
    L2: analyze(keywords1) → keywords2
    L3: refactor(keywords1+keywords2) → keywords3
    L4: verify(keywords1+keywords2+keywords3) → keywords4
    L5: finalize(all_keywords)

    Keywords accumulate and enrich prompts at each layer.
    """
    print("=" * 70)
    print("Example 4: Cascading Prompt Construction")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "cascading-prompts",
        "Keyword cascade workflow"
    )

    # Track keywords across layers
    print("\n  Keyword Cascade Pattern:")
    print("    Each layer's keywords inform next layer's prompt")
    print("    Progressive context enrichment")

    # Layer 1: Initial scan
    workflow.add_step(
        "layer1_scan",
        "mock-ai",
        "initial scan of {target}"
    )

    # Cascade 1→2
    def cascade_to_layer2(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if not last or not last.parsed_output:
            return "done"

        keywords = list(last.parsed_output.detected_keywords)
        print(f"\n    Layer 1 keywords: {keywords}")

        # Store for cascade
        ctx.set('layer1_keywords', keywords)

        # Construct prompt based on keywords
        if 'identified' in keywords or 'error' in keywords:
            return "layer2_analyze"
        return "done"

    workflow.add_decision("cascade_1_to_2", cascade_to_layer2)

    # Layer 2: Analyze with L1 context
    workflow.add_step(
        "layer2_analyze",
        "mock-ai",
        "analyze issues: {layer1_keywords} in {target}"
    )

    # Cascade 2→3
    def cascade_to_layer3(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if not last or not last.parsed_output:
            return "done"

        keywords = list(last.parsed_output.detected_keywords)
        print(f"    Layer 2 keywords: {keywords}")

        # Merge with layer 1
        layer1_kw = ctx.get('layer1_keywords', [])
        all_keywords = list(set(layer1_kw + keywords))
        ctx.set('layer2_keywords', keywords)
        ctx.set('cascaded_keywords', all_keywords)

        print(f"    Cascaded keywords: {all_keywords}")

        return "layer3_refactor"

    workflow.add_decision("cascade_2_to_3", cascade_to_layer3)

    # Layer 3: Refactor with L1+L2 context
    workflow.add_step(
        "layer3_refactor",
        "mock-ai",
        "refactor {target} addressing: {cascaded_keywords}"
    )

    # Cascade 3→4
    def cascade_to_layer4(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if not last or not last.parsed_output:
            return "done"

        keywords = list(last.parsed_output.detected_keywords)
        print(f"    Layer 3 keywords: {keywords}")

        # Merge all layers
        all_kw = ctx.get('cascaded_keywords', []) + keywords
        ctx.set('all_keywords', list(set(all_kw)))

        return "layer4_verify"

    workflow.add_decision("cascade_3_to_4", cascade_to_layer4)

    # Layer 4: Verify with full context
    workflow.add_step(
        "layer4_verify",
        "mock-ai",
        "verify all aspects: {all_keywords} for {target}"
    )

    # Layer 5: Finalize
    workflow.add_step(
        "layer5_finalize",
        "mock-ai",
        "finalize changes to {target}"
    )

    # Done
    workflow.add_step(
        "done",
        "mock-ai",
        "complete"
    )

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/payment.py"})

    print(f"\n  Cascade Results:")
    print(f"    Layer 1 keywords: {context.get('layer1_keywords')}")
    print(f"    Layer 2 keywords: {context.get('layer2_keywords')}")
    print(f"    All cascaded: {context.get('all_keywords')}")
    print(f"    Total layers: {len(context.results)}")

    print("\n✓ Example 4 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPLEX KEYWORD-DRIVEN EXAMPLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_5_full_template_library():
    """
    Example 5: Seven-Layer with Complete Template Library

    Sophisticated: Full template library loaded from "database",
    each layer queries library based on previous keywords.

    Flow:
    L1: scan → keywords
    L2: query_templates(keywords) → best_template → execute
    L3: query_templates(new_keywords) → next_template → execute
    ... continues for 7 layers

    All prompts come from template database, no hardcoding.
    """
    print("=" * 70)
    print("Example 5: Seven-Layer with Complete Template Library")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "full-template-lib",
        "Complete database-backed workflow"
    )

    # Comprehensive template library (simulating full DB)
    template_library = TemplateLibrary()

    templates = [
        ("scan_security", "error|vulnerability", "deep security audit of {target}", 100),
        ("scan_performance", "optimize|slow", "performance analysis of {target}", 90),
        ("load_context", "identified", "load context about issues in {target}", 80),
        ("create_plan", "refactor", "create refactoring plan for {target}", 70),
        ("execute_fixes", "complete", "apply fixes to {target}", 60),
        ("run_tests", "refactor|optimize", "run test suite for {target}", 50),
        ("verify_quality", "complete", "quality verification of {target}", 40),
    ]

    for name, pattern, response, priority in templates:
        template_library.add_template(ResponseTemplate(
            name=name,
            pattern=pattern,
            response=response,
            strategy=MatchStrategy.REGEX,
            priority=priority
        ))

    print(f"\n  Template Library: {len(templates)} templates loaded")
    print("  Each layer queries library based on keywords\n")

    # Build dynamic workflow
    for layer_num in range(1, 8):
        if layer_num == 1:
            # First layer: scan
            workflow.add_step(
                f"layer{layer_num}",
                "mock-ai",
                "comprehensive scan of {target}"
            )
        else:
            # Subsequent layers: template-driven
            workflow.add_step(
                f"layer{layer_num}",
                "mock-ai",
                "{prompt_layer" + str(layer_num) + "}"
            )

        # Decision after each layer (except last)
        if layer_num < 7:
            def make_decision(layer=layer_num):
                def query_template(ctx: WorkflowContext) -> str:
                    last = ctx.get_last_result()
                    if not last or not last.parsed_output:
                        return "done"

                    text = last.parsed_output.decoded_text
                    keywords = last.parsed_output.detected_keywords

                    print(f"    Layer {layer} keywords: {keywords}")

                    # Query template library (iterate over all categories)
                    matches = []
                    for category, templates in template_library.templates.items():
                        for template in templates:
                            if template.matches(text):
                                matches.append(template)

                    if matches:
                        best = sorted(matches, key=lambda t: t.priority, reverse=True)[0]
                        next_layer = layer + 1
                        prompt_key = f"prompt_layer{next_layer}"

                        print(f"      → Template: {best.name}")
                        print(f"      → Next: {best.response}")

                        ctx.set(prompt_key, best.response)
                        return f"layer{next_layer}"

                    return "done"
                return query_template

            workflow.add_decision(f"query_{layer_num}", make_decision(layer_num))

    workflow.add_step("done", "mock-ai", "workflow complete")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"\n  Results:")
    print(f"    Layers executed: {len(context.results) - 1}")  # -1 for done
    print(f"    All prompts from template library: ✓")
    print(f"    Dynamic routing based on keywords: ✓")

    print("\n✓ Example 5 complete\n")


def example_6_cascading_keyword_detection():
    """
    Example 6: Eight-Layer Cascading Keyword Detection

    Advanced: Each layer not only uses previous keywords but also
    learns which keyword combinations lead to better outcomes.

    Flow:
    L1: detect keywords → track
    L2: analyze keyword patterns → predict best path
    L3: execute based on prediction → measure outcome
    L4-8: Continue with adaptive keyword-based routing

    Demonstrates learning from keyword patterns.
    """
    print("=" * 70)
    print("Example 6: Eight-Layer Cascading Keyword Detection")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "cascading-keywords",
        "Adaptive keyword cascade"
    )

    print("\n  Keyword Pattern Learning:")
    print("    Track keyword combinations")
    print("    Predict best paths")
    print("    Adapt routing dynamically\n")

    # Keyword pattern tracking
    keyword_history = []

    # Layer 1: Initial detection
    workflow.add_step(
        "layer1_detect",
        "mock-ai",
        "initial detection on {target}"
    )

    # Build layers 2-8 with keyword tracking
    for layer_num in range(2, 9):
        # Decision before layer
        def make_adaptive_decision(layer=layer_num):
            def adaptive_route(ctx: WorkflowContext) -> str:
                last = ctx.get_last_result()
                if not last or not last.parsed_output:
                    return "done"

                keywords = last.parsed_output.detected_keywords
                keyword_history.append((layer - 1, keywords))

                print(f"    Layer {layer-1} keywords: {keywords}")

                # Analyze keyword patterns
                if layer > 2:
                    recent_keywords = [kw for _, kws in keyword_history[-3:] for kw in kws]
                    keyword_freq = {}
                    for kw in recent_keywords:
                        keyword_freq[kw] = keyword_freq.get(kw, 0) + 1

                    most_common = max(keyword_freq.items(), key=lambda x: x[1])[0] if keyword_freq else None
                    print(f"      Pattern: '{most_common}' appearing frequently")

                    ctx.set(f'pattern_layer{layer}', most_common)

                # Construct adaptive prompt
                if 'error' in keywords:
                    prompt = f"emergency fix for layer {layer-1} errors in {{target}}"
                elif 'identified' in keywords:
                    prompt = f"detailed analysis for layer {layer-1} issues in {{target}}"
                elif 'refactor' in keywords:
                    prompt = f"refactoring based on layer {layer-1} findings for {{target}}"
                else:
                    prompt = f"continue processing {{target}} at layer {layer}"

                ctx.set(f'prompt_layer{layer}', prompt)
                return f"layer{layer}"

            return adaptive_route

        workflow.add_decision(f"adaptive_{layer_num-1}", make_adaptive_decision(layer_num))

        # Add layer
        workflow.add_step(
            f"layer{layer_num}",
            "mock-ai",
            "{prompt_layer" + str(layer_num) + "}"
        )

    workflow.add_step("done", "mock-ai", "cascade complete")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/core/"})

    print(f"\n  Cascade Results:")
    print(f"    Total layers: {len(context.results) - 1}")
    print(f"    Keyword patterns tracked: {len(keyword_history)}")
    print(f"\n    Keyword History:")
    for layer, keywords in keyword_history[:5]:  # Show first 5
        print(f"      Layer {layer}: {keywords}")

    print("\n✓ Example 6 complete\n")


def example_7_adaptive_meta_learning():
    """
    Example 7: Ten-Layer Adaptive Meta-Learning

    Most sophisticated: System learns which keyword patterns lead to
    successful outcomes and adapts routing strategy in real-time.

    Flow:
    L1-3: Initial scan, detect, analyze
    L4-6: Apply changes with keyword-based routing
    L7-8: Verify and measure success
    L9: Meta-analyze keyword→outcome patterns
    L10: Update routing strategy for future runs

    Demonstrates meta-learning from keyword patterns.
    """
    print("=" * 70)
    print("Example 7: Ten-Layer Adaptive Meta-Learning")
    print("=" * 70)
    print("\n  🧠 Meta-Learning from Keyword Patterns")

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "meta-learning",
        "Adaptive learning workflow"
    )

    # Learning database (tracks keyword→outcome)
    learning_db = {
        'keyword_success_rates': {},
        'pattern_outcomes': [],
        'routing_adjustments': []
    }

    print("  Tracking:")
    print("    • Keyword → Success correlation")
    print("    • Pattern effectiveness")
    print("    • Routing adaptations\n")

    # Phase 1: Detection (L1-3)
    layers_phase1 = [
        ("layer1_scan", "deep scan of {target}"),
        ("layer2_detect", "detect patterns in {target}"),
        ("layer3_analyze", "analyze findings for {target}"),
    ]

    for name, prompt in layers_phase1:
        workflow.add_step(name, "mock-ai", prompt)

    # Phase 2: Action (L4-6) with adaptive routing
    for layer_num in range(4, 7):
        def make_learned_decision(layer=layer_num):
            def learned_route(ctx: WorkflowContext) -> str:
                last = ctx.get_last_result()
                if not last or not last.parsed_output:
                    return "done"

                keywords = last.parsed_output.detected_keywords
                print(f"    Layer {layer-1} keywords: {keywords}")

                # Update learning DB
                for kw in keywords:
                    if kw not in learning_db['keyword_success_rates']:
                        learning_db['keyword_success_rates'][kw] = {'count': 0, 'success': 0}
                    learning_db['keyword_success_rates'][kw]['count'] += 1

                # Adaptive routing based on learned patterns
                best_keyword = None
                best_success_rate = 0

                for kw in keywords:
                    if kw in learning_db['keyword_success_rates']:
                        stats = learning_db['keyword_success_rates'][kw]
                        rate = stats['success'] / stats['count'] if stats['count'] > 0 else 0.5
                        if rate > best_success_rate:
                            best_success_rate = rate
                            best_keyword = kw

                print(f"      Learning: Best keyword '{best_keyword}' (rate: {best_success_rate:.2f})")

                ctx.set(f'best_keyword_layer{layer}', best_keyword)
                ctx.set(f'prompt_layer{layer}', f"action based on '{best_keyword}' for {{target}}")

                return f"layer{layer}"

            return learned_route

        workflow.add_decision(f"learned_{layer_num-1}", make_learned_decision(layer_num))

        workflow.add_step(
            f"layer{layer_num}",
            "mock-ai",
            "{prompt_layer" + str(layer_num) + "}"
        )

    # Phase 3: Verification (L7-8)
    workflow.add_step("layer7_verify", "mock-ai", "verify all changes to {target}")
    workflow.add_step("layer8_measure", "mock-ai", "measure success metrics for {target}")

    # Phase 4: Meta-Learning (L9-10)
    workflow.add_step("layer9_meta", "mock-ai", "meta-analyze keyword patterns")

    # Final: Update learning DB
    def meta_learning_update(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if last and last.success:
            print("\n    🎓 Meta-Learning Update:")

            # Mark successful keywords
            for layer_num in range(4, 7):
                kw = ctx.get(f'best_keyword_layer{layer_num}')
                if kw and kw in learning_db['keyword_success_rates']:
                    learning_db['keyword_success_rates'][kw]['success'] += 1
                    print(f"      ✓ Keyword '{kw}' marked successful")

            # Store pattern
            learning_db['pattern_outcomes'].append({
                'success': True,
                'keywords_used': [ctx.get(f'best_keyword_layer{i}') for i in range(4, 7)]
            })

            print(f"      Total patterns learned: {len(learning_db['pattern_outcomes'])}")

        return "layer10_finalize"

    workflow.add_decision("meta_learn", meta_learning_update)

    workflow.add_step("layer10_finalize", "mock-ai", "finalize with learned insights")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/"})

    print(f"\n  Meta-Learning Results:")
    print(f"    Layers executed: {len(context.results)}")
    print(f"    Keywords tracked: {len(learning_db['keyword_success_rates'])}")
    print(f"\n    Learning Database:")
    for kw, stats in list(learning_db['keyword_success_rates'].items())[:3]:
        rate = stats['success'] / stats['count'] if stats['count'] > 0 else 0
        print(f"      '{kw}': {stats['count']} uses, {rate:.0%} success")

    print(f"\n    Patterns learned: {len(learning_db['pattern_outcomes'])}")
    print(f"    Future runs will use this learned knowledge!")

    print("\n✓ Example 7 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    """Run all keyword-driven examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Keyword-Driven Orchestration with Mock CLI".center(68) + "║")
    print("║" + "  Database Template & Adaptive Learning".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    examples = [
        # Simple
        ("SIMPLE", example_1_keyword_to_prompt),
        ("SIMPLE", example_2_template_selection),
        ("SIMPLE", example_3_database_lookup),
        ("SIMPLE", example_4_cascading_prompts),

        # Complex
        ("COMPLEX", example_5_full_template_library),
        ("COMPLEX", example_6_cascading_keyword_detection),
        ("COMPLEX", example_7_adaptive_meta_learning),
    ]

    for category, example in examples:
        try:
            if category == "COMPLEX":
                print("\n" + "▼" * 70)
                print("  ENTERING COMPLEX KEYWORD-DRIVEN TERRITORY")
                print("▼" * 70 + "\n")

            example()
        except Exception as e:
            print(f"✗ Example failed: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("\n")
    print("=" * 70)
    print("✅ ALL KEYWORD-DRIVEN EXAMPLES COMPLETED")
    print("=" * 70)
    print("\n📊 Summary:")
    print("\n  Simple Keyword-Driven (4):")
    print("    1. Keyword detection → prompt construction")
    print("    2. Multiple keywords → template selection")
    print("    3. Database lookup → context enrichment")
    print("    4. Cascading prompts from keywords")
    print("\n  Complex Keyword-Driven (3):")
    print("    5. Seven-layer with full template library")
    print("    6. Eight-layer cascading keyword detection")
    print("    7. Ten-layer adaptive meta-learning")
    print("\n🎓 Key Concepts Demonstrated:")
    print("    ✓ Mock CLI generates realistic output with keywords")
    print("    ✓ Parser detects keywords (identified, error, complete, refactor, optimize)")
    print("    ✓ Database/template lookup based on keywords")
    print("    ✓ Dynamic prompt construction")
    print("    ✓ Context enrichment through layers")
    print("    ✓ Keyword pattern learning")
    print("    ✓ Adaptive routing based on success rates")
    print("\n🔄 Integration Points:")
    print("    Mock CLI → Parser → Keyword Detection → Template DB →")
    print("    Prompt Construction → Next Layer Execution → Repeat")
    print("\n💾 Database Simulation:")
    print("    • Template library (pattern → response mapping)")
    print("    • Keyword success tracking")
    print("    • Pattern outcome history")
    print("    • Routing strategy adaptation")
    print("\n🧠 Learning Patterns:")
    print("    • Keyword frequency analysis")
    print("    • Success rate tracking")
    print("    • Pattern effectiveness measurement")
    print("    • Real-time routing adaptation")
    print("\n" + "=" * 70)
    print()


if __name__ == "__main__":
    main()
