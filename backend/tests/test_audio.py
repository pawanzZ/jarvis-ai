from __future__ import annotations
import asyncio
import math
import struct
import pytest
from jarvis.audio.mic_stream import MicStream
from jarvis.audio.speaker_output import SpeakerOutput
from jarvis.audio.vad import VAD


# --- VAD Tests ---

def test_vad_initialization():
    vad = VAD(threshold=0.05, sample_rate=16000, frame_size=512, hangover_frames=8, min_speech_frames=3)
    assert vad.threshold == 0.05
    assert vad.sample_rate == 16000
    assert vad.frame_size == 512
    assert vad.hangover_frames == 8
    assert vad.min_speech_frames == 3
    assert vad.in_speech is False


def test_vad_calculate_energy_silence():
    vad = VAD(threshold=0.02)
    assert vad.calculate_energy([]) == 0.0
    assert vad.calculate_energy(None) == 0.0
    assert vad.calculate_energy([0.0] * 512) == 0.0
    assert vad.calculate_energy(b"\x00" * 1024) == 0.0


def test_vad_calculate_energy_float_samples():
    vad = VAD(threshold=0.02)
    samples = [0.5, -0.5, 0.5, -0.5]
    energy = vad.calculate_energy(samples)
    assert 0.49 <= energy <= 0.51


def test_vad_calculate_energy_pcm_bytes():
    vad = VAD(threshold=0.02)
    # 16-bit integer PCM half scale: 16384 -> ~0.5 float
    raw_bytes = struct.pack("<4h", 16384, -16384, 16384, -16384)
    energy = vad.calculate_energy(raw_bytes)
    assert 0.49 <= energy <= 0.51


def test_vad_is_speech_detection():
    vad = VAD(threshold=0.1)
    silence = [0.001] * 512
    speech = [0.5] * 512
    assert vad.is_speech(silence) is False
    assert vad.is_speech(speech) is True


def test_vad_process_frame_state_transitions():
    vad = VAD(threshold=0.1, min_speech_frames=2, hangover_frames=3)
    silence = [0.0] * 512
    voiced = [0.4] * 512

    # Frame 1: Voiced 1/2 -> not yet in speech
    res1 = vad.process_frame(voiced)
    assert res1["is_speech"] is True
    assert res1["in_speech"] is False
    assert res1["speech_started"] is False

    # Frame 2: Voiced 2/2 -> enters speech!
    res2 = vad.process_frame(voiced)
    assert res2["in_speech"] is True
    assert res2["speech_started"] is True

    # Frame 3: Sustained voiced
    res3 = vad.process_frame(voiced)
    assert res3["in_speech"] is True
    assert res3["speech_started"] is False

    # Frame 4: Silence 1/3 (hangover)
    res4 = vad.process_frame(silence)
    assert res4["is_speech"] is False
    assert res4["in_speech"] is True
    assert res4["speech_ended"] is False

    # Frame 5: Silence 2/3
    res5 = vad.process_frame(silence)
    assert res5["in_speech"] is True

    # Frame 6: Silence 3/3 -> speech ended!
    res6 = vad.process_frame(silence)
    assert res6["in_speech"] is False
    assert res6["speech_ended"] is True

    # Frame 7: Continuous silence
    res7 = vad.process_frame(silence)
    assert res7["in_speech"] is False
    assert res7["speech_ended"] is False


def test_vad_reset():
    vad = VAD(threshold=0.1, min_speech_frames=1)
    vad.process_frame([0.5] * 512)
    assert vad.in_speech is True
    vad.reset()
    assert vad.in_speech is False


# --- MicStream Tests ---

@pytest.mark.asyncio
async def test_mic_stream_lifecycle():
    mic = MicStream(sample_rate=16000, chunk_size=512, simulate=True)
    assert mic.is_recording is False
    assert mic.get_is_recording() is False

    await mic.start()
    assert mic.is_recording is True
    assert mic.get_is_recording() is True

    await mic.stop()
    assert mic.is_recording is False


@pytest.mark.asyncio
async def test_mic_stream_read_and_feed_chunk():
    mic = MicStream(sample_rate=16000, chunk_size=4, simulate=True)
    await mic.start()

    custom_chunk = [0.1, 0.2, 0.3, 0.4]
    await mic.feed_chunk(custom_chunk)

    chunk = await mic.read_chunk(timeout=1.0)
    assert len(chunk) == 4
    assert chunk == custom_chunk

    await mic.stop()


@pytest.mark.asyncio
async def test_mic_stream_simulation_chunks():
    mic = MicStream(sample_rate=16000, chunk_size=128, simulate=True)
    await mic.start()

    # Read simulated chunk
    chunk = await mic.read_chunk(timeout=0.5)
    assert len(chunk) == 128
    assert isinstance(chunk, list)

    await mic.stop()


@pytest.mark.asyncio
async def test_mic_stream_async_iterator():
    mic = MicStream(sample_rate=16000, chunk_size=64, simulate=True)
    await mic.start()

    collected = []
    async for chunk in mic.chunks():
        collected.append(chunk)
        if len(collected) >= 3:
            break

    assert len(collected) == 3
    assert len(collected[0]) == 64
    await mic.stop()


# --- SpeakerOutput Tests ---

def test_speaker_volume_control():
    spk = SpeakerOutput(sample_rate=24000, volume=0.8, simulate=True)
    assert spk.volume == 0.8
    assert spk.get_volume() == 0.8

    spk.volume = 1.5
    assert spk.volume == 1.0  # Clamped

    spk.set_volume(-0.5)
    assert spk.volume == 0.0  # Clamped

    spk.set_volume(0.65)
    assert math.isclose(spk.volume, 0.65)


@pytest.mark.asyncio
async def test_speaker_play_and_stop():
    spk = SpeakerOutput(sample_rate=24000, simulate=True)
    assert spk.is_playing is False

    # 480 samples at 24000Hz = 0.02s
    audio = [0.1] * 480
    await spk.play(audio)
    assert spk.is_playing is False


@pytest.mark.asyncio
async def test_speaker_interruption():
    spk = SpeakerOutput(sample_rate=24000, simulate=True)
    # Long audio (24000 samples = 1s)
    long_audio = [0.1] * 24000

    play_task = asyncio.create_task(spk.play(long_audio))
    await asyncio.sleep(0.05)
    assert spk.is_playing is True

    spk.stop()
    await play_task
    assert spk.is_playing is False
