# /decision-lookup

Search the vault KF-Prototype-Decisions.md for a topic; return relevant decision numbers and key constraints.

## Usage
```
/decision-lookup <topic>
```
Examples:
- `/decision-lookup identity`
- `/decision-lookup named graphs`
- `/decision-lookup SSSOM`
- `/decision-lookup apple silicon`

## Steps

1. Open vault file via `--add-dir` access:
   `~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/KF-Prototype-Decisions.md`

2. Search for topic keywords across all decision entries

3. Also check the local decisions-index:
   `.claude/rules/decisions-index.md`

4. Return matching decisions with:
   - Decision number (D1–D21+)
   - One-sentence summary
   - Key constraints relevant to the query topic
   - Any open questions flagged in the decision

## Output Format

```
Topic: "{topic}"

Relevant decisions:

D{n}: {summary}
  Key constraints:
  - {constraint 1}
  - {constraint 2}
  Open questions: {any flagged questions}

D{m}: {summary}
  ...

See full log: ~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/KF-Prototype-Decisions.md
```

## Notes
- Requires vault access: launch with `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ~/Obsidian/obsidian`
- The decisions-index.md provides fast one-line summaries; the vault file has full rationale
- When creating new code that touches an undecided area, flag "new decision needed" and suggest creating a new decision in the vault
