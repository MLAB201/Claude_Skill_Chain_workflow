# Install instructions (for Claude Code)

If a user asks you to "install these skills", "set this up", or similar while this repo is the
working directory, follow the steps below in order. Do not skip the validation steps — this
repo's own `/rigorous-build` skill exists specifically to prevent silent, unverified changes,
so hold yourself to it here.

## 0. Detect the environment first

- Determine the user's home directory and OS (you already know your platform from context).
- Determine whether `~/.claude/settings.json` already exists. If it does, you are **merging**,
  not replacing — read it in full before touching it.

## 1. Install the skills (always)

Copy all eight skill folders into the user's global skills directory:

```
~/.claude/skills/rigorous-build/     <-  skills/rigorous-build/     (SKILL.md + PERSONA-MINER.md)
~/.claude/skills/caveman/            <-  skills/caveman/            (SKILL.md)
~/.claude/skills/rb-explore/         <-  skills/rb-explore/         (SKILL.md)
~/.claude/skills/ui-inspiration/     <-  skills/ui-inspiration/     (SKILL.md)
~/.claude/skills/rb-graphics-builder/ <- skills/rb-graphics-builder/ (SKILL.md)
~/.claude/skills/compactor/          <-  skills/compactor/          (SKILL.md)
~/.claude/skills/counsel-of-5/       <-  skills/counsel-of-5/       (SKILL.md)
~/.claude/skills/rb-interview/       <-  skills/rb-interview/       (SKILL.md)
```

If any folder already exists at the destination, ask the user before overwriting — don't
silently clobber a skill they may have customized.

## 2. Install the token-optimizer hook (always, cross-platform)

Copy `hooks/trim-bash-output.js` to `~/.claude/hooks/trim-bash-output.js`. This one is plain
Node and runs on any OS.

## 3. Install the auto-backup hook (Windows only)

Copy `hooks/archive-backup.ps1` to `~/.claude/hooks/archive-backup.ps1` **only if the user is on
Windows** — it's a PowerShell script and will fail to launch on macOS/Linux (no `powershell.exe`
on PATH). If the user is not on Windows, skip this step and tell them so at the end — don't wire
a hook entry for a script that can't run.

## 4. Wire the hooks into `settings.json` — merge, never overwrite

This is the step most likely to break something if done carelessly, so:

1. **Back up first.** If `~/.claude/settings.json` exists, copy it to
   `~/.claude/settings.json.bak-<yyyymmdd-HHMMSS>` before editing.
2. **Read the existing file** (or start from `{}` if it doesn't exist yet).
3. Ensure `hooks.PreToolUse` is an array (create it if missing).
4. For the `Bash` matcher: check whether a hook entry already invokes `trim-bash-output.js`
   (by path). If not, **append** a new matcher block (don't touch unrelated matcher blocks the
   user already has):
   ```json
   {
     "matcher": "Bash",
     "hooks": [
       {
         "type": "command",
         "command": "node \"<absolute path to trim-bash-output.js on THIS machine>\"",
         "timeout": 5,
         "statusMessage": "Trimming noisy command output"
       }
     ]
   }
   ```
5. **Windows only** — for the `Edit|Write|NotebookEdit` matcher: check whether a hook entry
   already invokes `archive-backup.ps1`. If not, append:
   ```json
   {
     "matcher": "Edit|Write|NotebookEdit",
     "hooks": [
       {
         "type": "command",
         "command": "powershell.exe",
         "args": [
           "-NoProfile",
           "-ExecutionPolicy",
           "Bypass",
           "-File",
           "<absolute path to archive-backup.ps1 on THIS machine>"
         ],
         "timeout": 30,
         "statusMessage": "Backing up file to _archive"
       }
     ]
   }
   ```
   If a matcher block for `Edit|Write|NotebookEdit` (or `Bash`) already exists with *other*
   hooks in it, add your hook to that block's `hooks` array — don't create a duplicate matcher
   block for the same pattern.
6. Use absolute paths matching where you actually copied the files in steps 2–3 — never the
   literal placeholder paths from `hooks/settings.snippet.json`.

## 5. Validate before declaring done

- Parse the written `settings.json` back (e.g. `JSON.parse`/`ConvertFrom-Json`) to confirm it's
  still valid JSON — if it isn't, restore the backup from step 4.1 and report the failure
  instead of leaving broken config in place.
- Run `node --check` on the copied `trim-bash-output.js` to confirm it's intact.
- Confirm all eight skill folders exist at their destination with their `SKILL.md` present.

## 6. Tell the user what happened

Report plainly: which skills were installed, which hooks were wired (and which were skipped and
why, e.g. "skipped archive-backup.ps1 — you're on macOS"), and that they need to **restart
Claude Code** (or start a new session) for the hook changes to take effect. Point them at
`hooks/README.md` if they want to understand what the hooks actually do.
