# experiment-loop skill

Portable, agent-agnostic experiment-iteration protocol. `SKILL.md` is the canonical
source; the protocol is plain markdown with no code dependency, so any coding agent can
follow it. Parameters the invoker supplies: `<runner>` (e.g. `uv run python`), `<script>`,
`<metric>`.

## Install

**Claude Code, all projects (personal skill):**

```bash
mkdir -p ~/.claude/skills/experiment-loop
cp SKILL.md ~/.claude/skills/experiment-loop/SKILL.md
```

Invoke with `/experiment-loop` or let the model pick it up from the description.

**Claude Code, one project:** copy the directory to `<repo>/.claude/skills/experiment-loop/`.

**Codex CLI:**

```bash
mkdir -p ~/.codex/prompts
cp SKILL.md ~/.codex/prompts/experiment-loop.md
```

Invoke with `/experiment-loop`. Alternatively paste the protocol into a project's
`AGENTS.md` for always-on behavior. (Verify the prompts path against current Codex docs.)

**Any other agent:** point it at `SKILL.md` in your first message, autoresearch-style:
"Read skills/experiment-loop/SKILL.md and run the loop on <script> with metric <metric>."

## Provenance

Adapted from [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
(`program.md`). Changes based on a controlled before/after evaluation
(`docs/report/2026-07-12-experiment-loop-evaluation.md`):

- Noise guard: replicate-before-keep for improvements inside the measured noise floor
  (the evaluation caught a "keep" of Δ0.008 against a ±0.03 floor).
- `git revert` instead of `git reset --hard`, keeping discarded experiments inspectable.
- Stale-`run.log` removal before each run (a noclobber shell silently no-opped a run).
