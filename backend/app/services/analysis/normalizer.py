from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def normalize_audio(input_path: Path) -> Path:
    """Normalize audio for provider analysis when ffmpeg is available.

    We intentionally fall back to the original file when ffmpeg is unavailable so
    local development and tests stay lightweight.
    """

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        # Check if we have a locally downloaded ffmpeg binary in the project bin directory (useful for Render free tier)
        local_ffmpeg = Path(__file__).parents[3] / "bin" / "ffmpeg"
        if local_ffmpeg.exists():
            ffmpeg = str(local_ffmpeg)
        else:
            return input_path

    normalized_path = input_path.with_name(f"{input_path.stem}.normalized.wav")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(normalized_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not normalized_path.exists():
        return input_path
    return normalized_path
