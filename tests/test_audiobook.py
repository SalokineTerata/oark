import asyncio
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outil"))

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

import main_audiobook
import orientation
import qwen_renderer
from assembler import assemble
from diarizer import diarize, markdown_blocks
from main_audiobook import chapter_paths
from tts_generator import check_voices, generate_audio


def fake_chat(batch: dict):
    """Answer speaker-resolution calls with KODA and analysis batches with the given content."""
    import json

    def chat(**kwargs):
        reply = Mock()
        if "role" in kwargs["format"]["properties"]:
            reply.message.content = json.dumps({"locuteur": "AUTRE", "role": "koda"})
        else:
            reply.message.content = json.dumps(batch)
        return reply
    return chat


class AudiobookTests(unittest.TestCase):
    def test_markdown_preserves_order_and_separates_dialogue(self):
        text = "# Chapitre 1 — Départ\n\n**Koda** arrive.\nElle attend.\n\n— Bonjour !\n— Salut !\n\nIl tourne. — Allons-y.\n"
        self.assertEqual(markdown_blocks(text), [
            "Chapitre 1 — Départ", "Koda arrive. Elle attend.",
            "— Bonjour !", "— Salut !", "Il tourne.", "— Allons-y.",
        ])

    def test_chapters_sorted_numerically_and_gaps_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for number in range(1, 11):
                (directory / f"{number} - chapitre.md").touch()
            paths = chapter_paths(directory)
            self.assertEqual(paths[1].name, "2 - chapitre.md")
            self.assertEqual(paths[-1].name, "10 - chapitre.md")
            (directory / "2 - chapitre.md").unlink()
            with self.assertRaisesRegex(ValueError, "chapitre 2 attendu"):
                chapter_paths(directory)

    def test_diarization_validates_response_and_preserves_text(self):
        client = Mock()
        client.chat.return_value.message.content = "[KODA]"
        self.assertEqual(diarize(["— Bonjour !"], client, "test"), [("[KODA]", "— Bonjour !")])
        client.chat.return_value.message.content = "Koda"
        with self.assertRaisesRegex(ValueError, "Réponse Ollama invalide"):
            diarize(["— Bonjour !"], client, "test")

    def test_generation_names_and_retries(self):
        async def save(path):
            Path(path).write_bytes(b"mp3")
        communicate = Mock()
        communicate.return_value.save = AsyncMock(side_effect=save)
        with tempfile.TemporaryDirectory() as temp, patch("tts_generator.edge_tts.Communicate", communicate):
            files = asyncio.run(generate_audio([("[KODA]", "Bonjour"), ("[JARO]", "Salut")], Path(temp)))
            self.assertEqual([path.name for path in files], ["0001_KODA.mp3", "0002_JARO.mp3"])
            self.assertNotEqual(communicate.call_args_list[0].args[1], communicate.call_args_list[1].args[1])
            with self.assertRaisesRegex(ValueError, "Locuteur inconnu"):
                asyncio.run(generate_audio([("[AUTRE]", "Bonjour")], Path(temp)))
        communicate.return_value.save = AsyncMock(side_effect=[OSError("interruption"), None])
        with tempfile.TemporaryDirectory() as temp, patch("tts_generator.edge_tts.Communicate", communicate), \
                patch("tts_generator.asyncio.sleep", new_callable=AsyncMock):
            async def retry_save(path):
                if communicate.return_value.save.await_count == 1:
                    raise OSError("interruption")
                Path(path).write_bytes(b"mp3")
            communicate.return_value.save.side_effect = retry_save
            asyncio.run(generate_audio([("[KODA]", "Bonjour")], Path(temp)))
            self.assertEqual(communicate.return_value.save.await_count, 2)

    def test_assembly_order_silence_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            first = directory / "first.mp3"
            second = directory / "second.mp3"
            Sine(440).to_audio_segment(duration=500).export(first, format="mp3").close()
            Sine(880).to_audio_segment(duration=500).export(second, format="mp3").close()
            unrelated = directory / "other.txt"
            unrelated.write_text("keep", encoding="utf-8")
            target = directory / "book.mp3"
            assemble([first, second], target)
            result = AudioSegment.from_mp3(target)
            self.assertLess(abs(len(result) - 1200), 60)
            self.assertLess(result[550:650].rms, result[100:400].rms / 10)
            self.assertGreater(result[100:400].rms, 1000)
            self.assertGreater(result[800:1100].rms, 1000)
            def crossings(segment):
                samples = segment.get_array_of_samples()
                return sum(a < 0 <= b for a, b in zip(samples, samples[1:]))
            self.assertLess(crossings(result[100:400]), crossings(result[800:1100]))
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")
            self.assertTrue(first.exists() and second.exists())

    def test_bad_segment_does_not_replace_existing_book(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            bad = directory / "bad.mp3"
            bad.write_bytes(b"not an mp3")
            target = directory / "book.mp3"
            target.write_bytes(b"original")
            with self.assertRaisesRegex(RuntimeError, "Impossible de décoder"):
                assemble([bad], target)
            self.assertEqual(target.read_bytes(), b"original")
            self.assertEqual(sorted(path.name for path in directory.iterdir()), ["bad.mp3", "book.mp3"])

    def test_voice_probe_checks_all_voices(self):
        async def stream():
            yield {"type": "audio", "data": b"audio"}
        communicate = Mock()
        communicate.return_value.stream = stream
        with patch("tts_generator.edge_tts.Communicate", communicate):
            asyncio.run(check_voices())
        self.assertEqual(communicate.call_count, 5)

    def test_orientation_rejects_bad_dimensions_unknown_and_changed_sources(self):
        segment = {"id": 1, "texte": "Chapitre 1", "locuteur": "NARRATEUR", "type": "chapitre",
                   "fiabilite_locuteur": "explicite",
                   "emotion": "neutre", "valence": 0.0, "activation": 0.5, "dominance": 0.5,
                   "intensite": 0.5, "intention": "narrer", "vocalisation": "parole"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "1 - test.md"
            source.write_text("test", encoding="utf-8")
            path = root / "orientation.json"
            document = {"version": 1, "chapitre": 1, "source": source.name,
                        "sha256_source": orientation.source_hash(source), "segments": [segment]}
            orientation.atomic_json(path, document)
            orientation.read_orientation(path, source, 1)
            segment["activation"] = 2
            with self.assertRaisesRegex(ValueError, "activation"):
                orientation.validate_segment(segment)
            segment["activation"] = 0.5
            segment["locuteur"] = "INCONNU"
            with self.assertRaisesRegex(ValueError, "INCONNU"):
                orientation.validate_segment(segment)
            source.write_text("modifié", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Source modifiée"):
                orientation.read_orientation(path, source, 1)

    def test_voice_profiles_and_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "voix.json"
            qwen_renderer.ensure_profiles(path, {"NARRATEUR", "KODA", "ARTILLEUR"})
            voices = qwen_renderer.load_profiles(path)
            self.assertEqual(voices["KODA"]["timbre"], "ono_anna")
            self.assertIn(voices["ARTILLEUR"]["timbre"], qwen_renderer.TIMBRES)
            orientation.atomic_json(path, {"KODA": {"timbre": "inconnu", "caractere": "x"}})
            with self.assertRaisesRegex(ValueError, "Profil vocal invalide"):
                qwen_renderer.load_profiles(path)
        profile = {"timbre": "ono_anna", "caractere": "a young woman"}
        segment = {"intensite": 0.9, "activation": 0.8, "dominance": 0.5, "valence": 0,
                   "emotion": "colere", "intention": "menacer", "vocalisation": "cri", "type": "dialogue"}
        text = qwen_renderer.instruction(segment, profile)
        for expected in ("intensely angry", "Fast", "threatening", "shouting"):
            self.assertIn(expected, text)
        segment["type"] = "narration"
        self.assertNotEqual(text, qwen_renderer.instruction(segment, profile))

    def test_long_text_is_split_at_sentence_ends(self):
        text = " ".join(["Une phrase assez longue pour remplir."] * 20)
        pieces = qwen_renderer.split_text(text)
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(len(p) <= qwen_renderer.MAX_CHARS for p in pieces))
        self.assertEqual(" ".join(pieces), text)

    def test_long_sentence_is_split_without_losing_words(self):
        text = " ".join(["Une phrase continue"] * 30) + "."
        pieces = qwen_renderer.split_text(text)
        self.assertTrue(all(len(p) <= qwen_renderer.MAX_CHARS for p in pieces))
        self.assertEqual(" ".join(pieces), text)

    def test_auto_mode_rejects_unresolved_speaker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "livre-test"
            directory.mkdir()
            source = directory / "1 - test.md"
            source.write_text("# Chapitre 1 — Essai", encoding="utf-8")
            segment = {"id": 1, "texte": "Chapitre 1 — Essai", "locuteur": "INCONNU", "type": "chapitre",
                       "fiabilite_locuteur": "incertain", "emotion": "neutre", "valence": 0.0, "activation": 0.5,
                       "dominance": 0.5, "intensite": 0.5, "intention": "narrer", "vocalisation": "rire"}
            document = {"version": 1, "chapitre": 1, "source": source.name,
                        "sha256_source": orientation.source_hash(source), "segments": [segment]}
            with patch.object(main_audiobook, "ROOT", root), patch.object(main_audiobook, "BOOKS", {"1": "livre-test"}), \
                    patch("main_audiobook.ollama.Client"), patch("main_audiobook.check_model"), \
                    patch("main_audiobook.analyse_chapter", return_value=document), \
                    patch("sys.argv", ["main_audiobook.py", "analyse", "--auto"]):
                main_audiobook.run()
            path = root / "voix" / "voix.json"
            self.assertNotIn("INCONNU", qwen_renderer.load_profiles(path))
            with patch.object(main_audiobook, "ROOT", root), patch.object(main_audiobook, "BOOKS", {"1": "livre-test"}), \
                    patch("main_audiobook.Engine"), patch("main_audiobook.render_book", return_value=root / "audio.mp3") as render, \
                    patch("sys.argv", ["main_audiobook.py", "generer", "--auto"]):
                with self.assertRaisesRegex(ValueError, "INCONNU"):
                    main_audiobook.run()
            render.assert_not_called()

    def test_orchestrator_keeps_reviewed_orientation_and_renders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chapter_dir = root / "livre-test"
            chapter_dir.mkdir()
            source = chapter_dir / "1 - test.md"
            source.write_text("# Chapitre 1 — Essai\n\nBonjour.", encoding="utf-8")
            audio_dir = root / "exports-audiobook" / "temp_audio"
            audio_dir.mkdir(parents=True)
            other = audio_dir / "a-conserver.mp3"
            other.write_bytes(b"untouched")
            def segment(number, text, speaker, kind):
                return {"id": number, "texte": text, "locuteur": speaker, "type": kind,
                        "fiabilite_locuteur": "explicite",
                        "emotion": "neutre", "valence": 0.0, "activation": 0.5,
                        "dominance": 0.5, "intensite": 0.5, "intention": "narrer",
                        "vocalisation": "parole"}
            document = {"version": 1, "chapitre": 1, "source": source.name,
                        "sha256_source": orientation.source_hash(source), "modele_analyse": "test",
                        "segments": [segment(1, "Chapitre 1 — Essai", "NARRATEUR", "chapitre"),
                                     segment(2, "Bonjour.", "KODA", "dialogue")]}
            with patch.object(main_audiobook, "ROOT", root), \
                    patch.object(main_audiobook, "BOOKS", {"1": "livre-test"}), \
                    patch("main_audiobook.ollama.Client"), \
                    patch("main_audiobook.check_model"), \
                    patch("main_audiobook.analyse_chapter", return_value=document) as analyse:
                with patch("sys.argv", ["main_audiobook.py", "analyse", "--book", "1"]):
                    main_audiobook.run()
                    main_audiobook.run()
                self.assertEqual(analyse.call_count, 1)
                with patch("sys.argv", ["main_audiobook.py", "generer", "--book", "1"]):
                    with self.assertRaisesRegex(ValueError, "Validation humaine requise"):
                        main_audiobook.run()
                engine = Mock()
                engine.speak.side_effect = lambda jobs: [
                    np.array(Sine(220).to_audio_segment(duration=600).get_array_of_samples(), dtype=np.float32) / 32768
                    for _ in jobs]
                with patch("main_audiobook.Engine", return_value=engine), \
                        patch("sys.argv", ["main_audiobook.py", "generer", "--book", "1", "--approuve"]):
                    main_audiobook.run()
                    main_audiobook.run()
                self.assertEqual(engine.speak.call_count, 1)
            self.assertTrue((root / "exports-audiobook" / "Livre-1_Audiobook.mp3").is_file())
            self.assertGreater(len(AudioSegment.from_mp3(root / "exports-audiobook" / "Livre-1_Audiobook.mp3")), 1000)
            self.assertEqual(other.read_bytes(), b"untouched")
            self.assertTrue((root / "exports-audiobook" / "orientations" / "Livre-1" / "chapitre-001.json").exists())

    def test_analysis_preserves_text_and_identifies_dialogue(self):
        response = {"locuteur": "KODA", "emotion": "neutre", "valence": 0.0, "activation": 0.5,
                    "fiabilite_locuteur": "explicite",
                    "dominance": 0.5, "intensite": 0.5, "intention": "repondre", "vocalisation": "parole"}
        client = Mock()
        import json
        client.chat.side_effect = fake_chat({"0": response, "1": response})
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "1 - test.md"
            source.write_text("# Chapitre 1 — Essai\n\n— Bonjour !", encoding="utf-8")
            data = orientation.analyse_chapter(source, 1, client, "test")
            self.assertEqual([(s["locuteur"], s["texte"]) for s in data["segments"]],
                             [("NARRATEUR", "Chapitre 1 — Essai"), ("KODA", "— Bonjour !")])

    def test_analysis_retries_invalid_json(self):
        import json
        response = {"locuteur": "NARRATEUR", "emotion": "neutre", "valence": 0.0, "activation": 0.5,
                    "fiabilite_locuteur": "explicite", "dominance": 0.5, "intensite": 0.5,
                    "intention": "narrer", "vocalisation": "parole"}
        invalid, valid = Mock(), Mock()
        invalid.message.content = "{"
        valid.message.content = json.dumps({"0": response})
        client = Mock()
        client.chat.side_effect = [invalid, valid]
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "1 - test.md"
            source.write_text("# Chapitre 1 — Essai", encoding="utf-8")
            self.assertEqual(len(orientation.analyse_chapter(source, 1, client, "test")["segments"]), 1)
        self.assertEqual(client.chat.call_count, 2)

    def test_analysis_splits_incise_and_keeps_speaker_for_continuation(self):
        response = {"locuteur": "KODA", "emotion": "neutre", "valence": 0.0, "activation": 0.5,
                    "fiabilite_locuteur": "deduit", "dominance": 0.5, "intensite": 0.5,
                    "intention": "repondre", "vocalisation": "parole"}
        client = Mock()
        import json
        client.chat.side_effect = fake_chat({str(i): response for i in range(4)})
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "1 - test.md"
            source.write_text("# Chapitre 1 — Essai\n\n— Viens, dit-elle doucement. Je t'attends.", encoding="utf-8")
            segments = orientation.analyse_chapter(source, 1, client, "test")["segments"]
            self.assertEqual([(s["type"], s["locuteur"], s["texte"]) for s in segments], [
                ("chapitre", "NARRATEUR", "Chapitre 1 — Essai"),
                ("dialogue", "KODA", "— Viens,"),
                ("narration", "NARRATEUR", "dit-elle doucement."),
                ("dialogue", "KODA", "Je t'attends."),
            ])
            self.assertEqual(segments[3]["fiabilite_locuteur"], "deduit")
            self.assertEqual(" ".join(s["texte"] for s in segments[1:]),
                             "— Viens, dit-elle doucement. Je t'attends.")

    def test_dialogue_without_attribution_remains_intact(self):
        block = "— Je réponds à ta question. Je suis là."
        self.assertEqual(orientation.split_blocks([block]), [(block, "dialogue", None)])


if __name__ == "__main__":
    unittest.main()
