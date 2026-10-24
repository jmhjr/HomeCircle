"""Actual pure-Python SRP proofs stay isolated across synthetic awaited flows."""

import asyncio
import importlib.metadata
from pathlib import Path
import socket
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest
import srp as selected_srp
import srp._pysrp as shared_srp

from custom_components.homecircle._vendor_findmy.keychain import recovery
from custom_components.homecircle._vendor_findmy.reports import account
from custom_components.homecircle._vendor_findmy.util import srp as isolated

SALT = b"fixture-srp-salt"
SERVER_PUBLIC = b"\2"
GSA_IDENTITY = "example@example.invalid"
GSA_PASSWORD = "fixture-password-canary"
GSA_SECRET = b"\1" * 256
RECOVERY_IDENTITY = b"fixture-dsid"
RECOVERY_PASSWORD = "fixture-passcode-canary"
RECOVERY_SECRET = (b"\3" * 32).rjust(256, b"\0")


class ProofCaptured(Exception):
    """Stop the synthetic exchange before any server reply needs to be trusted."""


class SyntheticFailure(Exception):
    """Fixed local transport failure, never an Apple response."""


@pytest.fixture(autouse=True)
def original_flags_and_no_network(monkeypatch):
    initial = shared_srp._rfc5054_compat, shared_srp._no_username_in_x

    def forbidden(*args, **kwargs):
        raise AssertionError("a synthetic SRP test attempted a real socket")

    monkeypatch.setattr(socket, "socket", forbidden)
    try:
        yield
    finally:
        shared_srp.rfc5054_enable(initial[0])
        shared_srp.no_username_in_x(initial[1])


def reference(identity, password, secret, *, omit_username, rfc5054=True):
    """Use the unmodified installed implementation, sequentially and only in RAM."""
    before = shared_srp._rfc5054_compat, shared_srp._no_username_in_x
    try:
        shared_srp.rfc5054_enable(rfc5054)
        shared_srp.no_username_in_x(omit_username)
        user = shared_srp.User(identity, password, hash_alg=shared_srp.SHA256,
                               ng_type=shared_srp.NG_2048, bytes_a=secret)
        proof = user.process_challenge(SALT, SERVER_PUBLIC)
        assert proof is not None
        return proof
    finally:
        shared_srp.rfc5054_enable(before[0])
        shared_srp.no_username_in_x(before[1])


@pytest.fixture
def actual_srp(monkeypatch):
    original_user = isolated.gsa.User

    def deterministic_user(*args, **kwargs):
        kwargs.setdefault("bytes_a", GSA_SECRET)
        return original_user(*args, **kwargs)

    monkeypatch.setattr(account.srp, "User", deterministic_user)
    monkeypatch.setattr(recovery.secrets, "token_bytes", lambda count: b"\3" * count)
    monkeypatch.setattr(recovery, "parse_challenge", lambda *args: SimpleNamespace(
        dsid=RECOVERY_IDENTITY, salt=SALT, server_public=SERVER_PUBLIC,
    ))
    monkeypatch.setattr(recovery, "build_recovery_proof", lambda challenge, proof: proof)


async def entered(event):
    await asyncio.wait_for(event.wait(), 5)


async def finished(task):
    with pytest.raises(ProofCaptured):
        await asyncio.wait_for(task, 5)


class RecoveryProxy:
    def __init__(self):
        self.init_entered, self.init_release = asyncio.Event(), asyncio.Event()
        self.recover_entered, self.recover_release = asyncio.Event(), asyncio.Event()
        self.proof = None
        self.failure = None

    async def srp_init(self, *args):
        self.init_entered.set()
        await self.init_release.wait()
        if self.failure == "init":
            raise SyntheticFailure
        return None

    async def recover(self, label, proof, transaction_id, **kwargs):
        self.proof = proof
        self.recover_entered.set()
        await self.recover_release.wait()
        if self.failure == "recover":
            raise SyntheticFailure
        raise ProofCaptured

    def start(self):
        record = SimpleNamespace(is_recovery_candidate=True, label="Example recovery record")
        return asyncio.create_task(recovery.recover_bottled_peer(self, record, RECOVERY_PASSWORD))


