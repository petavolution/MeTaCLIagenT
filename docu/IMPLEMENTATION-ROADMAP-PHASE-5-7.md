# Implementation Roadmap - Phases 5-7

**Status**: Active Development
**Current Phase**: Phase 5 (Integration & Validation)
**Goal**: Complete meta-framework with real-world integration

---

## 🎯 STRATEGIC SEQUENCE

Based on project vision and maximum value delivery:

### **Phase 5: Integration & Validation** 📍 **NEXT**
**Goal**: Prove abstractions work with existing code

### **Phase 6: Template Engine**
**Goal**: Enable conditional automation (core vision feature)

### **Phase 7: Session Manager**
**Goal**: Add state persistence and resume capability

---

## 📋 PHASE 5: INTEGRATION & VALIDATION

**Duration**: 3-4 days
**Priority**: **CRITICAL** - Validates entire approach

### **Objectives**
1. Integrate UniversalOrchestrator with existing CLISequence
2. Migrate pre-built workflows to use new abstractions
3. Test with real AI tools (aider, claude-code, grep, sed)
4. Prove backward compatibility
5. Validate migration path

### **Tasks**

#### 5.1 Create Integration Bridge (Day 1)
**File**: `eats_core/orchestrator_bridge.py`

```python
class OrchestratorBridge:
    """
    Bridge between old CLISequence and new UniversalOrchestrator.

    Allows gradual migration:
    - CLISequence can use UniversalOrchestrator internally
    - Existing code works unchanged
    - New code uses UniversalOrchestrator directly
    """

    @staticmethod
    def cli_sequence_to_tools(sequence: CLISequence) -> List[UniversalTool]:
        """Convert CLISequence steps to UniversalTools."""
        pass

    @staticmethod
    def orchestration_result_to_sequence_result(
        result: OrchestrationResult
    ) -> SequenceResult:
        """Convert OrchestrationResult to CLISequence format."""
        pass
```

#### 5.2 Update CLISequence to Use Orchestrator (Day 1-2)
**File**: `eats_core/cli_orchestrator.py`

Enhancement:
```python
class CLISequence:
    def __init__(self, ...):
        # Add option to use new orchestrator
        self.use_universal_orchestrator = True
        self._orchestrator = UniversalOrchestrator() if use_universal_orchestrator else None

    async def run(self, ...):
        if self._orchestrator:
            # Use new unified execution
            tools = OrchestratorBridge.cli_sequence_to_tools(self)
            result = await self._orchestrator.execute(tools, inputs, ...)
            return OrchestratorBridge.orchestration_result_to_sequence_result(result)
        else:
            # Fallback to old implementation
            return await self._run_legacy(...)
```

#### 5.3 Migrate Pre-Built Workflows (Day 2)
**Files**: `eats_core/workflow_templates.py`, `eats_cli.py`

Migrate these workflows to use UniversalOrchestrator:
- code-review workflow
- code-generate workflow
- explain-code workflow
- refactor workflow
- debug workflow

#### 5.4 Real-World Testing (Day 3)
**Create**: `tests/test_integration.py`

Test scenarios:
```python
# Test 1: Simple POSIX pipeline
grep → sed → awk

# Test 2: AI tool chain
aider → claude-code (review)

# Test 3: Mixed workflow
git diff → claude-code (analyze) → aider (fix)

# Test 4: Parallel AI analysis
parallel(claude-code, gemini, aider) → aggregate

# Test 5: Existing CLI workflow
run existing code-review workflow with new orchestrator
```

#### 5.5 Performance Benchmarking (Day 3)
**Create**: `benchmarks/orchestrator_benchmark.py`

Compare:
- Old CLISequence vs New UniversalOrchestrator (sequential)
- Old ParallelExecutor vs New UniversalOrchestrator (parallel)
- Overhead measurement
- Memory usage

#### 5.6 Migration Guide (Day 4)
**Create**: `docu/MIGRATION-GUIDE.md`

Document:
- How to migrate existing code
- Backward compatibility notes
- New vs old API comparison
- Best practices

### **Success Criteria**
- ✅ All existing workflows work with new orchestrator
- ✅ Performance overhead < 5%
- ✅ Zero breaking changes for existing users
- ✅ Real AI tools execute successfully
- ✅ Migration path documented

### **Deliverables**
1. `orchestrator_bridge.py` - Integration bridge
2. Enhanced `cli_orchestrator.py` - Uses UniversalOrchestrator
3. Migrated workflow templates
4. Integration tests
5. Performance benchmarks
6. Migration guide

---

## 📋 PHASE 6: TEMPLATE ENGINE

**Duration**: 5-6 days
**Priority**: **HIGH** - Core vision feature

### **Objectives**
1. Create template-based conditional automation
2. Enable IF/THEN workflow logic
3. Implement variable substitution
4. Pattern matching for outputs
5. Integration with UniversalOrchestrator

### **Tasks**

