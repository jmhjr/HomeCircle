"""Preserve Person identity and explicit tracker links across Core runtimes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.person import DOMAIN as PERSON_DOMAIN
from homeassistant.components.person import entities_in_person
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.homecircle.person_setup import (
    async_create_person,
    async_link_tracker,
    editable_person_collection,
    has_person_entity,
    tracker_link_error,
)


@pytest.fixture(params=[False, True], ids=["legacy-tuple", "person-data"])
def person_runtime(hass, monkeypatch, request):
    """Expose the same fictional entities through each supported runtime shape."""
    item = {
        "id": "synthetic-person-id",
        "device_trackers": ["device_tracker.example_existing"],
    }

    async def update(item_id, changes):
        assert item_id == item["id"]
        item.update(changes)

    collection = SimpleNamespace(
        async_items=Mock(return_value=[item]),
        async_create_item=AsyncMock(return_value={"id": item["id"]}),
        async_update_item=AsyncMock(side_effect=update),
    )
    entities = {
        "person.example_member": SimpleNamespace(
            editable=True, unique_id=item["id"]
        ),
        "person.example_yaml": SimpleNamespace(
            editable=False, unique_id="synthetic-yaml-person-id"
        ),
    }
    component = SimpleNamespace(get_entity=entities.get)
    data = (
        SimpleNamespace(storage_collection=collection, entity_component=component)
        if request.param else (object(), collection, component)
    )
    monkeypatch.setitem(hass.data, PERSON_DOMAIN, data)
    return collection, item


def test_real_person_detection_preserves_yaml_and_ignores_state_only_people(
    hass, person_runtime
):
    collection, item = person_runtime
    hass.states.async_set("person.example_state_only", "home")

    assert has_person_entity(hass, "person.example_member")
    assert has_person_entity(hass, "person.example_yaml")
    assert not has_person_entity(hass, "person.example_state_only")
    assert not has_person_entity(hass, "person.example_missing")
    assert editable_person_collection(hass, "person.example_member") == (
        collection, item["id"]
    )
    assert editable_person_collection(hass, "person.example_yaml") is None
    assert editable_person_collection(hass, "person.example_state_only") is None


async def test_create_person_preserves_registry_collision_and_starts_unlinked(
    hass, person_runtime
):
    collection, item = person_runtime
    registry = er.async_get(hass)
    existing = registry.async_get_or_create(
        PERSON_DOMAIN, PERSON_DOMAIN, "synthetic-existing-person-id",
        suggested_object_id="example_member",
    )
    created = registry.async_get_or_create(
        PERSON_DOMAIN, PERSON_DOMAIN, item["id"],
        suggested_object_id="example_member",
    )

    assert await async_create_person(hass, "  Example Member  ") == created.entity_id

    assert created.entity_id == "person.example_member_2"
    assert registry.async_get(existing.entity_id) == existing
    collection.async_create_item.assert_awaited_once_with(
        {"name": "Example Member", "user_id": None, "device_trackers": []}
    )


async def test_explicit_link_appends_without_losing_or_duplicating_trackers(
    hass, person_runtime
):
    collection, item = person_runtime
    await async_link_tracker(hass, "person.example_member", "device_tracker.example_phone")
    await async_link_tracker(hass, "person.example_member", "device_tracker.example_phone")

    assert item["device_trackers"] == [
        "device_tracker.example_existing", "device_tracker.example_phone"
    ]
    collection.async_update_item.assert_awaited_once_with(
        item["id"], {"device_trackers": item["device_trackers"]}
    )


@pytest.mark.parametrize("person_id", ["person.example_yaml", "person.example_missing"])
async def test_uneditable_and_missing_people_cannot_acquire_links(
    hass, person_runtime, person_id
):
    collection, _ = person_runtime
    assert tracker_link_error(hass, person_id, "device_tracker.example_phone") == (
        "person_not_editable"
    )
    with pytest.raises(ValueError, match="Person is not editable"):
        await async_link_tracker(hass, person_id, "device_tracker.example_phone")
    collection.async_update_item.assert_not_awaited()


def test_tracker_owned_by_another_person_remains_unavailable(hass, person_runtime):
    with patch(
        "custom_components.homecircle.person_setup.persons_with_entity",
        return_value=["person.example_other"],
    ):
        assert tracker_link_error(
            hass, "person.example_member", "device_tracker.example_phone"
        ) == "tracker_linked_elsewhere"


def test_missing_person_runtime_is_unavailable(hass, monkeypatch):
    monkeypatch.delitem(hass.data, PERSON_DOMAIN, raising=False)
    assert not has_person_entity(hass, "person.example_member")
    assert editable_person_collection(hass, "person.example_member") is None


async def test_create_person_uses_real_core_storage_and_registry_collision(hass):
    assert await async_setup_component(hass, PERSON_DOMAIN, {})
    registry = er.async_get(hass)
    existing = registry.async_get_or_create(
        PERSON_DOMAIN, PERSON_DOMAIN, "synthetic-existing-person-id",
        suggested_object_id="example_member",
    )

    person_id = await async_create_person(hass, "  Example Member  ")
    await hass.async_block_till_done()

    assert person_id == "person.example_member_2"
    assert hass.states.get(person_id).name == "Example Member"
    assert has_person_entity(hass, person_id)
    assert editable_person_collection(hass, person_id) is not None
    assert entities_in_person(hass, person_id) == []
    assert registry.async_get(existing.entity_id) == existing

    await async_link_tracker(hass, person_id, "device_tracker.example_existing")
    await async_link_tracker(hass, person_id, "device_tracker.example_phone")
    await async_link_tracker(hass, person_id, "device_tracker.example_phone")
    assert entities_in_person(hass, person_id) == [
        "device_tracker.example_existing", "device_tracker.example_phone"
    ]
