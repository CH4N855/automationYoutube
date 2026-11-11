import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import imageio_ffmpeg
import config

def load_audio_waveform(media_path: str) -> Optional[np.ndarray]:
    """
    Extract audio track from video or audio file using bundled FFmpeg,
    converted to 16kHz mono float32 PCM numpy array.
    Completely avoids PyAV container decoding errors.
    """
    if not os.path.exists(media_path):
        return None

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_wav = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_wav = tmp_file.name

        cmd = [
            ffmpeg_exe, "-y",
            "-i", media_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            tmp_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or not os.path.exists(tmp_wav) or os.path.getsize(tmp_wav) == 0:
            return None

        with wave.open(tmp_wav, "rb") as wf:
            frames = wf.getnframes()
            if frames == 0:
                return None
            raw_bytes = wf.readframes(frames)
            audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        return audio_np
    except Exception as e:
        print(f"[AudioWaveform] Extraction notice: {e}")
        return None
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except Exception:
                pass

def generate_subtitles_from_audio(audio_path: str, output_srt_path: Optional[str] = None) -> Optional[str]:
    """
    Transcribe audio file using faster-whisper and generate an SRT file
    with short, punchy 3-5 word segments optimized for YouTube Shorts.
    """
    if not output_srt_path:
        base = os.path.splitext(audio_path)[0]
        output_srt_path = f"{base}_captions.srt"

    try:
        audio_np = load_audio_waveform(audio_path)
        if audio_np is None or len(audio_np) == 0:
            return None

        from faster_whisper import WhisperModel
        # Use lightweight tiny model for blazing fast CPU inference (<2s)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_np, word_timestamps=True)

        srt_entries = []
        counter = 1

        for segment in segments:
            if not segment.words:
                # Fallback to segment-level timestamp
                start_str = _format_srt_time(segment.start)
                end_str = _format_srt_time(segment.end)
                text = segment.text.strip().upper()
                srt_entries.append(f"{counter}\n{start_str} --> {end_str}\n{text}\n")
                counter += 1
                continue

            # Group words into short 2-4 word punchy chunks
            words = segment.words
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                c_start = _format_srt_time(chunk[0].start)
                c_end = _format_srt_time(chunk[-1].end)
                c_text = " ".join([w.word.strip().upper() for w in chunk])
                srt_entries.append(f"{counter}\n{c_start} --> {c_end}\n{c_text}\n")
                counter += 1

        if srt_entries:
            with open(output_srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_entries))
            return output_srt_path

    except Exception as e:
        print(f"[Subtitles] Transcription notice: {e}")
        return None

    return None

def _format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"