#### 6.1 Template Language Design (Day 1)
**File**: `eats_core/templates/template_spec.md`

Define template syntax:
```yaml
# Example template
template:
  name: "code-review-with-fixes"

  variables:
    - CODE_FILE
    - REVIEWER

  steps:
    - tool: "{{REVIEWER}}"
      input: "Review this code: {{CODE_FILE}}"
      match:
        - pattern: "security issue"
          action: trigger_step
          step: fix_security
        - pattern: "looks good"
          action: complete

    - id: fix_security
      tool: aider
      input: "Fix security issues found in: {{previous_output}}"
```

#### 6.2 Template Parser (Day 1-2)
**File**: `eats_core/templates/parser.py`

```python
class TemplateParser:
    """Parse template definitions."""

    def parse_yaml(self, yaml_content: str) -> Template:
        """Parse YAML template."""
        pass

    def validate_template(self, template: Template) -> bool:
        """Validate template structure."""
        pass
```

#### 6.3 Pattern Matcher (Day 2-3)
**File**: `eats_core/templates/matcher.py`

```python
class PatternMatcher:
    """Match patterns in tool outputs."""

    def match(self, output: str, pattern: str) -> MatchResult:
        """Match pattern (regex, keywords, semantic)."""
        pass

    def extract(self, output: str, pattern: str) -> Dict[str, str]:
        """Extract variables from pattern match."""
        pass
```

#### 6.4 Variable Engine (Day 3)
**File**: `eats_core/templates/variables.py`

```python
class VariableEngine:
    """Variable substitution and management."""

    def substitute(self, text: str, variables: Dict[str, str]) -> str:
        """Replace {{VAR}} with values."""
        pass

    def extract_variables(self, text: str) -> List[str]:
        """Find all {{VAR}} in text."""
        pass
```

#### 6.5 Template Executor (Day 4)
**File**: `eats_core/templates/executor.py`

```python
class TemplateExecutor:
    """Execute templates using UniversalOrchestrator."""

    def __init__(self, orchestrator: UniversalOrchestrator):
        self.orchestrator = orchestrator
        self.matcher = PatternMatcher()
        self.variables = VariableEngine()

    async def execute(
        self,
        template: Template,
        initial_vars: Dict[str, str]
    ) -> TemplateResult:
        """Execute template with conditional logic."""
        pass
```

#### 6.6 Integration & Testing (Day 5-6)
**Create**:
- `tests/test_templates.py`
- `examples/template_examples.py`

Test scenarios:
```python
# Conditional workflow
IF security_issues_found THEN fix ELSE approve

# Loop workflow
WHILE tests_failing DO fix_and_test

# Multi-agent coordination
parallel_analyze → IF conflicts THEN resolve ELSE merge
```

### **Success Criteria**
- ✅ Template parser handles YAML/JSON
- ✅ Pattern matching works (regex + keywords)
- ✅ Variable substitution functional
- ✅ Conditional logic executes correctly
- ✅ Integration with UniversalOrchestrator seamless

### **Deliverables**
1. Template specification
2. Template parser
3. Pattern matcher
4. Variable engine
5. Template executor
6. Integration tests
7. Example templates

---

## 📋 PHASE 7: SESSION MANAGER

**Duration**: 4-5 days
**Priority**: **MEDIUM** - Completes the stack

### **Objectives**
1. Track execution state
2. Enable session resume
3. Persist artifacts
4. Compare sessions
5. Replay workflows

### **Tasks**

#### 7.1 Session Data Model (Day 1)
**File**: `eats_core/session/models.py`

```python
@dataclass
class Session:
    """Execution session."""
    id: str
    name: str
    created_at: datetime
    status: SessionStatus
    workflow_name: str
    variables: Dict[str, Any]

    # Results
    orchestration_results: List[OrchestrationResult]
    artifacts: Dict[str, Any]

    # State
    current_step: int
    can_resume: bool
```

#### 7.2 Session Manager (Day 1-2)
**File**: `eats_core/session/manager.py`

```python
class SessionManager:
    """Manage execution sessions."""

    async def create_session(
        self,
        name: str,
        workflow: str,
        variables: Dict[str, str]
    ) -> Session:
        """Create new session."""
        pass

    async def save_session(self, session: Session) -> None:
        """Persist session state."""
        pass

    async def resume_session(self, session_id: str) -> Session:
        """Resume paused session."""
        pass

    async def compare_sessions(
        self,
        session1_id: str,
        session2_id: str
    ) -> SessionComparison:
        """Compare two sessions."""
        pass
```

#### 7.3 Artifact Manager (Day 2-3)
**File**: `eats_core/session/artifacts.py`

```python
class ArtifactManager:
    """Manage session artifacts (CONTEXT.md, PLAN.md, etc.)."""

    def save_artifact(
        self,
        session_id: str,
        name: str,
        content: str
    ) -> None:
        """Save artifact to session."""
        pass

    def load_artifact(
        self,
        session_id: str,
        name: str
    ) -> str:
        """Load artifact from session."""
        pass

    def diff_artifacts(
        self,
        session1_id: str,
        session2_id: str,
        artifact_name: str
    ) -> str:
        """Compare artifact across sessions."""
        pass
```

