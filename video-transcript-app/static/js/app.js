// UI for the transcript API. Transcript text comes from third-party platforms,
// so it is only ever inserted with textContent, never innerHTML.
import {
  claudeMessage,
  countMatches,
  extractVideoLink,
  filenameFor,
  formatClock,
  splitMatches,
  timestampUrl,
  toJson,
  toPlainText,
  toSrt,
  toTimestampedText,
  toVtt,
} from "./formats.js";

const $ = (id) => document.getElementById(id);

const els = {
  form: $("lookup-form"),
  url: $("url-input"),
  submit: $("submit-btn"),
  paste: $("paste-btn"),
  sttOption: $("stt-option"),
  stt: $("stt-input"),
  sttLimit: $("stt-limit"),
  status: $("status"),
  error: $("error"),
  errorTitle: $("error-title"),
  errorDetails: $("error-details"),
  result: $("result"),
  thumbLink: $("video-thumb-link"),
  thumb: $("video-thumb"),
  title: $("video-title"),
  meta: $("video-meta"),
  badges: $("video-badges"),
  notes: $("notes"),
  trackField: $("track-field"),
  trackSelect: $("track-select"),
  search: $("search-input"),
  matchCount: $("match-count"),
  timestamps: $("timestamps-input"),
  transcript: $("transcript"),
  copy: $("copy-btn"),
  claude: $("claude-btn"),
  claudeHint: $("claude-hint"),
  stats: $("stats"),
};

const state = {
  result: null,
  lastUrl: "",
  view: "segments",
  query: "",
  busy: false,
};

// ---- preferences (per-browser convenience only; the page works without them)
const PREFS_KEY = "transcript-puller:prefs";
function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
  } catch {
    return {};
  }
}
function savePrefs() {
  try {
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({ view: state.view, timestamps: els.timestamps.checked, stt: els.stt.checked }),
    );
  } catch {
    /* storage unavailable: ignore */
  }
}

// ---- status / errors
let slowTimer = null;
function showStatus(message) {
  els.status.replaceChildren();
  const spinner = document.createElement("span");
  spinner.className = "spinner";
  spinner.setAttribute("aria-hidden", "true");
  const text = document.createElement("span");
  text.textContent = message;
  els.status.append(spinner, text);
  els.status.hidden = false;
}
function hideStatus() {
  els.status.hidden = true;
  clearTimeout(slowTimer);
}
function showError(message, details = []) {
  els.errorTitle.textContent = message;
  els.errorDetails.replaceChildren(
    ...details.filter(Boolean).map((d) => {
      const li = document.createElement("li");
      li.textContent = d;
      return li;
    }),
  );
  els.error.hidden = false;
}
function hideError() {
  els.error.hidden = true;
}