class GsaRequest:
    def __init__(self):
        self.init_entered, self.init_release = asyncio.Event(), asyncio.Event()
        self.proof = None

    async def __call__(self, packet):
        if packet["o"] == "init":
            self.init_entered.set()
            await self.init_release.wait()
            return {"Status": {"ec": 0}, "sp": "s2k", "s": SALT,
                    "B": SERVER_PUBLIC, "i": 1, "c": "fixture-challenge"}
        assert packet["o"] == "complete"
        self.proof = packet["M1"]
        raise ProofCaptured

    def start(self):
        client = account.AsyncAppleAccount.__new__(account.AsyncAppleAccount)
        client._username, client._password = GSA_IDENTITY, GSA_PASSWORD
        client._endpoint_policy = account.EndpointPolicy(account.MAC_POLICY_ID)
        client._login_state = account.LoginState.LOGGED_OUT
        client._gsa_request = self
        return asyncio.create_task(client._gsa_authenticate())


def assert_modes_and_shared_flags(expected):
    assert (shared_srp._rfc5054_compat, shared_srp._no_username_in_x) == expected
    assert isolated.gsa._rfc5054_compat is isolated.recovery._rfc5054_compat is True
    assert isolated.gsa._no_username_in_x is True
    assert isolated.recovery._no_username_in_x is False


def assert_required_proof(proof, identity, password, secret, *, omit_username):
    matches = proof == reference(identity, password, secret, omit_username=omit_username)
    matches_other_mode = proof == reference(identity, password, secret, omit_username=not omit_username)
    matches_unpadded = proof == reference(identity, password, secret,
                                         omit_username=omit_username, rfc5054=False)
    assert matches, "actual SDK proof differs from its required mode"
    assert not matches_other_mode, "synthetic control did not distinguish username modes"
    assert not matches_unpadded, "synthetic control did not distinguish RFC5054 modes"


def test_namespaces_use_installed_purepython_code_without_backend_selector(monkeypatch):
    assert importlib.metadata.version("srp") == "1.0.22"
    monkeypatch.setattr(selected_srp, "_mod", SimpleNamespace(User=object()))
    assert account.srp is isolated.gsa and recovery.srp is isolated.recovery
    assert isolated.gsa is not isolated.recovery
    for backend in (isolated.gsa, isolated.recovery):
        assert backend is not shared_srp
        assert Path(backend.__file__).resolve() == Path(shared_srp.__file__).resolve()
        assert backend.User.__init__.__globals__ is vars(backend)
        assert backend.User.process_challenge.__globals__ is vars(backend)
        assert backend.gen_x.__globals__ is vars(backend)
        assert backend.User.process_challenge.__code__.co_code == shared_srp.User.process_challenge.__code__.co_code
        assert backend.User.__init__.__code__.co_code == shared_srp.User.__init__.__code__.co_code


@pytest.mark.parametrize("initial", [(False, False), (False, True), (True, False), (True, True)])
async def test_actual_gsa_and_recovery_proofs_overlap_with_poisoned_shared_flags(actual_srp, caplog, initial):
    shared_srp.rfc5054_enable(initial[0])
    shared_srp.no_username_in_x(initial[1])
    gsa, proxy = GsaRequest(), RecoveryProxy()
    gsa_task = gsa.start()
    await entered(gsa.init_entered)
    recovery_task = proxy.start()
    try:
        await entered(proxy.init_entered)
        assert_modes_and_shared_flags(initial)
        gsa.init_release.set()
        await finished(gsa_task)
        assert_modes_and_shared_flags(initial)
        proxy.init_release.set()
        await entered(proxy.recover_entered)
        proxy.recover_release.set()
        await finished(recovery_task)
        encrypted = account.util.crypto.encrypt_password(GSA_PASSWORD, SALT, 1, "s2k")
        assert_required_proof(gsa.proof, GSA_IDENTITY, encrypted, GSA_SECRET, omit_username=True)
        assert_required_proof(proxy.proof, RECOVERY_IDENTITY, RECOVERY_PASSWORD,
                              RECOVERY_SECRET, omit_username=False)
        assert_modes_and_shared_flags(initial)
    finally:
        for task in (gsa_task, recovery_task):
            task.cancel()
        await asyncio.gather(gsa_task, recovery_task, return_exceptions=True)
    for sensitive in (GSA_PASSWORD, RECOVERY_PASSWORD, GSA_IDENTITY, RECOVERY_IDENTITY.decode()):
        assert sensitive not in caplog.text


