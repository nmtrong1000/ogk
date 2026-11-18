import re

import pytest

from app.modules.enrollment.service import CODE_ALPHABET, normalize_code
from tests.conftest import csrf_headers
from tests.enrollment.conftest import create_code, enroll

pytestmark = pytest.mark.anyio


async def test_code_has_eight_characters_and_ten_minutes(parent, clock):
    response = await create_code(parent)
    assert response.status_code == 201
    body = response.json()
    assert re.fullmatch(rf"[{CODE_ALPHABET}]{{4}}-[{CODE_ALPHABET}]{{4}}", body["code"])
    from datetime import datetime

    expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    assert (expires - clock.at).total_seconds() == 600
    assert body["expires_in"] == 600


async def test_consent_is_required(parent):
    response = await create_code(parent, consent=False)
    assert response.status_code == 422
    assert response.json() == {"detail": "consent_required"}


async def test_enroll_with_code(parent, agent):
    code = (await create_code(parent)).json()["code"]
    assert (await enroll(agent, code)).status_code == 201


async def test_used_code_is_rejected(parent, agent):
    code = (await create_code(parent)).json()["code"]
    assert (await enroll(agent, code)).status_code == 201
    response = await enroll(agent, code)
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid_code"}


async def test_expired_code_is_rejected(parent, agent, clock):
    code = (await create_code(parent)).json()["code"]
    clock.advance(minutes=10)
    response = await enroll(agent, code)
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid_code"}


async def test_code_just_before_expiry_works(parent, agent, clock):
    code = (await create_code(parent)).json()["code"]
    clock.advance(minutes=9, seconds=59)
    assert (await enroll(agent, code)).status_code == 201


async def test_unknown_code_is_rejected(agent):
    response = await enroll(agent, "0000-0000")
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid_code"}


async def test_new_code_replaces_unused_code(parent, agent):
    first = (await create_code(parent)).json()
    await create_code(parent)
    assert (await enroll(agent, first["code"])).status_code == 400
    assert (await parent.get(f"/api/pairing-codes/{first['id']}")).status_code == 404


async def test_code_input_is_normalised(parent, agent):
    code = (await create_code(parent)).json()["code"]
    typed = code.lower().replace("-", " ").replace("0", "o").replace("1", "l")
    assert (await enroll(agent, typed)).status_code == 201


def test_normalize_code():
    assert normalize_code("abcd-ef0l") == "ABCDEF01"
    assert normalize_code(" O1I L ") == "0111"


async def test_status_moves_from_pending_to_used(parent, agent):
    created = (await create_code(parent)).json()
    status = (await parent.get(f"/api/pairing-codes/{created['id']}")).json()
    assert status["status"] == "pending"
    assert status["device_id"] is None
    tokens = (await enroll(agent, created["code"])).json()
    status = (await parent.get(f"/api/pairing-codes/{created['id']}")).json()
    assert status["status"] == "used"
    assert status["device_id"] == tokens["device_id"]


async def test_status_expired(parent, clock):
    created = (await create_code(parent)).json()
    clock.advance(minutes=11)
    assert (await parent.get(f"/api/pairing-codes/{created['id']}")).json()["status"] == "expired"


async def test_other_parent_cannot_see_code(parent, other_parent):
    created = (await create_code(parent)).json()
    assert (await other_parent.get(f"/api/pairing-codes/{created['id']}")).status_code == 404


async def test_admin_cannot_create_code(admin):
    response = await admin.post("/api/pairing-codes", json={"consent": True}, headers=await csrf_headers(admin))
    assert response.status_code == 403


async def test_create_code_needs_csrf(parent):
    assert (await parent.post("/api/pairing-codes", json={"consent": True})).status_code == 403


async def test_enroll_rate_limited(agent):
    for _ in range(10):
        await enroll(agent, "0000-0000")
    assert (await enroll(agent, "0000-0000")).status_code == 429