// ---- API
async function fetchTranscript(url, language) {
  const body = { url, speech_to_text: !els.stt.closest("[hidden]") && els.stt.checked };
  if (language) body.language = language;
  let response;
  try {
    response = await fetch("/api/transcript", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw {
      message: "Couldn't reach the server.",
      details: ["Check that the computer running Transcript Puller is on and the app is still running."],
    };
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    /* non-JSON error page */
  }
  if (!response.ok) {
    const err = data?.error;
    throw {
      message: err?.message || `The server returned an error (${response.status}).`,
      details: err?.details || [],
    };
  }
  return data;
}

async function lookup(url, language = null) {
  if (state.busy) return;
  state.busy = true;
  els.submit.disabled = true;
  els.trackSelect.disabled = true;
  hideError();
  showStatus(language ? "Switching captions…" : "Fetching captions…");
  clearTimeout(slowTimer);
  slowTimer = setTimeout(() => {
    showStatus(
      els.stt.checked
        ? "Still working. If this video has no captions, speech-to-text can take a minute or two…"
        : "Still working. Some videos take a little longer…",
    );
  }, 6000);

  try {
    const result = await fetchTranscript(url, language);
    state.result = result;
    state.lastUrl = url;
    renderResult();
    updateAddressBar(url);
  } catch (err) {
    showError(err.message || "Something went wrong.", err.details || []);
    if (!language) {
      els.result.hidden = true;
    } else if (state.result) {
      // Switching tracks failed: keep showing the old transcript and its track.
      els.trackSelect.value = state.result.kind === "speech-to-text" ? "" : state.result.track_code;
    }
  } finally {
    hideStatus();
    state.busy = false;
    els.submit.disabled = false;
    els.trackSelect.disabled = false;
  }
}

function updateAddressBar(url) {
  try {
    // Also drops any ?text=/&title= left over from a share.
    const next = new URL("/", window.location.href);
    next.searchParams.set("url", url);
    window.history.replaceState(null, "", next);
  } catch {
    /* ignore */
  }
}

// ---- rendering
const PLATFORM_NAMES = { youtube: "YouTube", tiktok: "TikTok" };

function languageLabel(result) {
  if (result.kind === "speech-to-text") {
    try {
      const name = new Intl.DisplayNames([navigator.language || "en"], { type: "language" }).of(result.language);
      return `${name} (detected)`;
    } catch {
      return `${result.language} (detected)`;
    }
  }
  return result.language_name || result.language;
}

function kindLabel(result) {
  if (result.kind === "manual") return "Creator captions";
  if (result.kind === "speech-to-text") return "Speech-to-text";
  return result.platform === "tiktok" ? "TikTok captions" : "Auto-generated captions";
}

function badge(text, className) {
  const span = document.createElement("span");
  span.className = `badge ${className}`;
  if (className.startsWith("badge-youtube") || className.startsWith("badge-tiktok")) {
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.setAttribute("aria-hidden", "true");
    span.append(dot);
  }
  span.append(text);
  return span;
}

function renderResult() {
  const r = state.result;
  els.result.hidden = false;
  els.claudeHint.hidden = true;

  // Video card
  els.title.textContent = r.title || `${PLATFORM_NAMES[r.platform]} video ${r.video_id}`;
  els.title.title = r.title || "";
  const metaParts = [r.author, r.duration ? formatClock(r.duration) : null].filter(Boolean);
  els.meta.textContent = metaParts.join(" · ");
  els.meta.hidden = metaParts.length === 0;
  els.thumbLink.href = r.url;
  els.thumbLink.classList.toggle("portrait", r.platform === "tiktok");
  if (r.thumbnail) {
    els.thumb.src = r.thumbnail;
    els.thumbLink.hidden = false;
    els.thumb.onerror = () => {
      els.thumbLink.hidden = true;
    };
  } else {
    els.thumbLink.hidden = true;
  }

  const kindClass = { manual: "badge-manual", auto: "badge-auto", "speech-to-text": "badge-stt" }[r.kind] || "badge-auto";
  els.badges.replaceChildren(
    badge(PLATFORM_NAMES[r.platform] || r.platform, `badge-${r.platform}`),
    badge(kindLabel(r), kindClass),
    badge(languageLabel(r), "badge-lang"),
    badge(`via ${r.provider}`, "badge-provider"),
  );

  // Notes (fallbacks taken, quality caveats)
  els.notes.replaceChildren(
    ...(r.notes || []).map((n) => {
      const li = document.createElement("li");
      li.textContent = n;
      return li;
    }),
  );
  els.notes.hidden = !(r.notes && r.notes.length);

  // Track picker
  const tracks = r.tracks || [];
  const options = tracks.map((t) => {
    const opt = document.createElement("option");
    opt.value = t.code;
    const suffix = t.kind === "manual" ? " · creator" : "";
    opt.textContent = `${t.name}${suffix}`;
    return opt;
  });
  if (r.kind === "speech-to-text") {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Speech-to-text";
    options.unshift(opt);
  }
  els.trackSelect.replaceChildren(...options);
  els.trackSelect.value = r.kind === "speech-to-text" ? "" : r.track_code;
  els.trackField.hidden = options.length < 2;

  els.stats.textContent = `${r.word_count.toLocaleString()} words · ${r.segments.length.toLocaleString()} lines`;
  renderTranscript();
}

function appendHighlighted(parent, text) {
  for (const part of splitMatches(text, state.query)) {
    if (part.match) {
      const mark = document.createElement("mark");
      mark.textContent = part.text;
      parent.append(mark);
    } else {
      parent.append(part.text);
    }
  }
}

function timestampNode(seconds) {
  const href = timestampUrl(state.result, seconds);
  const node = document.createElement(href ? "a" : "span");
  node.className = "ts";
  node.textContent = formatClock(seconds);
  if (href) {
    node.href = href;
    node.target = "_blank";
    node.rel = "noopener noreferrer";
    node.title = "Open the video at this moment";
  }
  return node;
}

function renderTranscript() {
  const r = state.result;
  if (!r) return;
  const box = els.transcript;
  box.classList.toggle("no-ts", !els.timestamps.checked);
  const last = r.segments[r.segments.length - 1];
  box.style.setProperty("--ts-chars", String(formatClock(last ? last.start : 0).length));
  const fragment = document.createDocumentFragment();
  let matches = 0;

  if (state.view === "segments") {
    for (const seg of r.segments) {
      const hits = countMatches(seg.text, state.query);
      if (state.query && hits === 0) continue; // searching filters to matching lines
      matches += hits;
      const row = document.createElement("div");
      row.className = "line";
      const text = document.createElement("span");
      text.className = "line-text";
      appendHighlighted(text, seg.text);
      row.append(timestampNode(seg.start), text);
      fragment.append(row);
    }
  } else {
    for (const para of r.paragraphs) {
      const p = document.createElement("p");
      p.className = "para";
      p.append(timestampNode(para.start));
      matches += countMatches(para.text, state.query);
      appendHighlighted(p, para.text);
      fragment.append(p);
    }
  }

  if (!fragment.childNodes.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = state.query ? `No lines contain “${state.query}”.` : "This transcript is empty.";
    fragment.append(empty);
  }
  box.replaceChildren(fragment);
  els.matchCount.textContent = state.query ? `${matches} match${matches === 1 ? "" : "es"}` : "";
}

// ---- copy / download
function currentText() {
  const r = state.result;
  return els.timestamps.checked && state.view === "segments" ? toTimestampedText(r.segments) : toPlainText(r);
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API needs a secure context (https or localhost); fall back.
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.append(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    area.remove();
    return ok;
  }
}

async function copyText() {
  const ok = await copyToClipboard(currentText());
  els.copy.textContent = ok ? "Copied" : "Copy failed";
  setTimeout(() => {
    els.copy.textContent = "Copy text";
  }, 1600);
}

// Android's share sheet can't carry arbitrarily large text; past this, copy instead.
const SHARE_LIMIT = 400000;

function showClaudeHint(copied) {
  els.claudeHint.replaceChildren();
  if (copied) {
    const link = document.createElement("a");
    link.href = "https://claude.ai/new";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Open Claude";
    els.claudeHint.append("Copied the transcript. ", link, " and paste it into a new chat, then ask your question.");
  } else {
    els.claudeHint.textContent = "Couldn't copy automatically. Select the transcript text, copy it, and paste it into Claude.";
  }
  els.claudeHint.hidden = false;
}

async function sendToClaude() {
  const r = state.result;
  if (!r) return;
  const text = claudeMessage(r, currentText());
  // On a phone, the share sheet hands the text straight to the Claude app.
  const phone = window.matchMedia("(pointer: coarse)").matches;
  if (phone && navigator.share && text.length <= SHARE_LIMIT) {
    try {
      await navigator.share({ text });
      return;
    } catch (err) {
      if (err && err.name === "AbortError") return; // share sheet closed
      // Sharing isn't possible here: copy instead.
    }
  }
  showClaudeHint(await copyToClipboard(text));
}

const DOWNLOADS = {
  txt: { type: "text/plain", build: (r) => currentText() },
  srt: { type: "application/x-subrip", build: (r) => toSrt(r.segments) },
  vtt: { type: "text/vtt", build: (r) => toVtt(r.segments) },
  json: { type: "application/json", build: (r) => toJson(r) },
};

function download(format) {
  const r = state.result;
  const spec = DOWNLOADS[format];
  if (!r || !spec) return;
  const blob = new Blob([spec.build(r)], { type: `${spec.type};charset=utf-8` });
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filenameFor(r, format);
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

// ---- wiring
function setView(view) {
  state.view = view;
  for (const btn of document.querySelectorAll("[data-view]")) {
    btn.setAttribute("aria-pressed", String(btn.dataset.view === view));
  }
  savePrefs();
  renderTranscript();
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  // Accept a whole pasted share message, not just a bare link.
  const url = extractVideoLink(els.url.value) || els.url.value.trim();
  if (!url) {
    showError("Paste a YouTube or TikTok video link first.");
    els.url.focus();
    return;
  }
  els.url.value = url;
  lookup(url);
});

els.paste.addEventListener("click", async () => {
  let text = "";
  try {
    text = await navigator.clipboard.readText();
  } catch {
    showError("Couldn't read the clipboard.", ["Long-press the link box and choose Paste instead."]);
    return;
  }
  const url = extractVideoLink(text) || text.trim();
  if (!url) {
    showError("The clipboard is empty.", ["Copy a YouTube or TikTok link first (Share → Copy link)."]);
    return;
  }
  els.url.value = url;
  lookup(url);
});

els.trackSelect.addEventListener("change", () => {
  const code = els.trackSelect.value;
  if (code && state.lastUrl) lookup(state.lastUrl, code);
});

let searchTimer = null;
els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.query = els.search.value.trim();
    renderTranscript();
  }, 120);
});

