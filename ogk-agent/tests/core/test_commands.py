import pytest

from service.core.commands import CommandState

pytestmark = pytest.mark.anyio


async def test_same_command_from_multiple_transports_runs_once():
    state = CommandState()
    seen = []

    async def handler(command):
        seen.append(command["id"])

    state.set_handler(handler)
    command = {"id": 4, "child_id": 7, "type": "add_time", "minutes": 15}
    assert await state.process(command)
    assert await state.process(command)
    assert seen == [4]


async def test_invalid_command_id_is_not_acknowledged():
    state = CommandState()
    assert not await state.process({"id": "4"})
