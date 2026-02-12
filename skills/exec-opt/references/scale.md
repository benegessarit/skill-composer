# SCALE

Test extensibility by adding the N+1th instance. Catches over-hardcoding.

## Injection Point
phase-0 — Add before any design involving N instances of something

## When to use
The task needs **extensibility testing** — a design involves N instances of something and you need to verify adding N+1 is easy. Catches over-hardcoding before it calcifies.

Do NOT use when the design has a fixed, known set of instances that won't grow.

## Phases to Add

<phase name="Scale-Enumerate">
  <instruction>Identify what's being multiplied. How many exist now? Invent a realistic N+1th.</instruction>
  <output>
    **The thing:** [What's being repeated/typed/templated]
    **Current N:** [Count]
    **Hypothetical N+1:** [A realistic next instance]
  </output>
</phase>

<phase name="Scale-Trace">
  <instruction>Walk through adding N+1. List every file that changes.</instruction>
  <output>
    **To add N+1 requires:**
    - [File 1]: [what changes]
    - [File 2]: [what changes]
    ...

    **Delta:** [1 file / 2-3 files / 4+ files]
  </output>
</phase>

<phase name="Scale-Verdict">
  <instruction>Judge extensibility. If over-hardcoded, propose the 1-file fix.</instruction>
  <output>
    | Delta | Verdict |
    |-------|---------|
    | 1 file | EXTENSIBLE |
    | 2-3 files | ACCEPTABLE |
    | 4+ files | OVER-HARDCODED |

    **This design:** [Verdict]
    **If over-hardcoded, fix:** [What makes it 1-file?]
  </output>
</phase>

## Constraints
- N+1 must be realistic, not contrived to break the design
- Trace specific file paths, not "some changes"
- OVER-HARDCODED requires proposing a fix