els.timestamps.addEventListener("change", () => {
  savePrefs();
  renderTranscript();
});
els.stt.addEventListener("change", savePrefs);
els.copy.addEventListener("click", copyText);
els.claude.addEventListener("click", sendToClaude);
for (const btn of document.querySelectorAll("[data-view]")) {
  btn.addEventListener("click", () => setView(btn.dataset.view));
}
for (const btn of document.querySelectorAll("[data-download]")) {
  btn.addEventListener("click", () => download(btn.dataset.download));
}

async function init() {
  const prefs = loadPrefs();
  if (prefs.view === "paragraphs" || prefs.view === "segments") setView(prefs.view);
  if (typeof prefs.timestamps === "boolean") els.timestamps.checked = prefs.timestamps;
  if (typeof prefs.stt === "boolean") els.stt.checked = prefs.stt;

  try {
    const health = await (await fetch("/api/health")).json();
    if (health.speech_to_text) {
      els.sttOption.hidden = false;
      els.sttLimit.textContent = `(slower; videos up to ${health.speech_to_text_max_minutes} min)`;
    }
  } catch {
    /* server unreachable; the first lookup will report it */
  }

  if (navigator.clipboard?.readText) els.paste.hidden = false;

  // Opened with ?url=… (a bookmark) or from Android's Share menu, which sends
  // the shared message as ?text=… and sometimes ?title=….
  const params = new URL(window.location.href).searchParams;
  const shared = ["url", "text", "title"].map((name) => params.get(name)).filter(Boolean);
  if (shared.length) {
    const initial = extractVideoLink(...shared) || (params.get("url") || "").trim();
    if (initial) {
      els.url.value = initial;
      lookup(initial);
    } else {
      showError("That share didn't include a video link.", ["Share a YouTube or TikTok video, or paste its link."]);
    }
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* needs https (or localhost); the app works without it, it just can't be installed */
    });
  }
}

init();
