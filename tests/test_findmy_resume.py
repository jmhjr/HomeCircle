"""Existing report access is reusable without password, recovery or network I/O."""

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from custom_components.homecircle.findmy_resume import (
    has_saved_report_capability,
    prepare_saved_setup,
)
from custom_components.homecircle.findmy_setup import FindMySetupError, sdk


async def saved_data():
    account_type, provider_type, _, _ = sdk()
    from custom_components.homecircle._vendor_findmy import FindMyAccessory

    account = account_type(
        provider_type(), uid="example-local-user", devid="example-device"
    )
    session = account.to_json()
    await account.close()
    session["account"]["username"] = "example@example.invalid"
    session["login"] = {
        "state": 3,
        "data": {
            "dsid": "example-dsid",
            "mobileme_data": {"tokens": {"searchPartyToken": "example-report-token"}},
        },
    }
    accessory = FindMyAccessory(
        master_key=bytes([1]) * 28,
        skn=bytes([2]) * 32,
        sks=bytes([3]) * 32,
        paired_at=datetime(2026, 1, 1, tzinfo=UTC),
        name="Example item",
        identifier="example-accessory",
    )
    items = {
        "saved-item": {
            "accessory": accessory.to_json(),
            "report": {"last_seen": "2026-10-01T12:00:00+00:00"},
        }
    }
    return session, items


async def test_resume_preserves_identity_and_keys_without_auth_or_network(
    monkeypatch, tmp_path
):
    session, items = await saved_data()
    before = deepcopy((session, items))
    account_type, provider_type, _, _ = sdk()
    authenticate = AsyncMock(side_effect=AssertionError("unexpected authentication"))
    initialize = AsyncMock(side_effect=AssertionError("unexpected provisioning"))
    monkeypatch.setattr(account_type, "_gsa_authenticate", authenticate)
    monkeypatch.setattr(provider_type, "_get_ani", initialize)

    setup = prepare_saved_setup(session, items, tmp_path / "unused-libraries")
    try:
        assert setup.account.to_json() == session
        assert setup.account.device_uuid == "example-device"
        assert setup.account.local_user_uuid == "example-local-user"
        assert setup.discover_new is False
        assert setup.client is None
        assert (
            setup.accessories["saved-item"].to_json()
            == items["saved-item"]["accessory"]
        )
        assert setup.item_choices() == [
            {"value": "saved-item", "label": "Example item"}
        ]
        selected_session, selected = setup.selected_payload(["saved-item"])
        assert selected_session == session
        assert selected == items
        setup.previous_items["saved-item"]["report"]["last_seen"] = "changed"
        setup.account._login_state_data["dsid"] = "changed"
        assert (session, items) == before
        authenticate.assert_not_awaited()
        initialize.assert_not_awaited()
        assert not list(tmp_path.iterdir())
    finally:
        await setup.close()
    assert setup.accessories == {} and setup.previous_items == {}


async def test_resume_carries_only_report_grant_and_cannot_open_recovery(tmp_path):
    session, items = await saved_data()
    session["login"]["data"]["adsid"] = "example-auth-principal"
    session["login"]["data"]["mobileme_data"]["tokens"]["cloudKitToken"] = (
        "example-cloud-token"
    )
    before = deepcopy(session)
    setup = prepare_saved_setup(session, items, tmp_path / "unused-libraries")
    try:
        assert set(setup.account.service_tokens) == {"searchPartyToken"}
        assert setup.account.adsid is None
        with pytest.raises(FindMySetupError, match="findmy_saved_session_unavailable"):
            await setup.client_factory(setup.account)
        assert session == before
    finally:
        await setup.close()


@pytest.mark.parametrize(
    "path,value",
    [
        (("account", "password"), "example-password"),
        (("login", "state"), 2),
        (("login", "data", "dsid"), ""),
        (("login", "data", "dsid"), None),
        (("login", "data", "mobileme_data", "tokens", "searchPartyToken"), ""),
        (("login", "data", "mobileme_data", "tokens", "searchPartyToken"), None),
        (("login", "data", "mobileme_data", "tokens"), []),
        (("login", "data"), None),
    ],
)
async def test_missing_report_capability_does_not_fall_back_to_login(
    path, value, tmp_path
):
    session, items = await saved_data()
    target = session
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    before = deepcopy((session, items))
    assert not has_saved_report_capability(session)
    with pytest.raises(FindMySetupError, match="findmy_saved_session_unavailable"):
        prepare_saved_setup(session, items, tmp_path / "unused-libraries")
    assert (session, items) == before


@pytest.mark.parametrize("items", [{}, [], {"saved-item": {}}, {"": {"accessory": {}}}])
async def test_invalid_saved_items_are_refused_without_recovery(items, tmp_path):
    session, _ = await saved_data()
    with pytest.raises(FindMySetupError, match="findmy_saved_session_unavailable"):
        prepare_saved_setup(session, items, tmp_path / "unused-libraries")


@pytest.mark.parametrize(
    "session", [None, [], {}, {"account": None}, {"account": {}, "login": []}]
)
def test_capability_structure_inspection_is_safe_for_invalid_records(session):
    assert not has_saved_report_capability(session)
