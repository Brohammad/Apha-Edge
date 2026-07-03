# Phase 13 GitHub Issues

Run `gh auth login` then create these with:

```bash
gh issue create --title "Phase 13a: Python Strategy Runtime" --body-file - <<'EOF'
See docs/ROADMAP.md Phase 13a. Implemented in current branch.
EOF
```

Or create manually from the titles below.

| Issue | Title | Status |
|-------|-------|--------|
| 13a | Phase 13a: Python Strategy Runtime | Implemented |
| 13b | Phase 13b: DSL Expressiveness | Implemented |
| 13c | Phase 13c: Live Strategy Evaluation | Implemented |
| 13d | Phase 13d: Strategy Authoring UX | Implemented |

After `gh auth login`:

```bash
cd /path/to/alpha-edge
for spec in 13a 13b 13c 13d; do
  gh issue create --title "Phase ${spec}: ..." --body "Ref: docs/ROADMAP.md Phase ${spec}"
done
```
