from peis.core.stop_states import (
    StopState,
    is_terminal_state,
    is_halt_state,
    can_progress,
)


def test_stop_state_properties():
    assert is_terminal_state(StopState.RESOLVED)
    assert is_halt_state(StopState.HALT_CONFLICT)
    assert can_progress(StopState.RESOLVED)
    assert not can_progress(StopState.UNKNOWN)