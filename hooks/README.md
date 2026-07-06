# Hooks — token-optimizer + auto-backup

These are Claude Code [hooks](https://docs.claude.com/en/docs/claude-code/hooks): small scripts
the Claude Code harness runs automatically around tool calls. Two are included here:

| File | Fires on | What it does |
|---|---|---|
| `trim-bash-output.js` | `PreToolUse` for `Bash` | Rewrites a handful of exact, bare git commands (`git status`, `git diff`, `git log`, `git show`, `git branch`) to strip ANSI color / disable the pager before they run, so their output doesn't waste tokens in the transcript. Tracks the real bytes saved in a ledger file. |
| `archive-backup.ps1` | `PreToolUse` for `Edit`\|`Write`\|`NotebookEdit` | Copies the on-disk file to a timestamped archive **before** Claude edits it. This is what makes the "backup before edit" step in [`/rigorous-build`](../skills/rigorous-build/SKILL.md) actually enforced instead of just advisory. |

## Why `PreToolUse`, not `PostToolUse`

The Claude Code hook API only lets a hook rewrite tool input on `PreToolUse` (via
`updatedInput`) — a `PostToolUse` hook can react to a result but **cannot** shrink output
that's already been captured. So the only way to cut token spend on noisy commands is to
intercept and rewrite them *before* they run, which is what `trim-bash-output.js` does. Every
rewrite is exact-match and lossless — it never touches a command with extra flags, pipes,
redirects, or chaining, so anything you typed on purpose runs untouched.

## Setup

1. Copy the scripts somewhere permanent, e.g. `~/.claude/hooks/`:

   ```
   mkdir -p ~/.claude/hooks
   cp trim-bash-output.js ~/.claude/hooks/
   cp archive-backup.ps1  ~/.claude/hooks/
   ```

2. Open (or create) `~/.claude/settings.json` and add the `hooks` block from
   [`settings.snippet.json`](settings.snippet.json) in this folder — merge it into your
   existing `hooks` key if you already have one (don't overwrite the whole file).

3. **Update the paths** in the snippet to match wherever you put the scripts in step 1 — they
   must be absolute paths.

4. Restart Claude Code (or start a new session) so it picks up the settings change.

That's it — no npm install, no build step. `trim-bash-output.js` only needs Node (bundled with
Claude Code's runtime requirements); `archive-backup.ps1` needs PowerShell, so it's Windows-only
as written. On macOS/Linux you'd port the same logic to a POSIX shell or Node script — the
JSON-in-on-stdin / JSON-out-on-stdout contract is identical, only the file-copy command changes.

## Verifying it worked

- Run `git status` in a Bash tool call inside Claude Code. If the hook is wired up, check
  `~/.claude/bash-savings.json` afterward — it should now have an entry under `commands["git status"]`
  with `saved_bytes > 0`.
- Edit any existing file with Claude Code, then check `~/.claude/_archive/` (Windows) — you
  should find a timestamped copy of the file as it was right before the edit.

## Extending the token-optimizer

`trim-bash-output.js` is intentionally narrow — it only rewrites an *exact* bare command
(after trimming whitespace), never something with args attached, so it's safe to extend. To add
another lossless rewrite, add a `"bare command": "rewritten command"` entry to the `REWRITES`
map in the script. Only add a command to `METERED` if the rewrite genuinely changes the byte
count of piped (non-TTY) output — most `--no-color`/`--no-pager` flags are already the default
in a non-TTY context and won't show any measurable savings.