async def test_two_recoveries_finish_in_entry_order_without_changing_modes(actual_srp):
    before = shared_srp._rfc5054_compat, shared_srp._no_username_in_x
    first, second = RecoveryProxy(), RecoveryProxy()
    first_task = first.start()
    await entered(first.init_entered)
    second_task = second.start()
    try:
        await entered(second.init_entered)
        first.init_release.set()
        await entered(first.recover_entered)
        first.recover_release.set()
        await finished(first_task)
        assert_modes_and_shared_flags(before)
        second.init_release.set()
        await entered(second.recover_entered)
        second.recover_release.set()
        await finished(second_task)
        for proxy in (first, second):
            assert_required_proof(proxy.proof, RECOVERY_IDENTITY, RECOVERY_PASSWORD,
                                  RECOVERY_SECRET, omit_username=False)
        assert_modes_and_shared_flags(before)
    finally:
        for task in (first_task, second_task):
            task.cancel()
        await asyncio.gather(first_task, second_task, return_exceptions=True)


@pytest.mark.parametrize("phase", ["init", "recover"])
@pytest.mark.parametrize("interruption", ["cancel", "failure"])
async def test_cancel_or_failure_does_not_poison_other_recovery(actual_srp, phase, interruption):
    before = shared_srp._rfc5054_compat, shared_srp._no_username_in_x
    interrupted, survivor = RecoveryProxy(), RecoveryProxy()
    interrupted_task = interrupted.start()
    await entered(interrupted.init_entered)
    survivor_task = survivor.start()
    try:
        await entered(survivor.init_entered)
        if phase == "recover":
            interrupted.init_release.set()
            await entered(interrupted.recover_entered)
        if interruption == "cancel":
            interrupted_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await interrupted_task
        else:
            interrupted.failure = phase
            getattr(interrupted, phase + "_release").set()
            with pytest.raises(SyntheticFailure):
                await asyncio.wait_for(interrupted_task, 5)
        assert_modes_and_shared_flags(before)
        survivor.init_release.set()
        await entered(survivor.recover_entered)
        survivor.recover_release.set()
        await finished(survivor_task)
        assert_required_proof(survivor.proof, RECOVERY_IDENTITY, RECOVERY_PASSWORD,
                              RECOVERY_SECRET, omit_username=False)
        assert_modes_and_shared_flags(before)
    finally:
        for task in (interrupted_task, survivor_task):
            task.cancel()
        await asyncio.gather(interrupted_task, survivor_task, return_exceptions=True)


def test_another_thread_can_change_shared_flags_during_private_challenge(monkeypatch):
    at_challenge, changed = threading.Event(), threading.Event()
    original_gen_x = isolated.gsa.gen_x

    def external_caller():
        assert at_challenge.wait(5)
        shared_srp.rfc5054_enable(False)
        shared_srp.no_username_in_x(False)
        changed.set()

    def gated_gen_x(*args):
        at_challenge.set()
        assert changed.wait(5)
        return original_gen_x(*args)

    monkeypatch.setattr(isolated.gsa, "gen_x", gated_gen_x)
    thread = threading.Thread(target=external_caller)
    thread.start()
    try:
        user = isolated.gsa.User(GSA_IDENTITY, GSA_PASSWORD, hash_alg=isolated.gsa.SHA256,
                                 ng_type=isolated.gsa.NG_2048, bytes_a=GSA_SECRET)
        proof = user.process_challenge(SALT, SERVER_PUBLIC)
        assert_required_proof(proof, GSA_IDENTITY, GSA_PASSWORD, GSA_SECRET, omit_username=True)
        assert_modes_and_shared_flags((False, False))
    finally:
        at_challenge.set()
        thread.join(5)
        assert not thread.is_alive()


def test_fresh_import_preserves_ordinary_module_flags_for_all_modes():
    script = """
import srp._pysrp as shared
import srp as selected
import sys
selected._mod = object()
shared.rfc5054_enable(sys.argv[1] == '1')
shared.no_username_in_x(sys.argv[2] == '1')
before = shared._rfc5054_compat, shared._no_username_in_x
from custom_components.homecircle._vendor_findmy.reports import account
from custom_components.homecircle._vendor_findmy.keychain import recovery
assert (shared._rfc5054_compat, shared._no_username_in_x) == before
assert account.srp is not shared and recovery.srp is not shared
assert account.srp is not recovery.srp
"""
    for rfc5054, omit_username in (("0", "0"), ("0", "1"), ("1", "0"), ("1", "1")):
        result = subprocess.run([sys.executable, "-B", "-c", script, rfc5054, omit_username],
                                capture_output=True, timeout=15)
        assert result.returncode == 0, "fresh SRP import mutated ordinary module modes"
