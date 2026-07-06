#!/usr/bin/env node
/*
 * trim-bash-output.js  —  PreToolUse(Bash) command rewriter for token savings,
 *                         now with a true-savings ledger for `git status`.
 *
 * WHY: A PostToolUse hook CANNOT trim captured output (Claude Code hook API only
 * exposes `updatedInput` on PreToolUse). So the only way to shrink noisy Bash
 * output is to rewrite the command BEFORE it runs. This does that — conservatively.
 *
 * SAFETY CONTRACT (do not weaken):
 *   - Only rewrites a command that EXACTLY matches a key in REWRITES (after trim).
 *     Any extra args, flags, pipes, redirects, or && chains => passed through UNCHANGED.
 *     Rationale: if you were specific, you meant it. We never truncate a diff/log
 *     you might have needed.
 *   - Every rewrite is lossless: it disables ANSI color (pure token waste) and the
 *     pager. The only format change is `git status` -> `git status -sb`, the standard
 *     concise-but-complete status output.
 *   - The savings ledger is BEST-EFFORT and fully sandboxed in try/catch: any failure
 *     (git missing, not a repo, timeout, unwritable ledger) is swallowed and the
 *     rewrite is still emitted. Measurement must NEVER block or alter a command.
 *
 * SAVINGS LEDGER (scoped to `git status` only — see METERED):
 *   Empirically, of the five rewrites only `git status` -> `git status -sb` changes
 *   the byte count in the actual (piped, non-TTY) capture context: git already
 *   suppresses color AND the pager for non-TTY output, so the --no-color/--no-pager
 *   rewrites on diff/log/show/branch save ZERO bytes here (verified 2026-07-05). So
 *   we meter only `git status`, and we measure BOTH forms live each call — the true
 *   "would-have-been" bytes, not a calibrated guess. This captures dirty-tree status
 *   calls (hundreds of bytes saved) accurately instead of flattening them to an average.
 *   Note: `execSync` spawns git as a RAW child process; Claude Code does not intercept
 *   it, so there is no hook re-entrancy loop.
 *
 * LEDGER FILE: ~/.claude/bash-savings.json  (point your usage widget at this)
 *   { since, updated, commands: { "git status": { count, orig_bytes, new_bytes,
 *     saved_bytes } }, total_saved_bytes, total_saved_tokens_est, _note }
 *   saved_bytes is EXACT; *_tokens_est is bytes/~4 (approximate — only the byte->token
 *   conversion is an estimate; the byte deltas are measured).
 *
 * TO EXTEND: add an exact bare command -> replacement below. Keep it lossless. To also
 * meter a command, add its key to METERED (only worth it if the rewrite actually
 * changes bytes in a pipe — most git color/pager rewrites do not).
 * TO DISABLE: remove the hook entry from settings.json (or delete this file).
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execSync } = require("child_process");

const REWRITES = {
  "git status": "git -c color.ui=false status -sb",
  "git diff":   "git --no-pager -c color.ui=false diff",
  "git log":    "git --no-pager -c color.ui=false log",
  "git show":   "git --no-pager -c color.ui=false show",
  "git branch": "git -c color.ui=false branch",
};

// Only these bare commands get their true byte savings measured + logged.
const METERED = new Set(["git status"]);

const LEDGER = path.join(os.homedir(), ".claude", "bash-savings.json");
const APPROX_CHARS_PER_TOKEN = 4; // byte deltas are exact; this ratio is the only estimate
const MEASURE_TIMEOUT_MS = 1000;  // two calls worst-case 2s, well under the hook's 5s budget

// Run a read-only command purely to size its output. Returns byte count (raw Buffer
// length — never pass an encoding, or .length becomes a CHARACTER count). Throws on
// timeout / non-zero exit; the sole caller swallows it.
function measureBytes(cmd, cwd) {
  const out = execSync(cmd, {
    cwd: cwd || process.cwd(),
    timeout: MEASURE_TIMEOUT_MS,
    stdio: ["ignore", "pipe", "ignore"],
    windowsHide: true,
  });
  return out.length;
}

// Best-effort: measure both forms, append the true delta to the ledger. Never throws.
function recordSaving(key, origCmd, newCmd, cwd) {
  try {
    const origBytes = measureBytes(origCmd, cwd);
    const newBytes = measureBytes(newCmd, cwd);
    const saved = Math.max(0, origBytes - newBytes);

    let ledger = {};
    try {
      ledger = JSON.parse(fs.readFileSync(LEDGER, "utf8")) || {};
    } catch (_) {
      /* missing or corrupt -> start fresh */
    }
    if (!ledger.commands || typeof ledger.commands !== "object") ledger.commands = {};

    const now = new Date().toISOString();
    if (!ledger.since) ledger.since = now;
    ledger.updated = now;

    const c = ledger.commands[key] || { count: 0, orig_bytes: 0, new_bytes: 0, saved_bytes: 0 };
    c.count += 1;
    c.orig_bytes += origBytes;
    c.new_bytes += newBytes;
    c.saved_bytes += saved;
    ledger.commands[key] = c;

    let totalSaved = 0;
    for (const k of Object.keys(ledger.commands)) {
      totalSaved += ledger.commands[k].saved_bytes || 0;
    }
    ledger.total_saved_bytes = totalSaved;
    ledger.total_saved_tokens_est = Math.round(totalSaved / APPROX_CHARS_PER_TOKEN);
    ledger._note =
      "saved_bytes is exact; *_tokens_est ~= bytes/" + APPROX_CHARS_PER_TOKEN +
      ". Only `git status` is metered (the only rewrite that changes bytes in piped context).";

    // Atomic write: per-pid temp + rename, so a concurrent reader never sees a
    // half-written file. Concurrent writers may lose an increment (acceptable for a metric).
    const tmp = LEDGER + "." + process.pid + ".tmp";
    fs.writeFileSync(tmp, JSON.stringify(ledger, null, 2));
    fs.renameSync(tmp, LEDGER);
  } catch (_) {
    /* never block on measurement/ledger failure */
  }
}

let raw = "";
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  try {
    const input = JSON.parse(raw || "{}");
    const cmd = input && input.tool_input && input.tool_input.command;
    if (typeof cmd !== "string") return; // nothing to do -> pass through
    const key = cmd.trim();
    const replacement = REWRITES[key];
    if (!replacement) return; // not an exact bare match -> pass through untouched

    // Meter the true byte delta BEFORE emitting the rewrite (git status only).
    if (METERED.has(key)) recordSaving(key, key, replacement, input.cwd);

    const updatedInput = Object.assign({}, input.tool_input, { command: replacement });
    process.stdout.write(
      JSON.stringify({
        suppressOutput: true,
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          updatedInput,
        },
      })
    );
  } catch (_) {
    // On any error, emit nothing -> command runs exactly as written. Never block.
  }
});
