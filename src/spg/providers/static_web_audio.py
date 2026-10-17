"""Bounded format observations, never a claim of playback or musical quality."""
from io import BytesIO
import wave


def audio_observation(body, suffix):
    if suffix == ".wav":
        try:
            with wave.open(BytesIO(body), "rb") as audio:
                frames, channels, width = audio.getnframes(), audio.getnchannels(), audio.getsampwidth()
                if not frames or len(audio.readframes(frames)) != frames * channels * width:
                    raise ValueError("PROTECTED_CONTEXT_AUDIO_INVALID")
                return {"format": "PCM_WAVE", "sample_rate": audio.getframerate(),
                    "channels": channels, "sample_width": width, "frames": frames}
        except (wave.Error, EOFError) as error:
            raise ValueError("PROTECTED_CONTEXT_AUDIO_INVALID") from error
    if suffix != ".mp3":
        raise ValueError("PROTECTED_CONTEXT_AUDIO_UNSUPPORTED")
    offset = 0
    if body.startswith(b"ID3"):
        if len(body) < 10 or any(b & 128 for b in body[6:10]):
            raise ValueError("PROTECTED_CONTEXT_AUDIO_INVALID")
        offset = 10 + sum(b << shift for b, shift in zip(body[6:10], (21, 14, 7, 0)))
        if body[5] & 16:  # ID3v2 footer
            offset += 10
    def frame(at):
        if at + 4 > len(body):
            return None
        header = int.from_bytes(body[at:at + 4], "big")
        version, layer = (header >> 19) & 3, (header >> 17) & 3
        bitrate, rate = (header >> 12) & 15, (header >> 10) & 3
        if header >> 21 != 0x7ff or version == 1 or layer != 1 or bitrate in (0, 15) or rate == 3:
            return None
        rates = (44100, 48000, 32000)
        hz = rates[rate] // (1 if version == 3 else 2 if version == 2 else 4)
        kbps = ((0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
            if version == 3 else (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160))[bitrate]
        size = (144000 if version == 3 else 72000) * kbps // hz + ((header >> 9) & 1)
        if at + size > len(body):
            return None
        return size, hz, 1 if (header >> 6) & 3 == 3 else 2
    # Two consecutive complete frames avoid mistaking an ID3 label, extension,
    # HTML error or a single incidental sync word for an observed audio asset.
    for at in range(offset, min(offset + 4096, len(body))):
        first = frame(at)
        second = frame(at + first[0]) if first else None
        if first and second and first[1:] == second[1:]:
            return {"format": "MPEG_LAYER_III", "sample_rate": first[1],
                "channels": first[2], "observed_consecutive_frames": 2}
    raise ValueError("PROTECTED_CONTEXT_AUDIO_INVALID")
