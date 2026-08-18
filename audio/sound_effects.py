"""
[V16.8.0] J.A.R.V.I.S. Audio Cues & Sound Effects
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lightweight, zero-dependency audio cue synthesizer for J.A.R.V.I.S.
Generates soft, futuristic harmonic tones in memory without external audio assets.
"""

import math
import struct
import io
import threading
import logging
from typing import Optional

logger = logging.getLogger("JARVIS.SoundEffects")

# Lazy-loaded in-memory Sound objects
_CUE_SOUND: Optional[object] = None
_INIT_LOCK = threading.Lock()


def _generate_futuristic_chime_wav() -> bytes:
    """
    Synthesizes a dual-tone futuristic rising chime in-memory (WAV format).
    Frequencies: 880 Hz (A5) -> 1320 Hz (E6) with exponential decay envelope.
    """
    sample_rate = 22050
    duration_s = 0.18
    num_samples = int(sample_rate * duration_s)
    
    # 16-bit mono PCM
    raw_audio = bytearray()
    
    for i in range(num_samples):
        t = i / sample_rate
        # Frequency sweep from 880 to 1320 Hz
        freq = 880.0 + (1320.0 - 880.0) * (t / duration_s)
        # Soft exponential decay envelope
        envelope = math.exp(-6.0 * (t / duration_s))
        
        # Primary harmonic + gentle sub-harmonic
        sample_val = (math.sin(2.0 * math.pi * freq * t) * 0.7 +
                      math.sin(2.0 * math.pi * (freq * 0.5) * t) * 0.3)
        
        # Scale to 16-bit signed integer with gentle volume
        sample_int = int(sample_val * envelope * 12000.0)
        sample_int = max(-32768, min(32767, sample_int))
        
        raw_audio.extend(struct.pack("<h", sample_int))
        
    # Construct WAV header
    wav_header = bytearray()
    wav_header.extend(b"RIFF")
    wav_header.extend(struct.pack("<I", 36 + len(raw_audio)))
    wav_header.extend(b"WAVE")
    wav_header.extend(b"fmt ")
    wav_header.extend(struct.pack("<I", 16))       # Subchunk1Size (16 for PCM)
    wav_header.extend(struct.pack("<H", 1))        # AudioFormat (1 for PCM)
    wav_header.extend(struct.pack("<H", 1))        # NumChannels (1 = mono)
    wav_header.extend(struct.pack("<I", sample_rate)) # SampleRate
    wav_header.extend(struct.pack("<I", sample_rate * 2)) # ByteRate
    wav_header.extend(struct.pack("<H", 2))        # BlockAlign
    wav_header.extend(struct.pack("<H", 16))       # BitsPerSample
    wav_header.extend(b"data")
    wav_header.extend(struct.pack("<I", len(raw_audio)))
    
    return bytes(wav_header + raw_audio)


def _get_cue_sound():
    """Initializes and caches the pygame Sound object safely."""
    global _CUE_SOUND
    if _CUE_SOUND is not None:
        return _CUE_SOUND
        
    with _INIT_LOCK:
        if _CUE_SOUND is not None:
            return _CUE_SOUND
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            wav_bytes = _generate_futuristic_chime_wav()
            _CUE_SOUND = pygame.mixer.Sound(io.BytesIO(wav_bytes))
            _CUE_SOUND.set_volume(0.35)
            return _CUE_SOUND
        except Exception as e:
            logger.debug(f"[SoundEffects] Sound initialization skipped: {e}")
            return None


def play_speech_end_cue():
    """
    Plays a subtle futuristic chime indicating that speech recording finished
    and J.A.R.V.I.S. is now processing / transcribing the command.
    Non-blocking execution.
    """
    def _play():
        try:
            sound = _get_cue_sound()
            if sound:
                sound.play()
        except Exception as e:
            logger.debug(f"[SoundEffects] Play error: {e}")

    threading.Thread(target=_play, daemon=True).start()
