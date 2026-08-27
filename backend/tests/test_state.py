import pytest
from jarvis.core.state import StateMachine, JarvisState


@pytest.mark.asyncio
async def test_initial_state():
    sm = StateMachine()
    assert sm.state == JarvisState.IDLE


@pytest.mark.asyncio
async def test_valid_transition():
    sm = StateMachine()
    result = await sm.transition(JarvisState.LISTENING)
    assert result is True
    assert sm.state == JarvisState.LISTENING


@pytest.mark.asyncio
async def test_invalid_transition():
    sm = StateMachine()
    result = await sm.transition(JarvisState.SPEAKING)
    assert result is False
    assert sm.state == JarvisState.IDLE


@pytest.mark.asyncio
async def test_on_change_callback():
    sm = StateMachine()
    changes = []

    async def callback(old, new):
        changes.append((old, new))

    sm.on_change(callback)
    await sm.transition(JarvisState.LISTENING)
    assert len(changes) == 1
    assert changes[0] == (JarvisState.IDLE, JarvisState.LISTENING)


@pytest.mark.asyncio
async def test_thinking_to_listening_barge_in():
    """Barge-in during reasoning is allowed (THINKING -> LISTENING)."""
    sm = StateMachine()
    sm._state = JarvisState.THINKING
    result = await sm.transition(JarvisState.LISTENING)
    assert result is True
    assert sm.state == JarvisState.LISTENING


@pytest.mark.asyncio
async def test_speaking_to_listening_barge_in():
    """Interrupting Jarvis mid-speech is allowed (SPEAKING -> LISTENING)."""
    sm = StateMachine()
    sm._state = JarvisState.SPEAKING
    result = await sm.transition(JarvisState.LISTENING)
    assert result is True
    assert sm.state == JarvisState.LISTENING
