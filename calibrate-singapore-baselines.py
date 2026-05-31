import json
import numpy as np
import fsspec
import librosa
import soundfile as sf
from huggingface_hub import hf_hub_download

def disable_numba_cache_for_librosa():
    try:
        import numba
    except ImportError:
        return

    for decorator_name in ("jit", "guvectorize", "vectorize"):
        original_decorator = getattr(numba, decorator_name, None)
        if original_decorator is None or getattr(original_decorator, "_it_speak_cache_disabled", False):
            continue

        def decorator_without_cache(*args, _original_decorator=original_decorator, **kwargs):
            kwargs["cache"] = False
            return _original_decorator(*args, **kwargs)

        decorator_without_cache._it_speak_cache_disabled = True
        setattr(numba, decorator_name, decorator_without_cache)


disable_numba_cache_for_librosa()

IMDA_DATASET_REPO = "mesolitica/IMDA-TTS"
IMDA_DATASET_REVISION = "874631a55a9c20ae9710ab2038fc578b23b5f5b7"
IMDA_ZIP_FILENAME = "FEMALE_01.zip"
IMDA_ZIP_FOLDER = "FEMALE_01"

def build_imda_wav_path(filename):
    return (
        f"zip://{IMDA_ZIP_FOLDER}/{filename}"
        f"::hf://datasets/{IMDA_DATASET_REPO}@{IMDA_DATASET_REVISION}/{IMDA_ZIP_FILENAME}"
    )

def load_singapore_metadata(hf_hub_download_fn=hf_hub_download):
    metadata_path = hf_hub_download_fn(
        repo_id=IMDA_DATASET_REPO,
        repo_type="dataset",
        revision=IMDA_DATASET_REVISION,
        filename="texts.json",
    )

    with open(metadata_path) as f:
        return json.load(f)

def iter_singapore_samples(metadata, max_samples, open_fn=fsspec.open, read_audio_fn=sf.read):
    emitted = 0

    for item in metadata:
        if emitted >= max_samples:
            break

        text_transcript = item.get("text") or item.get("transcription") or ""
        if not text_transcript:
            continue

        with open_fn(build_imda_wav_path(item["filename"]), "rb") as audio_file:
            audio_data, sr = read_audio_fn(audio_file, dtype="float32")

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        emitted += 1
        yield {
            "audio": np.asarray(audio_data, dtype=np.float32),
            "sampling_rate": sr,
            "text": text_transcript,
        }

def run_singapore_calibration(num_samples=30):
    print(f"📡 Initializing Stream from Hugging Face for IMDA National Speech Corpus...")
    
    # IMDA-TTS stores WAV files inside a zip plus a top-level texts.json.
    # Stream individual zip members instead of letting datasets parse WAV bytes as JSON.
    metadata = load_singapore_metadata()
    
    all_wpms = []
    all_pitch_stds = []
    
    print(f"🧪 Analyzing the first {num_samples} local tracks to map Singaporean baselines...")
    
    for idx, item in enumerate(iter_singapore_samples(metadata, max_samples=num_samples)):
        # 1. Safely extract audio data from the stream
        audio_data = item["audio"]
        sr = item["sampling_rate"]
        
        # Handle defensive mapping for the transcript text depending on schema labels
        text_transcript = item["text"]
            
        # Standardize sample rate to 16kHz for uniform DSP analysis
        if sr != 16000:
            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=16000)
            sr = 16000
            
        # 2. Extract Pitch Variety (Intonation) tailored to local voice inflection
        f0, _, _ = librosa.pyin(
            audio_data, 
            fmin=librosa.note_to_hz('C2'), # Ingests low base registers
            fmax=librosa.note_to_hz('C7')  # Captures sharp emphasis points
        )
        voiced_pitches = [p for p in np.nan_to_num(f0) if p > 0]
        
        if voiced_pitches:
            pitch_std = float(np.std(voiced_pitches))
            all_pitch_stds.append(pitch_std)
        else:
            pitch_std = 0.0
        
        # 3. Compute Pacing Profile (Words Per Minute) 
        # Local speech pacing handles syllables differently than Western speech!
        word_count = len(text_transcript.split())
        duration_seconds = len(audio_data) / sr
        wpm = (word_count / duration_seconds) * 60
        all_wpms.append(wpm)
        
        print(f"   [Sample {idx+1}] WPM: {wpm:.1f} | Pitch StdDev: {pitch_std:.2f} | Transcript: \"{text_transcript[:40]}...\"")

    # 4. Generate the Calibrated Configuration JSON Output
    if not all_wpms or not all_pitch_stds:
        raise RuntimeError("Singapore calibration did not produce enough voiced speech samples.")

    calibrated_singapore_targets = {
        "archetype": "Singapore Formal/Academic Rehearsal",
        "dataset_source": "IMDA National Speech Corpus (NSC) via Mesolitica",
        "calibrated_metrics": {
            "target_wpm": round(float(np.mean(all_wpms)), 1),
            "target_pitch_std": round(float(np.mean(all_pitch_stds)), 2),
            "wpm_tolerance_margin": round(float(np.std(all_wpms)), 1),
            "pitch_tolerance_margin": round(float(np.std(all_pitch_stds)), 2)
        }
    }
    
    # 5. Export configuration profile 
    output_filename = "calibrated_singapore_targets.json"
    with open(output_filename, "w") as f:
        json.dump(calibrated_singapore_targets, f, indent=4)
        
    print(f"\n🎉 Localized Phase 1 Complete! Config targets emitted to '{output_filename}'")
    print(json.dumps(calibrated_singapore_targets, indent=4))

if __name__ == "__main__":
    run_singapore_calibration(num_samples=30)
