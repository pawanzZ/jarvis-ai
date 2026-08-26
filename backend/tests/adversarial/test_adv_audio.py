from __future__ import annotations
import asyncio
import math
import pytest
from jarvis.audio.mic_stream import MicStream
from jarvis.audio.speaker_output import SpeakerOutput
from jarvis.audio.vad import VAD


def test_vad_corrupted_and_extreme_inputs():
    vad = VAD(threshold=0.1)

    # Empty and None
    assert vad.calculate_energy(None) == 0.0
    assert vad.calculate_energy([]) == 0.0
    assert vad.calculate_energy(b"") == 0.0
    assert vad.calculate_energy("invalid_string") == 0.0

    # Extremely large buffer (100,000 samples)
    large_buffer = [0.05] * 100000
    energy = vad.calculate_energy(large_buffer)
    assert 0.049 <= energy <= 0.051

    # Mixed invalid items in list
    mixed = [0.1, "bad", None, 0.2]
    e_mixed = vad.calculate_energy(mixed)
    assert e_mixed >= 0.0


@pytest.mark.asyncio
async def test_mic_stream_rapid_start_stop_cycles():
    mic = MicStream(sample_rate=16000, chunk_size=256, simulate=True)
    for _ in range(10):
        await mic.start()
        assert mic.is_recording is True
        await asyncio.sleep(0.005)
        await mic.stop()
        assert mic.is_recording is False


@pytest.mark.asyncio
async def test_speaker_concurrent_play_calls():
    spk = SpeakerOutput(sample_rate=24000, simulate=True)
    audio1 = [0.1] * 2400  # 0.1s
    audio2 = [0.2] * 2400  # 0.1s

    # Launch two plays concurrently - second should supersede first cleanly
    t1 = asyncio.create_task(spk.play(audio1))
    await asyncio.sleep(0.01)
    t2 = asyncio.create_task(spk.play(audio2))

    await asyncio.gather(t1, t2)
    assert spk.is_playing is False


@pytest.mark.asyncio
async def test_mic_stream_queue_overflow_resilience():
    mic = MicStream(sample_rate=16000, chunk_size=128, simulate=True)
    await mic.start()

    # Feed 200 chunks into a 100-maxsize queue rapidly
    for i in range(200):
        await mic.feed_chunk([float(i % 10) * 0.1] * 128)

    # Read chunks out without error
    chunk = await mic.read_chunk(timeout=0.2)
    assert len(chunk) == 128
    await mic.stop()
