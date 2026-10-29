# Vendored third-party Claude Code resources

Copied into the repo so cloud Claude Code sessions (which load the committed `.claude/`, not the local
user-scope plugins) have them. All MIT; the original notices are in this directory.

| Path | Source | Version | Changes |
|---|---|---|---|
| `.claude/skills/diataxis-*` (7) | `github.com/hrsandrabi/diataxis` (plugin `diataxis`) | 1.0.1 @ `0907a2a7` | dirs + `name:` prefixed `diataxis-`; `diataxis:<x>` refs → `diataxis-<x>`; survey plan template no longer names the non-existent `diataxis:subagent-driven-development` / `diataxis:executing-plans` <!-- docs-check: allow (upstream plugin name, not a symbol defined in this repo) --> |
| `.claude/skills/review-docs`, `.claude/skills/write-project-docs` | `github.com/naokami3/ai_dotfiles#plugins/doc-authoring-skills` | 2.1.0 @ `9c66c1ee` | `check-doc-links.py` reformatted by the repo's black pre-commit hook (no logic change) |
| `.claude/agents/tutorial-engineer.md` | `github.com/wshobson/agents` (plugin `code-documentation`) | 1.2.1 | `name:` `code-documentation-tutorial-engineer` → `tutorial-engineer` |

To refresh: re-copy from the plugin cache (`~/.claude/plugins/cache/...`) and re-apply the changes above.
