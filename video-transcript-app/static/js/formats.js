// Pure helpers for formatting transcripts. No DOM access, so they run under
// `node --test` too (see tests/formats.test.mjs).

function splitTime(seconds) {
  const totalMs = Math.max(0, Math.round((Number(seconds) || 0) * 1000));
  const ms = totalMs % 1000;
  const totalSeconds = Math.floor(totalMs / 1000);
  return {
    h: Math.floor(totalSeconds / 3600),
    m: Math.floor((totalSeconds % 3600) / 60),
    s: totalSeconds % 60,
    ms,
  };
}

const pad = (n, width = 2) => String(n).padStart(width, "0");

/** 75.4 -> "1:15", 3725 -> "1:02:05" */
export function formatClock(seconds) {
  const { h, m, s } = splitTime(Math.floor(Math.max(0, Number(seconds) || 0)));
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

function formatCueTime(seconds, separator) {
  const { h, m, s, ms } = splitTime(seconds);
  return `${pad(h)}:${pad(m)}:${pad(s)}${separator}${pad(ms, 3)}`;
}

export const formatSrtTime = (seconds) => formatCueTime(seconds, ",");
export const formatVttTime = (seconds) => formatCueTime(seconds, ".");

export function toSrt(segments) {
  return segments
    .map((seg, i) => `${i + 1}\n${formatSrtTime(seg.start)} --> ${formatSrtTime(seg.end)}\n${seg.text}\n`)
    .join("\n");
}

function escapeVtt(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function toVtt(segments) {
  const cues = segments.map(
    (seg) => `${formatVttTime(seg.start)} --> ${formatVttTime(seg.end)}\n${escapeVtt(seg.text)}\n`,
  );
  return ["WEBVTT\n", ...cues].join("\n");
}

export function toTimestampedText(segments) {
  return segments.map((seg) => `[${formatClock(seg.start)}] ${seg.text}`).join("\n") + "\n";
}

/** Plain text in paragraphs, as the server built it (result.text). */
export function toPlainText(result) {
  return `${result.text}\n`;
}

export function toJson(result) {
  const { platform, video_id, url, title, author, duration, language, language_name, kind, provider, segments, text } = result;
  return JSON.stringify(
    { platform, video_id, url, title, author, duration, language, language_name, kind, provider, segments, text },
    null,
    2,
  ) + "\n";
}

/** A download filename from the video title (or ID), safe on every OS. */
export function filenameFor(result, ext) {
  const base = (result.title || `${result.platform}-${result.video_id}`)
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^\w\s.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80)
    .trim()
    .replace(/\s/g, "-") || `${result.platform}-${result.video_id}`;
  const lang = result.language ? `.${String(result.language).replace(/[^\w-]/g, "")}` : "";
  return `${base}${lang}.${ext}`;
}

/** Split text into [{text, match}] runs for highlighting `query` (case-insensitive). */
export function splitMatches(text, query) {
  if (!query) return [{ text, match: false }];
  // Match on the original string (not a lower-cased copy, whose length can
  // differ for some characters) so the slices line up.
  const pattern = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "giu");
  const parts = [];
  let from = 0;
  for (const m of text.matchAll(pattern)) {
    if (m.index > from) parts.push({ text: text.slice(from, m.index), match: false });
    parts.push({ text: m[0], match: true });
    from = m.index + m[0].length;
  }
  if (from < text.length) parts.push({ text: text.slice(from), match: false });
  return parts;
}

export function countMatches(text, query) {
  return splitMatches(text, query).filter((p) => p.match).length;
}

/** Link to a moment in the video, where the platform supports it (YouTube only). */
export function timestampUrl(result, seconds) {
  if (result.platform !== "youtube") return null;
  return `https://www.youtube.com/watch?v=${encodeURIComponent(result.video_id)}&t=${Math.floor(seconds)}s`;
}

/**
 * The first http(s) link in any of the given strings, or "". Apps share links
 * wrapped in text ("Check out this video! https://vm.tiktok.com/…/"), and
 * Android puts the YouTube/TikTok share in `text` rather than `url`.
 */
export function extractVideoLink(...candidates) {
  for (const candidate of candidates) {
    const match = String(candidate ?? "").match(/https?:\/\/[^\s<>"']+/i);
    if (match) return match[0].replace(/[),.!?;:\]]+$/, "");
  }
  return "";
}
