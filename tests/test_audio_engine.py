import importlib.util
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "audio-engine.py"
spec = importlib.util.spec_from_file_location("audio_engine", MODULE_PATH)
audio_engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio_engine)


class AudioFormatTests(unittest.TestCase):
    def test_mp3_and_m4a_are_supported_audio_formats(self):
        self.assertTrue(audio_engine.is_supported_audio_file("presentation.mp3"))
        self.assertTrue(audio_engine.is_supported_audio_file("presentation.m4a"))
        self.assertTrue(audio_engine.is_supported_audio_file("PRESENTATION.M4A"))

    def test_default_audio_file_uses_single_local_supported_audio_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            expected_audio = temp_path / "test1.m4a"
            expected_audio.write_bytes(b"placeholder")

            self.assertEqual(audio_engine.resolve_default_audio_file(temp_path), expected_audio)

    def test_default_audio_file_falls_back_to_sample_when_no_local_audio_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(
                audio_engine.resolve_default_audio_file(Path(temp_dir)),
                Path(temp_dir) / "sample_presentation.mp3",
            )

    def test_default_audio_file_prefers_sample_when_multiple_local_audio_files_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sample_audio = temp_path / "sample_presentation.mp3"
            sample_audio.write_bytes(b"placeholder")
            (temp_path / "test1.m4a").write_bytes(b"placeholder")

            self.assertEqual(audio_engine.resolve_default_audio_file(temp_path), sample_audio)

    def test_default_audio_file_uses_newest_supported_file_when_multiple_exist_without_sample(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            older_audio = temp_path / "older.m4a"
            newer_audio = temp_path / "newer.m4a"
            older_audio.write_bytes(b"older")
            newer_audio.write_bytes(b"newer")
            older_time = 1000
            newer_time = 2000
            older_audio.touch()
            newer_audio.touch()
            import os
            os.utime(older_audio, (older_time, older_time))
            os.utime(newer_audio, (newer_time, newer_time))

            self.assertEqual(audio_engine.resolve_default_audio_file(temp_path), newer_audio)

    def test_list_local_audio_files_returns_all_supported_audio_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "b.m4a").write_bytes(b"placeholder")
            (temp_path / "a.mp3").write_bytes(b"placeholder")
            (temp_path / "notes.txt").write_text("ignore")

            self.assertEqual(
                audio_engine.list_local_audio_files(temp_path),
                [temp_path / "a.mp3", temp_path / "b.m4a"],
            )

    def test_default_output_path_uses_audio_stem(self):
        self.assertEqual(
            audio_engine.resolve_output_path("test1.m4a"),
            Path("test1_analysis.json"),
        )

    def test_write_analysis_json_saves_result_to_disk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "result.json"
            result = {
                "observed_metrics": {"wpm": 132.5, "pitch_std": 64.66},
                "scores": {"overall_score": 0.0},
            }

            saved_path = audio_engine.write_analysis_json(result, output_path)

            self.assertEqual(saved_path, output_path)
            self.assertEqual(json.loads(output_path.read_text()), result)

    def test_process_audio_files_writes_json_one_by_one_and_prints_progress_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            first_audio = temp_path / "first.m4a"
            second_audio = temp_path / "second.m4a"
            first_audio.write_bytes(b"first")
            second_audio.write_bytes(b"second")
            calls = []
            printed_lines = []

            def fake_analyze_audio(audio_path):
                calls.append(Path(audio_path))
                print("internal analysis output should be hidden")
                return {"file": Path(audio_path).name}

            audio_engine.process_audio_files(
                [first_audio, second_audio],
                analyze_fn=fake_analyze_audio,
                print_fn=printed_lines.append,
            )

            self.assertEqual(calls, [first_audio, second_audio])
            self.assertEqual(printed_lines, ["1/2 complete", "2/2 complete", "complete"])
            self.assertEqual(json.loads((temp_path / "first_analysis.json").read_text()), {"file": "first.m4a"})
            self.assertEqual(json.loads((temp_path / "second_analysis.json").read_text()), {"file": "second.m4a"})

    def test_process_audio_files_can_write_batch_results_to_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            output_dir = temp_path / "results"
            input_dir.mkdir()
            first_audio = input_dir / "base.m4a"
            second_audio = input_dir / "better.mp3"
            first_audio.write_bytes(b"first")
            second_audio.write_bytes(b"second")

            def fake_analyze_audio(audio_path):
                return {"file": Path(audio_path).name}

            audio_engine.process_audio_files(
                [first_audio, second_audio],
                output_dir=output_dir,
                analyze_fn=fake_analyze_audio,
                print_fn=lambda message: None,
            )

            self.assertEqual(json.loads((output_dir / "base_analysis.json").read_text()), {"file": "base.m4a"})
            self.assertEqual(json.loads((output_dir / "better_analysis.json").read_text()), {"file": "better.mp3"})
            self.assertFalse((input_dir / "base_analysis.json").exists())
            self.assertFalse((input_dir / "better_analysis.json").exists())

    def test_process_benchmark_audio_files_uses_base_as_profile_for_mp3_and_m4a_scripts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "voice-testing1"
            input_dir.mkdir()
            base_audio = input_dir / "base.mp3"
            script_one = input_dir / "script1.m4a"
            script_two = input_dir / "script2.mp3"
            base_audio.write_bytes(b"base")
            script_one.write_bytes(b"script one")
            script_two.write_bytes(b"script two")
            calls = []

            def fake_analyze_audio(audio_path, scoring_profile=None):
                calls.append((Path(audio_path).name, scoring_profile))
                raw_by_name = {
                    "base.mp3": {"wpm": 150.0, "pitch_variance_std": 42.0, "is_monotone_delivery": False},
                    "script1.m4a": {"wpm": 170.0, "pitch_variance_std": 35.0, "is_monotone_delivery": False},
                    "script2.mp3": {"wpm": 130.0, "pitch_variance_std": 55.0, "is_monotone_delivery": False},
                }
                return {
                    "analysis_status": "Success",
                    "baseline_profile": {
                        "archetype": "Template",
                        "dataset_source": "Template profile",
                        "calibrated_metrics": {
                            "target_wpm": 160.7,
                            "target_pitch_std": 36.37,
                            "wpm_tolerance_margin": 12.0,
                            "pitch_tolerance_margin": 8.0,
                        },
                    },
                    "performance_scores": {
                        "pacing_alignment": 100.0,
                        "vocal_intonation_variety": 100.0,
                        "word_choice_efficiency": 100.0,
                        "aggregate_vocal_rating": 100.0,
                    },
                    "extracted_telemetry": {
                        "measured_wpm": raw_by_name[Path(audio_path).name]["wpm"],
                        "measured_pitch_std_hz": raw_by_name[Path(audio_path).name]["pitch_variance_std"],
                        "total_filler_count": 0,
                    },
                    "pauses_timeline": [],
                    "actionable_coaching_cards": [],
                    "transcript": {"text": "test transcript", "word_count": 10},
                    "speech_issues": {},
                    "raw_metrics": raw_by_name[Path(audio_path).name],
                    "debug": {"word_timeline": []},
                }

            audio_engine.process_benchmark_audio_files(
                [base_audio, script_one, script_two],
                analyze_fn=fake_analyze_audio,
                print_fn=lambda message: None,
            )

            self.assertEqual([name for name, _ in calls], ["base.mp3", "script1.m4a", "script2.mp3"])
            self.assertIsNone(calls[0][1])
            self.assertEqual(calls[1][1]["calibrated_metrics"]["target_wpm"], 150.0)
            self.assertEqual(calls[1][1]["calibrated_metrics"]["target_pitch_std"], 42.0)
            self.assertEqual(calls[2][1]["calibrated_metrics"]["target_wpm"], 150.0)
            self.assertEqual(calls[2][1]["calibrated_metrics"]["target_pitch_std"], 42.0)
            base_result = json.loads((input_dir / "base_analysis.json").read_text())
            script_result = json.loads((input_dir / "script1_analysis.json").read_text())
            self.assertEqual(base_result["baseline_profile"]["dataset_source"], "Folder benchmark: base.mp3")
            self.assertEqual(script_result["baseline_profile"]["dataset_source"], "Folder benchmark: base.mp3")

    def test_main_batches_selected_input_directory_to_selected_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "round_1"
            output_dir = temp_path / "round_1_results"
            input_dir.mkdir()
            (input_dir / "base.m4a").write_bytes(b"base")
            (input_dir / "better.mp3").write_bytes(b"better")

            with patch.object(audio_engine, "process_benchmark_audio_files") as process_benchmark_audio_files:
                audio_engine.main([
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                ])

            process_benchmark_audio_files.assert_called_once()
            args, kwargs = process_benchmark_audio_files.call_args
            self.assertEqual(args[0], [input_dir / "base.m4a", input_dir / "better.mp3"])
            self.assertEqual(kwargs["output_dir"], output_dir)

    def test_main_accepts_input_alias_for_selected_input_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "voice-testing1"
            input_dir.mkdir()
            (input_dir / "test1.m4a").write_bytes(b"test1")

            with patch.object(audio_engine, "process_audio_files") as process_audio_files:
                audio_engine.main(["--input", str(input_dir)])

            process_audio_files.assert_called_once()
            args, kwargs = process_audio_files.call_args
            self.assertEqual(args[0], [input_dir / "test1.m4a"])
            self.assertIsNone(kwargs["output_dir"])

    def test_no_extension_audio_engine_wrapper_exists_for_python_command(self):
        wrapper_path = MODULE_PATH.with_name("audio-engine")

        self.assertTrue(wrapper_path.is_file())

    def test_other_file_formats_are_not_supported(self):
        self.assertFalse(audio_engine.is_supported_audio_file("presentation.wav"))
        self.assertFalse(audio_engine.is_supported_audio_file("presentation.txt"))

    def test_missing_supported_file_fails_before_audio_decoding(self):
        fake_librosa = SimpleNamespace(load=Mock(side_effect=AssertionError("librosa.load was called")))

        with patch.object(audio_engine, "librosa", fake_librosa):
            with self.assertRaises(FileNotFoundError):
                audio_engine.analyze_audio("missing.m4a")

    def test_analysis_decodes_supported_files_with_whisper_decoder(self):
        with tempfile.NamedTemporaryFile(suffix=".m4a") as audio_file:
            fake_librosa = SimpleNamespace(
                load=Mock(side_effect=AssertionError("librosa.load was called")),
                note_to_hz=Mock(side_effect=[65, 2093]),
                pyin=Mock(return_value=(np.array([100.0, np.nan]), None, None)),
            )
            fake_model = Mock()
            fake_model.transcribe.return_value = ([SimpleNamespace(words=[
                SimpleNamespace(word="hello", start=0.0, end=0.2),
            ])], None)

            fake_decode_audio = Mock(return_value=np.zeros(16000, dtype=np.float32))

            with (
                patch.object(audio_engine, "librosa", fake_librosa),
                patch.object(audio_engine, "decode_audio", fake_decode_audio, create=True),
                patch.object(audio_engine, "WhisperModel", Mock(return_value=fake_model)),
            ):
                with redirect_stdout(io.StringIO()):
                    results = audio_engine.analyze_audio(audio_file.name)

        fake_decode_audio.assert_called_once_with(audio_file.name, sampling_rate=16000)
        fake_librosa.load.assert_not_called()
        self.assertEqual(results["analysis_status"], "Success")
        json.dumps(results)

    def test_alignment_score_has_full_credit_inside_tolerance(self):
        self.assertEqual(audio_engine.score_alignment(78.5, 78.5, 19.7), 100.0)
        self.assertEqual(audio_engine.score_alignment(90.0, 78.5, 19.7), 100.0)
        self.assertLess(audio_engine.score_alignment(140.0, 78.5, 19.7), 100.0)

    def test_score_caps_make_visible_issues_meaningfully_affect_scores(self):
        scores = audio_engine.build_performance_scores(
            observed_wpm=138.1,
            observed_pitch_std=66.24,
            filler_count=1,
            total_words=91,
            calibrated_metrics={
                "target_wpm": 135.2,
                "target_pitch_std": 78.24,
                "wpm_tolerance_margin": 12.0,
                "pitch_tolerance_margin": 8.0,
            },
        )

        self.assertEqual(scores["pacing_alignment"], 100.0)
        self.assertEqual(scores["vocal_intonation_variety"], 85.0)
        self.assertEqual(scores["word_choice_efficiency"], 90.0)
        self.assertEqual(scores["aggregate_vocal_rating"], 92.0)

    def test_score_caps_lower_flawed_filler_heavy_delivery(self):
        scores = audio_engine.build_performance_scores(
            observed_wpm=110.4,
            observed_pitch_std=68.32,
            filler_count=6,
            total_words=66,
            calibrated_metrics={
                "target_wpm": 135.2,
                "target_pitch_std": 78.24,
                "wpm_tolerance_margin": 12.0,
                "pitch_tolerance_margin": 8.0,
            },
        )

        self.assertEqual(scores["pacing_alignment"], 85.0)
        self.assertEqual(scores["vocal_intonation_variety"], 85.0)
        self.assertEqual(scores["word_choice_efficiency"], 75.0)
        self.assertEqual(scores["aggregate_vocal_rating"], 81.5)

    def test_analysis_output_uses_delivery_evaluation_report_shape(self):
        baseline = {
            "archetype": "Singapore Formal/Academic Rehearsal",
            "dataset_source": "IMDA National Speech Corpus (NSC) via Mesolitica",
            "calibrated_metrics": {
                "target_wpm": 78.5,
                "target_pitch_std": 99.99,
                "wpm_tolerance_margin": 19.7,
                "pitch_tolerance_margin": 9.74,
            },
        }

        words = [
            SimpleNamespace(word="basically", start=0.0, end=0.2),
            SimpleNamespace(word="actually", start=0.3, end=0.5),
        ]
        words.extend(
            SimpleNamespace(word=f"word{i}", start=float(i), end=float(i) + 0.2)
            for i in range(77)
        )
        fake_segment = SimpleNamespace(words=words)

        with tempfile.NamedTemporaryFile(suffix=".m4a") as audio_file:
            fake_librosa = SimpleNamespace(
                note_to_hz=Mock(side_effect=[65, 2093]),
                pyin=Mock(return_value=(np.array([1.0, 200.98]), None, None)),
            )
            fake_model = Mock()
            fake_model.transcribe.return_value = ([fake_segment], None)
            fake_decode_audio = Mock(return_value=np.zeros(16000 * 60, dtype=np.float32))

            with (
                patch.object(audio_engine, "librosa", fake_librosa),
                patch.object(audio_engine, "decode_audio", fake_decode_audio, create=True),
                patch.object(audio_engine, "WhisperModel", Mock(return_value=fake_model)),
                patch.object(audio_engine, "load_scoring_profile", Mock(return_value=baseline)),
            ):
                with redirect_stdout(io.StringIO()):
                    results = audio_engine.analyze_audio(audio_file.name)

        self.assertEqual(results["analysis_status"], "Success")
        self.assertEqual(results["baseline_profile"]["archetype"], baseline["archetype"])
        self.assertEqual(results["baseline_profile"]["calibrated_metrics"], baseline["calibrated_metrics"])
        self.assertEqual(results["extracted_telemetry"]["measured_wpm"], 79.0)
        self.assertEqual(results["extracted_telemetry"]["measured_pitch_std_hz"], 99.99)
        self.assertEqual(results["extracted_telemetry"]["total_filler_count"], 2)
        self.assertIn("performance_scores", results)
        self.assertEqual(results["performance_scores"]["pacing_alignment"], 100.0)
        self.assertEqual(results["performance_scores"]["vocal_intonation_variety"], 100.0)
        self.assertLess(results["performance_scores"]["word_choice_efficiency"], 100.0)
        self.assertEqual(
            results["transcript"]["text"],
            "basically actually " + " ".join(f"word{i}" for i in range(77)),
        )
        self.assertEqual(results["transcript"]["word_count"], 79)
        self.assertNotIn("transcript_segments", results)
        self.assertEqual(len(results["debug"]["word_timeline"]), 79)
        self.assertEqual(results["debug"]["word_timeline"][-1]["word"], "word76")
        self.assertEqual(
            [issue["phrase"] for issue in results["speech_issues"]["filler_words"]],
            ["basically", "actually"],
        )
        self.assertIn("actionable_coaching_cards", results)
        json.dumps(results)

    def test_analysis_output_includes_human_readable_summary_and_metric_meanings(self):
        baseline = {
            "archetype": "Singapore Formal/Academic Rehearsal",
            "dataset_source": "IMDA National Speech Corpus (NSC) via Mesolitica",
            "calibrated_metrics": {
                "target_wpm": 78.5,
                "target_pitch_std": 99.99,
                "wpm_tolerance_margin": 19.7,
                "pitch_tolerance_margin": 9.74,
            },
        }
        words = [
            SimpleNamespace(word="So,", start=0.0, end=0.2),
            SimpleNamespace(word="basically,", start=0.3, end=0.5),
        ]
        words.extend(
            SimpleNamespace(word=f"word{i}", start=float(i), end=float(i) + 0.2)
            for i in range(158)
        )
        fake_segment = SimpleNamespace(words=words)

        with tempfile.NamedTemporaryFile(suffix=".m4a") as audio_file:
            fake_librosa = SimpleNamespace(
                note_to_hz=Mock(side_effect=[65, 2093]),
                pyin=Mock(return_value=(np.array([10.0, 82.74]), None, None)),
            )
            fake_model = Mock()
            fake_model.transcribe.return_value = ([fake_segment], None)
            fake_decode_audio = Mock(return_value=np.zeros(16000 * 60, dtype=np.float32))

            with (
                patch.object(audio_engine, "librosa", fake_librosa),
                patch.object(audio_engine, "decode_audio", fake_decode_audio, create=True),
                patch.object(audio_engine, "WhisperModel", Mock(return_value=fake_model)),
                patch.object(audio_engine, "load_scoring_profile", Mock(return_value=baseline)),
            ):
                with redirect_stdout(io.StringIO()):
                    results = audio_engine.analyze_audio(audio_file.name)

        self.assertIn("summary", results)
        self.assertEqual(results["summary"]["overall_label"], "Needs work")
        self.assertIn("fast", results["summary"]["headline"].lower())
        self.assertGreaterEqual(len(results["summary"]["top_actions"]), 2)
        self.assertEqual(results["readable_metrics"]["pace"]["label"], "Too fast")
        self.assertEqual(results["readable_metrics"]["pace"]["unit"], "words per minute")
        self.assertIn("58.8-98.2", results["readable_metrics"]["pace"]["target_range"])
        self.assertEqual(results["readable_metrics"]["intonation"]["label"], "Too flat")
        self.assertEqual(results["readable_metrics"]["fillers"]["label"], "Some fillers")
        self.assertIn("raw_metrics", results)
        self.assertNotIn("metadata", results)
        self.assertEqual(results["raw_metrics"]["wpm"], 160.0)
        self.assertEqual(results["raw_metrics"]["pitch_variance_std"], 36.37)

    def test_speech_issues_include_pacing_and_intonation_flags(self):
        readable_metrics = {
            "pace": {"label": "Too fast", "meaning": "You are speaking faster than the target range."},
            "intonation": {"label": "Too flat", "meaning": "Your pitch variation is below the target range."},
            "fillers": {"label": "Clean", "meaning": "You used very few filler words."},
        }
        issues = audio_engine.build_speech_issues(
            [{"word": "Hello", "clean": "hello", "start": 0.0, "end": 0.2}],
            [],
            readable_metrics=readable_metrics,
        )

        self.assertEqual(issues["pacing_flags"][0]["issue"], "Too fast")
        self.assertEqual(issues["intonation_flags"][0]["issue"], "Too flat")

    def test_split_speech_segments_uses_sentence_boundaries_and_word_timestamps(self):
        words = [
            {"word": "First", "clean": "first", "start": 0.0, "end": 0.3},
            {"word": "idea.", "clean": "idea", "start": 0.4, "end": 0.8},
            {"word": "Second", "clean": "second", "start": 1.6, "end": 1.9},
            {"word": "point?", "clean": "point", "start": 2.0, "end": 2.4},
        ]

        segments = audio_engine.split_speech_segments(words)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["phrase"], "First idea.")
        self.assertEqual(segments[0]["start"], 0.0)
        self.assertEqual(segments[0]["end"], 0.8)
        self.assertEqual(segments[0]["word_count"], 2)
        self.assertEqual(segments[1]["phrase"], "Second point?")
        self.assertEqual(segments[1]["start"], 1.6)
        self.assertEqual(segments[1]["end"], 2.4)

    def test_build_segment_metrics_counts_fillers_pauses_wpm_and_pitch_variation(self):
        words = [
            {"word": "So,", "clean": "so", "start": 0.0, "end": 0.2},
            {"word": "first.", "clean": "first", "start": 0.3, "end": 0.6},
            {"word": "Basically", "clean": "basically", "start": 1.0, "end": 1.2},
            {"word": "next", "clean": "next", "start": 2.9, "end": 3.1},
            {"word": "idea.", "clean": "idea", "start": 3.2, "end": 3.5},
        ]
        pauses = [
            {"timestamp": 1.2, "duration": 1.7, "classification": "Hesitation Gap"},
        ]
        pitch_timeline = [100.0, 110.0, 120.0, 130.0] * 40

        segments = audio_engine.build_segment_metrics(words, pauses, pitch_timeline, sample_rate=16000)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["filler_count"], 1)
        self.assertEqual(segments[0]["wpm"], 200.0)
        self.assertEqual(segments[0]["pause_gap_count"], 0)
        self.assertIsNotNone(segments[0]["pitch_variance_std"])
        self.assertEqual(segments[1]["filler_count"], 1)
        self.assertEqual(segments[1]["pause_gap_count"], 1)
        self.assertEqual(segments[1]["pause_gaps"][0]["classification"], "Hesitation Gap")

    def test_speech_issues_use_segment_specific_pacing_and_intonation_flags(self):
        words = [
            {"word": "Opening", "clean": "opening", "start": 0.0, "end": 0.2},
            {"word": "rush.", "clean": "rush", "start": 0.3, "end": 0.5},
            {"word": "Flat", "clean": "flat", "start": 3.0, "end": 3.4},
            {"word": "close.", "clean": "close", "start": 3.5, "end": 4.0},
        ]
        segment_metrics = [
            {
                "phrase": "Opening rush.",
                "start": 0.0,
                "end": 0.5,
                "word_count": 2,
                "wpm": 240.0,
                "filler_count": 0,
                "pitch_variance_std": 35.0,
                "pause_gap_count": 0,
                "pause_gaps": [],
            },
            {
                "phrase": "Flat close.",
                "start": 3.0,
                "end": 4.0,
                "word_count": 2,
                "wpm": 120.0,
                "filler_count": 0,
                "pitch_variance_std": 4.0,
                "pause_gap_count": 0,
                "pause_gaps": [],
            },
        ]
        calibrated_metrics = {
            "target_wpm": 120.0,
            "target_pitch_std": 30.0,
            "wpm_tolerance_margin": 20.0,
            "pitch_tolerance_margin": 10.0,
        }

        issues = audio_engine.build_speech_issues(
            words,
            [],
            segment_metrics=segment_metrics,
            calibrated_metrics=calibrated_metrics,
        )

        self.assertEqual(issues["pacing_flags"][0]["phrase"], "Opening rush.")
        self.assertEqual(issues["pacing_flags"][0]["issue"], "Too fast")
        self.assertEqual(issues["intonation_flags"][0]["phrase"], "Flat close.")
        self.assertEqual(issues["intonation_flags"][0]["issue"], "Too flat")

    def test_current_profile_uses_good_test_as_benchmark(self):
        project_root = MODULE_PATH.parent
        profile = json.loads((project_root / "calibrated_singapore_targets.json").read_text())

        metrics = profile["calibrated_metrics"]

        self.assertEqual(profile["dataset_source"], "Prototype benchmark: good-test.m4a")
        self.assertEqual(metrics["target_wpm"], 160.7)
        self.assertEqual(metrics["target_pitch_std"], 36.37)
        self.assertEqual(metrics["wpm_tolerance_margin"], 12.0)
        self.assertEqual(metrics["pitch_tolerance_margin"], 8.0)

    def test_summary_is_not_strong_when_metrics_have_visible_issues(self):
        readable_metrics = {
            "pace": {"label": "On target"},
            "intonation": {"label": "Over-varied"},
            "fillers": {"label": "Distracting fillers"},
        }
        performance_scores = {"aggregate_vocal_rating": 85.0}

        summary = audio_engine.build_summary(readable_metrics, performance_scores, [])

        self.assertEqual(summary["overall_label"], "Developing")


if __name__ == "__main__":
    unittest.main()
