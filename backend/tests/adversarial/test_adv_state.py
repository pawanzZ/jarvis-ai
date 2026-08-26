import asyncio
import pytest
from jarvis.core.state import StateMachine, JarvisState, TRANSITIONS


@pytest.mark.asyncio
async def test_all_state_transition_matrix():
    """Verify all valid and invalid transitions across the 5x5 state matrix."""
    all_states = list(JarvisState)
    for initial in all_states:
        for target in all_states:
            sm = StateMachine()
            sm._state = initial
            expected_valid = target in TRANSITIONS.get(initial, set())
            result = await sm.transition(target)
            assert result is expected_valid, f"Transition {initial} -> {target} returned {result}, expected {expected_valid}"
            if expected_valid:
                assert sm.state == target
            else:
                assert sm.state == initial


@pytest.mark.asyncio
async def test_concurrent_conflicting_transitions():
    """Stress test: Multiple concurrent coroutines attempting different transitions from IDLE."""
    sm = StateMachine()
    results = []

    async def attempt_transition(target_state: JarvisState):
        res = await sm.transition(target_state)
        results.append((target_state, res))

    # IDLE can transition to LISTENING or ERROR. IDLE -> THINKING or SPEAKING is invalid.
    await asyncio.gather(
        attempt_transition(JarvisState.LISTENING),
        attempt_transition(JarvisState.ERROR),
        attempt_transition(JarvisState.THINKING),
        attempt_transition(JarvisState.SPEAKING),
    )

    # Exactly one valid transition should succeed initially or machine remains in valid state
    assert sm.state in [JarvisState.LISTENING, JarvisState.ERROR, JarvisState.IDLE]
