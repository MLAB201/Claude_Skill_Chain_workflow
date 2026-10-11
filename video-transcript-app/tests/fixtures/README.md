# Test fixtures

- `youtube_innertube_*.json`, `youtube_timedtext.xml`: trimmed copies of real YouTube
  responses captured by the `youtube-transcript-api` project (its `test/assets`), used to
  drive that library offline through a fake HTTP adapter. Only the keys the library reads
  were kept.
- `youtube_watch_page.html`: a stub watch page carrying just the `INNERTUBE_API_KEY` the
  library looks for (the real public key is replaced with a placeholder).
- `youtube_auto_rolling.vtt`, `youtube_auto.json3`, `manual.vtt`, `tiktok.srt`: hand-written
  in the formats YouTube and TikTok serve (YouTube's rolling auto-caption WebVTT with inline
  word timings, YouTube json3, a WebVTT file using NOTE/STYLE/voice tags, and the SRT that
  yt-dlp builds from TikTok's caption JSON).
