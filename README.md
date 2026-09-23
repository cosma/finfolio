# FinFolio
Fact-checks for finance content




### Spec Kit 

```bash
specify init project --integration claude --force #use  --force for already existing directory
```

1. Go to the project folder: `cd project`
2. Start Claude in this project directory; spec-kit skills were installed to `.claude/skills`   
3. Start using skills with your coding agent:                                                 
   3.1 `/speckit-constitution` - Establish project principles                                   
   3.2 `/speckit-specify` - Create baseline specification                                       
   3.3 `/speckit-plan` - Create implementation plan                                             
   3.4 `/speckit-tasks` - Generate actionable tasks                                             
   3.5 `/speckit-implement` - Execute implementation                                            
   3.6 `/speckit-converge` - Assess the codebase and append remaining work as tasks 

#### Spec Kit Skills Workflow

These 6 core skills form a **spec-driven development loop**:

**1. `/speckit-constitution`** — Establishes project principles & governance
- Creates `.specify/memory/constitution.md` — your project's non-negotiable rules, principles, and governance
- Source of truth that all downstream artifacts must comply with
- For FinFolio: 7 core principles (accuracy, no financial advice, facts vs. forecasts, transparency, monetization awareness, official APIs, resource discipline)
- Updated rarely (only on major principle changes)

**2. `/speckit-specify`** — Creates baseline feature specification
- Produces `specs/<feature>/spec.md` — **"what are we building?"** document
- Includes feature description, user stories, acceptance criteria, edge cases, non-functional requirements
- Does NOT include implementation details (no tech stack, file names, code structure)
- Validated against constitution principles

**3. `/speckit-plan`** — Designs the implementation architecture
- Produces design artifacts: `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
- Includes architecture, file structure, tech choices, API specs, integration guide
- Checked against constitution constraints (Haiku default, lean dependencies, official APIs only)

**4. `/speckit-tasks`** — Breaks the plan into executable tasks
- Produces `specs/<feature>/tasks.md` — ordered, dependency-aware checklist
- Each task is small enough to implement in one sitting
- Marked with IDs, parallel/sequential flags, dependencies, test-first ordering

**5. `/speckit-implement`** — Executes the tasks
- Reads `tasks.md` and writes the code
- Creates/updates source files, runs tests, marks tasks complete
- Handles project setup (`.gitignore`, env files, dependencies)
- Requires all checklists to pass before starting

**6. `/speckit-converge`** — Fills the gap between plan and reality
- Diffs your actual codebase against spec/plan/tasks
- Finds unbuilt work and appends it back to `tasks.md`
- Detects unexpected code (tech debt, exploration) not in the spec

**The Loop**:
```
constitution (principles, once)
      ↓
   spec (what to build)
      ↓
   plan (how to build it)
      ↓
   tasks (ordered checklist)
      ↓
 implement (write the code)
      ↓
  converge (find gaps)
      └→ (append more tasks if needed)
         └→ implement (finish)
```

Each stage **validates against the previous** (spec checks constitution, plan checks constitution & spec, tasks checks plan, etc.). This prevents drift and ensures FinFolio's constitution principles are enforced throughout development.

**Optional skills that you can use for your specs (improve quality & confidence)**
                                                                                         
- `/speckit-clarify` (optional) - Ask structured questions to de-risk ambiguous areas before planning (run before `/speckit-plan` if used)    
- `/speckit-analyze` (optional) - Cross-artifact consistency & alignment report (after `/speckit-tasks`, before `/speckit-implement`)
- `/speckit-checklist` (optional) - Generate quality checklists to validate requirements completeness, clarity, and consistency (after `/speckit-plan`)