#### 7.4 Persistence Layer (Day 3)
**File**: `eats_core/session/persistence.py`

```python
class SessionPersistence:
    """Persist sessions to database and filesystem."""

    def __init__(self, db_path: str, archive_path: str):
        self.db = Database(db_path)
        self.archive = FileArchive(archive_path)

    def save(self, session: Session) -> None:
        """Save to DB + files."""
        pass

    def load(self, session_id: str) -> Session:
        """Load from DB + files."""
        pass
```

#### 7.5 Integration (Day 4)
**Update**: `eats_core/universal_orchestrator.py`

```python
class UniversalOrchestrator:
    def __init__(self, session_manager: Optional[SessionManager] = None):
        self.session_manager = session_manager

    async def execute_with_session(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        session_name: str,
        ...
    ) -> OrchestrationResult:
        """Execute and track in session."""
        session = await self.session_manager.create_session(...)
        result = await self.execute(...)
        await self.session_manager.save_session(session)
        return result
```

#### 7.6 Testing & Documentation (Day 5)
**Create**:
- `tests/test_session_manager.py`
- `examples/session_examples.py`
- `docu/SESSION-MANAGEMENT.md`

### **Success Criteria**
- ✅ Sessions persisted to DB + files
- ✅ Resume works correctly
- ✅ Artifacts tracked and diffable
- ✅ Session comparison functional
- ✅ Replay capability

### **Deliverables**
1. Session data models
2. Session manager
3. Artifact manager
4. Persistence layer
5. Integration with orchestrator
6. Tests and documentation

---

## 🎯 OVERALL TIMELINE

| Phase | Duration | Status |
|-------|----------|--------|
| 1-2: Foundation | ✅ Complete | Transport + VisualSwarm |
| 3-4: Core Abstractions | ✅ Complete | UniversalTool + Orchestrator |
| **5: Integration** | **3-4 days** | **← NEXT** |
| 6: Template Engine | 5-6 days | Planned |
| 7: Session Manager | 4-5 days | Planned |
| **TOTAL** | **12-15 days** | **To complete meta-framework** |

---

## 🚀 IMMEDIATE NEXT ACTIONS

### **Starting Phase 5 (Integration) RIGHT NOW:**

1. **Create orchestrator_bridge.py**
   - Bridge old CLISequence to new UniversalOrchestrator
   - Conversion utilities

2. **Update cli_orchestrator.py**
   - Add use_universal_orchestrator flag
   - Implement dual-mode execution

3. **Test with existing workflows**
   - code-review
   - code-generate
   - Prove backward compatibility

4. **Benchmark performance**
   - Measure overhead
   - Compare with legacy

---

## 💡 WHY THIS SEQUENCE IS OPTIMAL

### **Integration First** (Phase 5)
✅ **Risk Mitigation**: Validates abstractions work with real code
✅ **Practical Value**: Existing workflows benefit immediately
✅ **Confidence Building**: Proves migration path viable
✅ **Early Testing**: Catches issues before building on top

### **Templates Second** (Phase 6)
✅ **Core Vision**: Template-based automation is central to project
✅ **High Impact**: Unlocks conditional workflows
✅ **Foundation Ready**: Orchestrator proven and stable
✅ **Playbook Enabler**: Required for declarative workflows

### **Sessions Third** (Phase 7)
✅ **Builds on Success**: Integration + templates working
✅ **Complete Stack**: Adds persistence layer on proven foundation
✅ **Natural Progression**: State management after execution working
✅ **Final Polish**: Completes the meta-framework

---

## 📊 SUCCESS METRICS

### **Phase 5 Success**
- All existing workflows work with new orchestrator
- Zero breaking changes
- Performance overhead < 5%
- Migration guide complete

### **Phase 6 Success**
- Conditional workflows execute correctly
- Template syntax intuitive
- Pattern matching reliable
- Variable substitution robust

### **Phase 7 Success**
- Sessions persist reliably
- Resume works correctly
- Artifacts tracked and diffable
- Comparison useful

---

## 🎉 END STATE

After Phases 5-7 complete:

```
✅ Universal Tool Abstraction (ANY CLI tool)
✅ Universal Orchestrator (ONE execution engine)
✅ Integration (Works with existing code)
✅ Template Engine (Conditional automation)
✅ Session Manager (State + persistence)

= COMPLETE META-FRAMEWORK 🌟
```

Ready for:
- Playbook YAML workflows
- Self-orchestration
- Distributed execution
- Cloud integration
- Production deployment

---

**RECOMMENDATION**: Start Phase 5 (Integration) immediately!

**First file to create**: `eats_core/orchestrator_bridge.py`

Ready to begin? 🚀
