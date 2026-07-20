#!/usr/bin/env python3
"""AIKING Song Engine.

Creates a repeatable release packet for AIKING songs destined for YouTube and
Spotify-style distribution. The engine does not upload/publish by itself; it
produces the assets, metadata, prompts, and QA checklist needed for the human
publishing gates.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any, Iterable


@dataclass(frozen=True)
class ReleasePaths:
    root: Path
    suno_packet: Path
    lyrics: Path
    youtube_packet: Path
    spotify_packet: Path
    checklist: Path
    calendar: Path
    manifest: Path


REQUIRED_FIELDS = (
    "song_title",
    "artist",
    "purpose",
    "hook",
    "voice",
    "language",
    "genre",
)


DEFAULTS: dict[str, Any] = {
    "project": "AIKING",
    "brand_positioning": "Australian executive AI advisory and agentic implementation consultancy",
    "audience": ["founders", "CEOs", "operators", "private clients"],
    "mood": ["futuristic", "confident", "premium"],
    "keywords": ["AI agents", "automation", "executive intelligence", "implementation", "Australia"],
    "avoid": ["cheesy startup jargon", "fake guarantees", "overly corporate phrasing", "profanity"],
    "model": "Suno v5.5 / current best available",
    "save_to": "AIKING Music Engine",
    "tempo": "mid-tempo, 88-96 BPM feel",
    "duration_target": "2:15-2:45",
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "aiking-song"


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,;]\s*", value) if part.strip()]
    return [str(value).strip()]


def load_brief(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        brief = json.load(handle)
    merged = dict(DEFAULTS)
    merged.update({key: value for key, value in brief.items() if value not in (None, "")})
    missing = [field for field in REQUIRED_FIELDS if not str(merged.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Brief is missing required field(s): {', '.join(missing)}")
    for key in ("audience", "mood", "keywords", "avoid"):
        merged[key] = as_list(merged.get(key))
    return merged


def release_paths(out_dir: Path, brief: dict[str, Any], release_date: str) -> ReleasePaths:
    slug = brief.get("slug") or slugify(str(brief["song_title"]))
    root = out_dir / f"{release_date}-{slug}"
    return ReleasePaths(
        root=root,
        suno_packet=root / "01-suno-advanced-packet.md",
        lyrics=root / "02-lyrics.md",
        youtube_packet=root / "03-youtube-upload-packet.md",
        spotify_packet=root / "04-spotify-distribution-packet.md",
        checklist=root / "05-release-checklist.md",
        calendar=root / "06-content-calendar.csv",
        manifest=root / "manifest.json",
    )


def comma_join(items: Iterable[str]) -> str:
    return ", ".join(item for item in items if item)


def render_style(brief: dict[str, Any]) -> str:
    style_parts = [
        str(brief["genre"]),
        str(brief.get("tempo", DEFAULTS["tempo"])),
        str(brief["voice"]),
        "clean premium mix",
        "wide cinematic intro",
        "memorable chant-ready chorus",
        "tight 808/sub foundation",
        "glossy synth texture",
        "subtle AI/vocoder ear-candy, not robotic novelty",
        "radio-ready structure",
        "YouTube intro usable hook",
    ]
    style_parts.extend(as_list(brief.get("mood")))
    return comma_join(style_parts)


def render_lyrics(brief: dict[str, Any]) -> str:
    hook = str(brief["hook"]).strip()
    keywords = as_list(brief.get("keywords"))
    keyword_line = ", ".join(keywords[:4]) if keywords else "quiet machines, sharper decisions"
    audience = as_list(brief.get("audience"))
    audience_line = " / ".join(audience[:3]) if audience else "founders / operators / leaders"

    return dedent(
        f"""
        # {brief['song_title']}

        [Intro]
        Lights low, servers hum
        New dawn loading, old rules done
        AIKING in the signal, moving clean
        Quiet power in the machine

        [Verse 1]
        Boardroom pressure, midnight screens
        Big decisions running underneath
        Founders tired of the guesswork game
        We build the agents, give the future a name

        {keyword_line}
        Turn the chaos into operating lines
        No loud promises, no plastic crown
        Just real systems when the sun goes down

        [Pre-Chorus]
        If the market moves fast, we move faster
        If the noise gets loud, we cut through
        From the first idea to the working answer
        Watch what applied intelligence can do

        [Chorus]
        {hook}
        {hook}
        From the boardroom floor to the city lights
        We make tomorrow work tonight
        {hook}

        [Verse 2]
        For the {audience_line}
        We turn sharp vision into muscle and speed
        Private briefings, clean execution
        Less confusion, more evolution

        Every workflow gets a second brain
        Every bottleneck breaks its chain
        Not a demo, not a slide-deck dream
        AIKING builds what leaders need

        [Bridge]
        Oooooh, let the old world fade
        Oooooh, new engines wake
        Oooooh, when the future calls
        We don't chase it, we install

        [Final Chorus]
        {hook}
        {hook}
        From the boardroom floor to the city lights
        We make tomorrow work tonight
        AIKING rises, calm and bright
        We make tomorrow work tonight

        [Outro]
        Lights low, systems live
        Future built, not imagined
        AIKING
        """
    ).strip() + "\n"


def render_suno_packet(brief: dict[str, Any]) -> str:
    style = render_style(brief)
    lyrics = render_lyrics(brief).rstrip()
    avoid = comma_join(as_list(brief.get("avoid")))
    return (
        f"# Suno Advanced Packet — {brief['song_title']}\n\n"
        "Mode: Advanced\n"
        f"Model: {brief.get('model', DEFAULTS['model'])}\n"
        "Audio: none unless a reference track is supplied\n"
        f"Voice: {brief['voice']}\n"
        "Inspo: none unless a reference is supplied\n"
        "Instrumental: false\n"
        f"Song Title: {brief['song_title']}\n"
        f"Save to: {brief.get('save_to', DEFAULTS['save_to'])}\n\n"
        "## Style\n"
        f"{style}\n\n"
        "## Avoid\n"
        f"{avoid}\n\n"
        "## Lyrics\n"
        f"{lyrics}\n"
    )


def render_youtube_packet(brief: dict[str, Any], release_slug: str) -> str:
    title = brief["song_title"]
    hook = brief["hook"]
    tags = as_list(brief.get("keywords")) + ["AIKING", "AI agents", "AI consulting", "business automation"]
    return dedent(
        f"""
        # YouTube Upload Packet — {title}

        ## Primary title
        {title} | AIKING Official Visualizer

        ## Alternate titles
        - {title} — The AIKING Brand Anthem
        - AIKING: We Make Tomorrow Work Tonight
        - {hook} | Official AIKING Music Visualizer

        ## Description
        AIKING is an Australian executive AI advisory and agentic implementation consultancy for founders, CEOs, boards, private clients, and operators who want practical AI systems — not hype.

        This track is the sonic identity for AIKING: calm power, executive intelligence, and real-world AI implementation.

        Website: https://aiking.info  
        Private Executive Briefing: ash@aiking.info

        ## Pinned comment
        What workflow would you want an AI agent to remove from your week first?

        ## Tags
        {comma_join(dict.fromkeys(tags))}

        ## Shorts cutdowns
        - 00:00-00:15 — intro/hook logo reveal
        - 00:42-01:02 — first chorus as standalone Short
        - 01:54-02:20 — bridge into final chorus

        ## Visualizer direction
        Dark premium AIKING palette, executive boardroom x neural interface, subtle gold/blue highlights, clean typography, slow camera movement, no cartoon robots, no generic neon spam.

        ## Output naming
        - Longform: `{release_slug}-official-visualizer.mp4`
        - Short 1: `{release_slug}-short-hook.mp4`
        - Thumbnail: `{release_slug}-thumbnail.png`
        """
    ).strip() + "\n"


def render_spotify_packet(brief: dict[str, Any], release_slug: str) -> str:
    contributors = as_list(brief.get("contributors")) or [str(brief["artist"])]
    return dedent(
        f"""
        # Spotify / Distributor Packet — {brief['song_title']}

        ## Release metadata
        Track title: {brief['song_title']}
        Artist: {brief['artist']}
        Version: Original Mix
        Language: {brief['language']}
        Explicit: No
        Duration target: {brief.get('duration_target', DEFAULTS['duration_target'])}
        Primary genre: {brief['genre']}
        Mood: {comma_join(as_list(brief.get('mood')))}
        Contributors / credits: {comma_join(contributors)}
        Copyright line: © {date.today().year} {brief['artist']}
        Phonographic copyright: ℗ {date.today().year} {brief['artist']}

        ## Distributor notes
        Spotify music releases normally go through a distributor or label delivery system. This engine prepares the packet; final distributor login, payment, rights confirmation, UPC/ISRC assignment, and publish button remain human approval gates.

        ## Asset requirements checklist
        - Final master WAV, 44.1kHz/16-bit or better, no clipping.
        - Backup MP3/AAC reference for review only.
        - Square cover art, minimum 3000x3000 preferred.
        - Clean rights record for generated music, lyrics, cover art, and samples.
        - ISRC/UPC from distributor or label account.
        - Release date and territory settings.

        ## Suggested filenames
        - Master: `{release_slug}-master.wav`
        - Review MP3: `{release_slug}-review.mp3`
        - Cover art: `{release_slug}-cover-3000.png`
        """
    ).strip() + "\n"


def render_checklist(brief: dict[str, Any]) -> str:
    return dedent(
        f"""
        # Release Checklist — {brief['song_title']}

        ## 1. Create / generate
        - [ ] Paste `01-suno-advanced-packet.md` into the music generator.
        - [ ] Generate 2-4 candidates.
        - [ ] Pick strongest candidate by hook memorability, vocal quality, and brand fit.
        - [ ] Save generation URL/job id in `manifest.json`.

        ## 2. Master / QA
        - [ ] Export/download WAV or highest-quality audio available.
        - [ ] Check loudness, clipping, intro silence, and ending tail.
        - [ ] Save final master and review MP3 in this release folder.
        - [ ] Confirm no accidental copyrighted melody/sample/reference dependence.

        ## 3. YouTube
        - [ ] Create visualizer or lyric video.
        - [ ] Export 16:9 MP4 and 9:16 Shorts cuts.
        - [ ] Use `03-youtube-upload-packet.md` for title, description, tags, pinned comment.
        - [ ] Human approves upload/login/publish.

        ## 4. Spotify / streaming
        - [ ] Create 3000x3000 cover art.
        - [ ] Confirm rights/commercial-use terms.
        - [ ] Upload through distributor/label system.
        - [ ] Human approves charge/payee, UPC/ISRC, release date, publish.

        ## 5. Repurpose
        - [ ] Post Short/Reel hook cut.
        - [ ] Add track to AIKING site/media kit if approved.
        - [ ] Create follow-up post: “How we built AIKING's sonic identity.”
        """
    ).strip() + "\n"


def render_calendar_rows(brief: dict[str, Any]) -> list[dict[str, str]]:
    title = str(brief["song_title"])
    return [
        {"stage": "teaser", "platform": "YouTube Shorts / Reels", "asset": "15s hook cut", "copy": f"The AIKING sound is coming: {brief['hook']}"},
        {"stage": "launch", "platform": "YouTube", "asset": "official visualizer", "copy": f"{title} is live — the AIKING brand anthem."},
        {"stage": "launch", "platform": "Spotify", "asset": "streaming release", "copy": f"Stream {title} by {brief['artist']}."},
        {"stage": "follow-up", "platform": "LinkedIn", "asset": "behind-the-build post", "copy": "Why executive AI needs a sonic identity, not just a logo."},
    ]


def write_calendar(path: Path, brief: dict[str, Any]) -> None:
    rows = render_calendar_rows(brief)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stage", "platform", "asset", "copy"])
        writer.writeheader()
        writer.writerows(rows)


def build_release(brief_path: Path, out_dir: Path, release_date: str) -> ReleasePaths:
    brief = load_brief(brief_path)
    paths = release_paths(out_dir, brief, release_date)
    paths.root.mkdir(parents=True, exist_ok=True)

    release_slug = paths.root.name.removeprefix(f"{release_date}-")
    lyrics = render_lyrics(brief)
    paths.lyrics.write_text(lyrics, encoding="utf-8")
    paths.suno_packet.write_text(render_suno_packet(brief), encoding="utf-8")
    paths.youtube_packet.write_text(render_youtube_packet(brief, release_slug), encoding="utf-8")
    paths.spotify_packet.write_text(render_spotify_packet(brief, release_slug), encoding="utf-8")
    paths.checklist.write_text(render_checklist(brief), encoding="utf-8")
    write_calendar(paths.calendar, brief)

    manifest = {
        "engine": "aiking_song_engine",
        "release_date": release_date,
        "release_slug": release_slug,
        "brief_path": str(brief_path),
        "outputs": {name: str(getattr(paths, name)) for name in paths.__dataclass_fields__ if name != "root"},
        "status": "packet_ready_human_publish_gate_required",
        "publish_gates": ["music-generation approval/credits", "YouTube login/publish", "distributor payment/rights confirmation"],
    }
    paths.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an AIKING YouTube/Spotify song release packet.")
    parser.add_argument("brief", type=Path, help="Path to a JSON song brief.")
    parser.add_argument("--out", type=Path, default=Path("music-engine/releases"), help="Output directory for release packets.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Release packet date prefix, YYYY-MM-DD.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = build_release(args.brief, args.out, args.date)
    print(json.dumps({"release_root": str(paths.root), "manifest": str(paths.manifest)}, indent=2))


if __name__ == "__main__":
    main()
