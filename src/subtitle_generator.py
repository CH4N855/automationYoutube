import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import config

def generate_subtitles_from_audio(audio_path: str, output_srt_path: Optional[str] = None) -> Optional[str]:
    """
    Transcribe audio file using faster-whisper and generate an SRT file
    with short, punchy 3-5 word segments optimized for YouTube Shorts.
    """
    if not output_srt_path:
        base = os.path.splitext(audio_path)[0]
        output_srt_path = f"{base}_captions.srt"

    try:
        from faster_whisper import WhisperModel
        # Use lightweight tiny model for blazing fast CPU inference (<2s)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, word_timestamps=True)

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
