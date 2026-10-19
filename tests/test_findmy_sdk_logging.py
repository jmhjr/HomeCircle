"""Dependency logging isolation uses no filesystem discovery or owner data."""

import importlib.util
import logging
import os
from pathlib import Path

import pytest

from custom_components.homecircle.findmy_setup import sdk


VENDOR = "custom_components.homecircle._vendor_findmy"
CANARY = "SYNTHETIC_PRIVATE_DEPENDENCY_LOG_MUST_NOT_ESCAPE"


@pytest.fixture(autouse=True)
def restore_logging():
    """Keep the synthetic handler/level controls local to these tests."""
    existing = {
        name: (
            logger,
            list(logger.handlers),
            logger.propagate,
            logger.disabled,
            logger.level,
        )
        for name, logger in logging.Logger.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    yield
    for name, logger in tuple(logging.Logger.manager.loggerDict.items()):
        if not isinstance(logger, logging.Logger):
            continue
        if name in existing:
            _, handlers, propagate, disabled, level = existing[name]
        else:
            handlers, propagate, disabled, level = [], True, False, logging.NOTSET
        logger.handlers[:] = handlers
        logger.propagate, logger.disabled = propagate, disabled
        logger.setLevel(level)


async def test_sdk_on_event_loop_never_discovers_module_files(monkeypatch):
    sdk()  # Actual package imports are already resolved before the tripwires.

    def refused(*args, **kwargs):
        pytest.fail("sdk must not discover dependency files on HA's event loop")

    monkeypatch.setattr(Path, "rglob", refused)
    monkeypatch.setattr(os, "scandir", refused)
    monkeypatch.setattr(importlib.util, "find_spec", refused)
    account, provider, states, client = sdk()
    assert account.__module__ == VENDOR + ".reports.account"
    assert provider.__module__ == VENDOR + ".reports.anisette"
    assert states.__module__ == VENDOR + ".reports.state"
    assert client.__module__ == VENDOR + ".icloud"


@pytest.mark.parametrize("namespace", [VENDOR, "anisette"])
def test_existing_direct_handlers_and_future_descendants_cannot_leak(
    namespace, caplog, capsys
):
    existing = logging.getLogger(namespace + ".synthetic_existing.deep")
    existing.disabled = False
    existing.setLevel(logging.DEBUG)
    existing.addHandler(logging.StreamHandler())
    with caplog.at_level(logging.DEBUG):
        sdk()
        boundary = logging.getLogger(namespace)
        assert boundary.disabled and boundary.propagate is False
        assert all(
            isinstance(handler, logging.NullHandler) for handler in boundary.handlers
        )
        assert existing.disabled
        assert all(
            isinstance(handler, logging.NullHandler) for handler in existing.handlers
        )
        existing.error(CANARY)

        # A parent disabled flag alone would not stop this child from propagating.
        future = logging.getLogger(namespace + ".synthetic_future.explicit_level")
        future.setLevel(logging.DEBUG)
        assert future.disabled is False
        future.debug(CANARY)
        future.critical(CANARY)

        # Dependency modules do not install handlers, but inherited levels also
        # protect a newly created child with a direct default-level handler.
        direct = logging.getLogger(namespace + ".synthetic_future.direct_handler")
        direct.addHandler(logging.StreamHandler())
        assert not direct.isEnabledFor(logging.DEBUG)
        direct.debug(CANARY)
        logging.getLogger("custom_components.homecircle.findmy_setup").warning(
            "safe synthetic setup status"
        )
    assert "safe synthetic setup status" in caplog.text
    assert CANARY not in caplog.text
    assert CANARY not in capsys.readouterr().err


def test_sdk_does_not_suppress_other_integration_namespaces(caplog):
    unaffected = [
        logging.getLogger("findmy.synthetic_other_integration"),
        logging.getLogger("anisette_extra.synthetic_other_dependency"),
        logging.getLogger(VENDOR + "_extra.synthetic_other_dependency"),
    ]
    for logger in unaffected:
        logger.disabled, logger.propagate = False, True
        logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG):
        sdk()
        for index, logger in enumerate(unaffected):
            logger.debug("safe unrelated namespace %s", index)
    assert all(
        "safe unrelated namespace " + str(index) in caplog.text for index in range(3)
    )
