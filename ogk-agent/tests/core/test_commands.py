import pytest

from service.core.commands import CommandState

pytestmark = pytest.mark.anyio


async def test_same_command_from_multiple_transports_runs_once():
    state = CommandState()
    seen = []

    async def handler(command):
        seen.append(command["id"])

    state.register(("add_time",), handler)
    command = {"id": 4, "child_id": 7, "type": "add_time", "minutes": 15}
    assert await state.process(command)
    assert await state.process(command)
    assert seen == [4]


async def test_invalid_command_id_is_not_acknowledged():
    state = CommandState()
    assert not await state.process({"id": "4"})


async def test_command_goes_to_handler_of_its_type_and_unknown_type_is_not_acknowledged():
    state = CommandState()
    seen = []

    async def lock(command):
        seen.append(("lock", command["id"]))

    async def purge(command):
        seen.append(("purge", command["id"]))

    state.register(("lock", "unlock"), lock)
    state.register(("purge_child",), purge)
    assert await state.process({"id": 1, "child_id": 7, "type": "purge_child"})
    assert await state.process({"id": 2, "child_id": 7, "type": "unlock"})
    assert not await state.process({"id": 3, "child_id": 7, "type": "erase"})
    assert seen == [("purge", 1), ("lock", 2)]
