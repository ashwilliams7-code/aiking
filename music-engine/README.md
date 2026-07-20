# AIKING Music Engine — YouTube + Spotify Release Packets

A local repeatable engine for turning an AIKING song idea into a publish-ready packet:

1. Suno Advanced prompt + sectioned lyrics.
2. YouTube upload packet: titles, description, tags, pinned comment, Shorts cuts, visualizer direction.
3. Spotify/distributor packet: release metadata, rights checklist, asset filenames.
4. Release checklist and repurposing calendar.

The engine intentionally stops before paid/API publishing actions. Final generation credits, YouTube login/publish, distributor payment, ISRC/UPC, and rights confirmations stay as human approval gates.

## Quick start

From the repo root:

```bash
python3 tools/aiking_song_engine.py music-engine/briefs/aiking-brand-anthem.json --date 2026-06-28
```

Generated packets land under:

```text
music-engine/releases/<date>-<song-slug>/
```

## Brief format

Create a JSON file in `music-engine/briefs/` with these required fields:

- `song_title`
- `artist`
- `purpose`
- `hook`
- `voice`
- `language`
- `genre`

Useful optional fields:

- `audience`
- `mood`
- `keywords`
- `avoid`
- `tempo`
- `duration_target`
- `contributors`
- `model`
- `save_to`

## Production lane

```text
brief JSON
  ↓
aiking_song_engine.py
  ↓
release packet
  ↓
generate 2-4 candidates
  ↓
pick + master
  ↓
YouTube visualizer + Shorts
  ↓
distributor upload for Spotify/streaming
```

## Next upgrade points

- Add direct audio-download ingestion once a generated track URL/job id exists.
- Add ffmpeg mastering QA for loudness/clipping/duration.
- Add visualizer generation templates for 16:9 YouTube and 9:16 Shorts.
- Add YouTube Data API upload after Ash explicitly approves account/auth scope.
- Add distributor-specific CSV export after a distributor is chosen.
