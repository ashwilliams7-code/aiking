import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("aiking_song_engine.py")
spec = importlib.util.spec_from_file_location("aiking_song_engine", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load engine module from {MODULE_PATH}")
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)


class AikingSongEngineTests(unittest.TestCase):
    def test_build_release_packet_from_sample_brief(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        brief = repo_root / "music-engine" / "briefs" / "aiking-brand-anthem.json"

        with tempfile.TemporaryDirectory() as tmp:
            paths = engine.build_release(brief, Path(tmp), "2026-06-28")

            self.assertTrue(paths.suno_packet.exists())
            self.assertTrue(paths.youtube_packet.exists())
            self.assertTrue(paths.spotify_packet.exists())
            self.assertTrue(paths.calendar.exists())
            self.assertIn("AIKING runs the future", paths.lyrics.read_text(encoding="utf-8"))
            self.assertIn("Mode: Advanced", paths.suno_packet.read_text(encoding="utf-8"))
            self.assertIn("Spotify / Distributor Packet", paths.spotify_packet.read_text(encoding="utf-8"))

            manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "packet_ready_human_publish_gate_required")
            self.assertEqual(manifest["release_slug"], "aiking-runs-the-future")

            with paths.calendar.open("r", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["platform"], "YouTube Shorts / Reels")


if __name__ == "__main__":
    unittest.main()
