"""Reported addresses remain tied to exact selected map evidence."""

from types import SimpleNamespace

from homeassistant.core import State

from custom_components.homecircle.api import reported_address


def scenario():
    # Fictional text; no actual address or coordinate is used.
    source = "device_tracker.example_phone"
    member = SimpleNamespace(
        id="person.example_member",
        place=None,
        focusable=True,
        location=SimpleNamespace(evidence=SimpleNamespace(source_entity=source)),
    )
    runtime = SimpleNamespace(
        config={"members": {member.id: {"trackers": [source]}}},
        states={
            source: State(
                source, "not_home", {"address": "Example street, Example city"}
            )
        },
    )
    return member, runtime, source


def test_address_uses_exact_selected_source_and_named_places_win():
    member, runtime, source = scenario()
    assert reported_address(member, runtime) == "Example street, Example city"
    member.place = "zone.example_work"
    assert reported_address(member, runtime) is None
    member.place = None
    member.location.evidence.source_entity = "device_tracker.example_other"
    runtime.states["device_tracker.example_other"] = runtime.states[source]
    assert reported_address(member, runtime) is None
    member.location.evidence.source_entity = source
    member.focusable = False
    assert reported_address(member, runtime) is None
    member.focusable = True
    member.location = None
    assert reported_address(member, runtime) is None


def test_address_rejects_missing_unavailable_and_malformed_values():
    member, runtime, source = scenario()
    for value in [
        None,
        {},
        [],
        "",
        " unknown ",
        "unavailable",
        "null",
        "none",
        "x" * 241,
        "Example\x00street",
    ]:
        runtime.states[source] = State(source, "not_home", {"address": value})
        assert reported_address(member, runtime) is None
    runtime.states[source] = State(source, "unavailable", {"address": "Example street"})
    assert reported_address(member, runtime) is None
    runtime.states[source] = State(
        source, "not_home", {"address": "Example street\n  Example city"}
    )
    assert reported_address(member, runtime) == "Example street Example city"
    runtime.states[source] = None
    assert reported_address(member, runtime) is None
