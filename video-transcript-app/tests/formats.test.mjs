// Run with: node --test tests/formats.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  countMatches,
  extractVideoLink,
  filenameFor,
  formatClock,
  formatSrtTime,
  splitMatches,
  timestampUrl,
  toSrt,
  toTimestampedText,
  toVtt,
} from "../static/js/formats.js";

const segments = [
  { start: 0.16, end: 2.149, text: "hey everyone" },
  { start: 3725.5, end: 3727, text: "R&D <draft> -- notes" },
];

test("clock formatting", () => {
  assert.equal(formatClock(0), "0:00");
  assert.equal(formatClock(75.9), "1:15");
  assert.equal(formatClock(3725), "1:02:05");
  assert.equal(formatClock(-3), "0:00");
});

test("cue timestamps round to milliseconds", () => {
  assert.equal(formatSrtTime(2.1495), "00:00:02,150");
  assert.equal(formatSrtTime(3725.5), "01:02:05,500");
});

test("SRT output", () => {
  assert.equal(
    toSrt(segments),
    "1\n00:00:00,160 --> 00:00:02,149\nhey everyone\n\n2\n01:02:05,500 --> 01:02:07,000\nR&D <draft> -- notes\n",
  );
});

test("VTT output escapes markup characters", () => {
  const vtt = toVtt(segments);
  assert.ok(vtt.startsWith("WEBVTT\n\n00:00:00.160 --> 00:00:02.149\nhey everyone\n"));
  assert.ok(vtt.includes("R&amp;D &lt;draft&gt; -- notes"));
});

test("timestamped text", () => {
  assert.equal(toTimestampedText(segments), "[0:00] hey everyone\n[1:02:05] R&D <draft> -- notes\n");
});

test("search highlighting is case-insensitive and regex-safe", () => {
  assert.deepEqual(splitMatches("Hey hey HEY", "hey"), [
    { text: "Hey", match: true },
    { text: " ", match: false },
    { text: "hey", match: true },
    { text: " ", match: false },
    { text: "HEY", match: true },
  ]);
  assert.equal(countMatches("a.b a+b (a)", "a.b"), 1);
  assert.equal(countMatches("price $5 (approx)", "(approx)"), 1);
  assert.deepEqual(splitMatches("nothing here", ""), [{ text: "nothing here", match: false }]);
});

test("filenames are safe", () => {
  assert.equal(
    filenameFor({ title: 'Café: "Best" video?! / part 2', platform: "youtube", video_id: "x", language: "en" }, "srt"),
    "Cafe-Best-video-part-2.en.srt",
  );
  assert.equal(filenameFor({ title: "", platform: "tiktok", video_id: "123", language: "eng-US" }, "txt"), "tiktok-123.eng-US.txt");
  assert.equal(filenameFor({ title: "🎉🎉", platform: "tiktok", video_id: "9", language: null }, "json"), "tiktok-9.json");
});

test("timestamp links only for YouTube", () => {
  assert.equal(
    timestampUrl({ platform: "youtube", video_id: "dQw4w9WgXcQ" }, 75.9),
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=75s",
  );
  assert.equal(timestampUrl({ platform: "tiktok", video_id: "1" }, 5), null);
});

test("pulls the video link out of shared text", () => {
  // What the TikTok and YouTube Android apps put in the share text.
  assert.equal(
    extractVideoLink("Check out this video! #fyp https://vm.tiktok.com/ZMabc123/ "),
    "https://vm.tiktok.com/ZMabc123/",
  );
  assert.equal(extractVideoLink("https://youtu.be/dQw4w9WgXcQ?si=Ab_cD-12"), "https://youtu.be/dQw4w9WgXcQ?si=Ab_cD-12");
  assert.equal(extractVideoLink("(see https://youtu.be/dQw4w9WgXcQ)."), "https://youtu.be/dQw4w9WgXcQ");
  // url param empty, text has the link, title is just a title
  assert.equal(extractVideoLink(null, "Watch: https://www.youtube.com/shorts/dQw4w9WgXcQ", "A title"), "https://www.youtube.com/shorts/dQw4w9WgXcQ");
  assert.equal(extractVideoLink("no link here", undefined, ""), "");
});
