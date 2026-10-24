"""Actual Unicorn guest boundaries using an empty synthetic Mach-O, never Apple code."""
from __future__ import annotations

import builtins
import hashlib
import json
import subprocess
import importlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from unicorn.x86_const import UC_X86_REG_RDI

EMULATOR = Path(__file__).resolve().parents[1] / 'custom_components/homecircle/_findmy_runtime/emulator'
EMPTY_MACHO = struct.pack('<8I', 0xFEEDFACF, 0x1000007, 3, 6, 0, 0, 0, 0)


@pytest.fixture
def modules(monkeypatch):
    # Match the child-only import layout, without retaining path/module changes.
    names = ('macho', 'harness', 'stubs', 'adi_run')
    previous = {name: sys.modules.get(name) for name in names}
    original_path = list(sys.path)
    monkeypatch.syspath_prepend(str(EMULATOR))
    result = SimpleNamespace(**{name: importlib.import_module(name) for name in names})
    try:
        yield result
    finally:
        sys.path[:] = original_path
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


@pytest.fixture
def harness(modules):
    return modules.harness.Harness(modules.harness.MachOImage('synthetic-empty-image', data=EMPTY_MACHO))


@pytest.mark.parametrize('cursor,base,capacity,allocator', [
    ('_scratch_cur', 'SCRATCH_ADDRESS', 'SCRATCH_SIZE', 'scratch'),
    ('_obj_cur', 'OBJECT_ADDRESS', 'OBJECT_SIZE', 'object'),
])
def test_guest_regions_reject_overflow_without_cursor_movement(modules, harness, cursor, base, capacity, allocator):
    module = modules.harness
    begin, size = getattr(module, base), getattr(module, capacity)
    allocate = getattr(harness, allocator)
    assert allocate(size - 16) == begin
    assert allocate(1) == begin + size - 16
    exhausted = getattr(harness, cursor)
    with pytest.raises(module.EmulationError, match='^emulator allocation exhausted$'):
        allocate(1)
    assert getattr(harness, cursor) == exhausted == begin + size


@pytest.mark.parametrize('value', [-1, True, 1.5, '16'])
def test_invalid_allocation_never_mutates_guest_cursors(modules, harness, value):
    before = harness._scratch_cur, harness._obj_cur
    for allocate in (harness.scratch, harness.object):
        with pytest.raises(modules.harness.EmulationError, match='^emulator allocation refused$'):
            allocate(value)
    assert (harness._scratch_cur, harness._obj_cur) == before


def test_malloc_is_bounded_with_existing_zero_size_minimum(modules, harness):
    module = modules.harness
    harness.uc.reg_write(UC_X86_REG_RDI, 0)
    assert harness._malloc(harness) == module.HEAP_ADDRESS
    assert harness._heap_cur == module.HEAP_ADDRESS + 32
    harness.uc.reg_write(UC_X86_REG_RDI, module.HEAP_SIZE - 32)
    assert harness._malloc(harness) == module.HEAP_ADDRESS + 32
    end = harness._heap_cur
    harness.uc.reg_write(UC_X86_REG_RDI, 2**64 - 1)
    with pytest.raises(module.EmulationError, match='^emulator allocation exhausted$'):
        harness._malloc(harness)
    assert harness._heap_cur == end == module.HEAP_ADDRESS + module.HEAP_SIZE


def test_two_max_worker_inputs_refused_before_writes_or_dispatch(modules, harness):
    module = modules.harness
    engine = modules.adi_run.CoreADI.__new__(modules.adi_run.CoreADI)
    engine.harness = harness
    marker = b'guest-object-sentinel'
    harness.mem_write(module.OBJECT_ADDRESS, marker)
    before = harness._scratch_cur
    dispatch = Mock(side_effect=AssertionError('oversized request was dispatched'))
    engine._dispatch = dispatch
    with pytest.raises(module.EmulationError, match='^emulator allocation exhausted$'):
        engine.provisioning_end(1, b'p' * 131072, b't' * 131072)
    assert harness._scratch_cur == before
    assert harness.mem_read(module.OBJECT_ADDRESS, len(marker)) == marker
    dispatch.assert_not_called()


def test_ordinary_provisioning_end_keeps_pointer_and_size_semantics(modules, harness):
    engine = modules.adi_run.CoreADI.__new__(modules.adi_run.CoreADI)
    engine.harness = harness

    def dispatch(name, packet):
        assert name == 'ProvisioningEnd'
        session, ptm, ptm_len, tk, tk_len = struct.unpack('>IQIQI', packet)
        assert session == 7 and ptm_len == 3 and tk_len == 4
        assert harness.mem_read(ptm, ptm_len) == b'ptm'
        assert harness.mem_read(tk, tk_len) == b'tick'
        assert ptm != tk
        return 0, 0, 0

    engine._dispatch = dispatch
    result = engine.provisioning_end(7, b'ptm', b'tick')
    assert result.ok and result.outputs == {'session': 7, 'ptm_len': 3, 'tk_len': 4}


def test_one_max_worker_input_remains_supported(modules, harness):
    engine = modules.adi_run.CoreADI.__new__(modules.adi_run.CoreADI)
    engine.harness = harness
    engine._dispatch = Mock(return_value=(0, 0, 0))
    result = engine.provisioning_start(-2, b'x' * 131072)
    assert result.ok and result.outputs['spim_len'] == 131072
    engine._dispatch.assert_called_once()


@pytest.mark.parametrize('mac_stubs', [False, True])
def test_actual_guest_random_hooks_consume_distinct_host_entropy(modules, harness, monkeypatch, mac_stubs):
    if mac_stubs:
        modules.stubs.MacStubs(harness)
    data = [b'\x01\x02\x03\x04', b'\x05\x06\x07\x08', b'first-buffer', b'next--buffer']
    entropy = Mock(side_effect=data)
    monkeypatch.setattr(modules.harness.secrets, 'token_bytes', entropy)
    stub = modules.harness.STUB_ADDRESS
    harness._stub_by_index[stub] = '_arc4random'
    assert harness.invoke(stub, []) == 0x04030201
    assert harness.invoke(stub, []) == 0x08070605
    harness._stub_by_index[stub] = '_arc4random_buf'
    output = harness.scratch(32)
    assert harness.invoke(stub, [output, 12]) == 0
    assert harness.mem_read(output, 12) == b'first-buffer'
    assert harness.invoke(stub, [output, 12]) == 0
    assert harness.mem_read(output, 12) == b'next--buffer'
    assert [call.args for call in entropy.call_args_list] == [(4,), (4,), (12,), (12,)]


@pytest.mark.parametrize('failure', [OSError('host-private-error'), b'short', bytearray(b'1234')])
def test_host_entropy_failure_is_fixed_and_has_no_pattern_fallback(modules, harness, monkeypatch, failure):
    entropy = Mock(side_effect=failure) if isinstance(failure, Exception) else Mock(return_value=failure)
    monkeypatch.setattr(modules.harness.secrets, 'token_bytes', entropy)
    with pytest.raises(modules.harness.EmulationError, match='^emulator entropy unavailable$') as error:
        harness.random_u32()
    assert 'host-private' not in str(error.value)


def test_random_buffer_failure_preserves_destination(modules, harness, monkeypatch):
    output = harness.scratch(32)
    marker = b'unchanged-memory'
    harness.mem_write(output, marker)
    monkeypatch.setattr(modules.harness.secrets, 'token_bytes', Mock(side_effect=OSError('private-entropy')))
    with pytest.raises(modules.harness.EmulationError, match='^emulator entropy unavailable$'):
        harness.random_buffer(output, len(marker))
    assert harness.mem_read(output, len(marker)) == marker


@pytest.mark.parametrize('address,size', [(0, 1), (2**64 - 1, 2), (1, 2**64 - 1)])
def test_unmapped_or_host_sized_random_buffer_refused_before_entropy(modules, harness, monkeypatch, address, size):
    entropy = Mock(side_effect=AssertionError('entropy called for invalid buffer'))
    monkeypatch.setattr(modules.harness.secrets, 'token_bytes', entropy)
    with pytest.raises(modules.harness.EmulationError, match='^emulator buffer refused$'):
        harness.random_buffer(address, size)
    entropy.assert_not_called()


def test_zero_random_buffer_is_a_noop_and_mapped_boundary_is_exact(modules, harness, monkeypatch):
    entropy = Mock(side_effect=AssertionError('entropy called for zero size'))
    monkeypatch.setattr(modules.harness.secrets, 'token_bytes', entropy)
    assert harness.random_buffer(0, 0) == 0
    harness.checked_buffer(modules.harness.HEAP_ADDRESS, modules.harness.HEAP_SIZE)
    with pytest.raises(modules.harness.EmulationError, match='^emulator buffer refused$'):
        harness.checked_buffer(modules.harness.HEAP_ADDRESS + 1, modules.harness.HEAP_SIZE)
    entropy.assert_not_called()


def test_guest_output_slice_is_bounded_before_host_read(modules, harness):
    engine = modules.adi_run.CoreADI.__new__(modules.adi_run.CoreADI)
    engine.harness = harness
    pointer, length = harness.scratch(8), harness.scratch(8)
    harness.write_u64(pointer, modules.harness.HEAP_ADDRESS)
    harness.write_u32(length, 2**32 - 1)
    with pytest.raises(modules.harness.EmulationError, match='^emulator buffer refused$'):
        engine._slice(pointer, length)


def test_coreadi_uses_supplied_immutable_verified_bytes_without_reopening_path(modules, monkeypatch, tmp_path):
    path = tmp_path / 'synthetic-image'
    path.write_bytes(b'replaced-unverified-content')
    real_open = builtins.open

    def refuse_image_open(name, *args, **kwargs):
        if str(name) == str(path):
            raise AssertionError('image path reopened after verification')
        return real_open(name, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', refuse_image_open)
    engine = modules.adi_run.CoreADI(path=path, image_bytes=EMPTY_MACHO)
    assert engine.harness.image.data is EMPTY_MACHO
    assert engine.harness.image.macho.ncmds == 0


def test_mutable_image_buffer_is_refused(modules):
    with pytest.raises(modules.harness.EmulationError, match='^emulator image bytes refused$'):
        modules.adi_run.CoreADI(image_bytes=bytearray(EMPTY_MACHO))


@pytest.mark.parametrize('extra', [0, 1])
def test_combined_scratch_budget_just_fits_or_refuses_before_writes(modules, harness, extra):
    module = modules.harness
    engine = modules.adi_run.CoreADI.__new__(modules.adi_run.CoreADI)
    engine.harness = harness
    marker = b'object-marker'
    harness.mem_write(module.OBJECT_ADDRESS, marker)
    harness.invoke = Mock(return_value=0)
    # 0x800 payload + 0x20 parameters, with both inputs aligned to sixteen.
    first = b'p' * 131072
    second = b't' * (module.SCRATCH_SIZE - 131072 - 0x820 + extra)
    if extra:
        with pytest.raises(module.EmulationError, match='^emulator allocation exhausted$'):
            engine.provisioning_end(1, first, second)
        assert harness._scratch_cur == module.SCRATCH_ADDRESS
        harness.invoke.assert_not_called()
    else:
        assert engine.provisioning_end(1, first, second).ok
        assert harness._scratch_cur == module.SCRATCH_ADDRESS + module.SCRATCH_SIZE
        harness.invoke.assert_called_once()
    assert harness.mem_read(module.OBJECT_ADDRESS, len(marker)) == marker


def test_guest_allocation_error_preserves_fixed_category_without_guest_addresses(modules, harness):
    stub = modules.harness.STUB_ADDRESS
    harness._stub_by_index[stub] = '_malloc'
    with pytest.raises(modules.harness.EmulationError, match='^emulator allocation exhausted$'):
        harness.invoke(stub, [2**64 - 1])


def synthetic_dispatcher_image(dispatch):
    """A tiny x86_64 fixture: set the caller's payload status to zero and return."""
    code = bytes.fromhex('48 8b 06 c7 00 00 00 00 00 31 c0 c3')
    size = dispatch + len(code)
    header = struct.pack('<8I', 0xFEEDFACF, 0x1000007, 3, 6, 1, 72, 0, 0)
    segment = struct.pack('<II16sQQQQIIII', 0x19, 72, b'__TEXT', 0, 0x100000, 0, size, 7, 7, 0, 0)
    image = bytearray(size)
    image[:len(header)] = header
    image[len(header):len(header)+len(segment)] = segment
    image[dispatch:] = code
    return bytes(image)


def test_actual_worker_child_loads_unicorn_and_executes_verified_synthetic_bytes(tmp_path):
    import unicorn

    runtime = EMULATOR.parent
    image = synthetic_dispatcher_image(0x979A0)
    library = tmp_path / 'synthetic-dispatcher.macho'
    library.write_bytes(image)
    # Only expected synthetic fixture hash/size differ. The actual worker main,
    # file reader, package loader, adapter, Unicorn execution and IPC remain intact.
    script = (
        'import importlib.util\n'
        f'spec = importlib.util.spec_from_file_location("synthetic_worker", {str(runtime / "worker.py")!r})\n'
        'worker = importlib.util.module_from_spec(spec)\n'
        'spec.loader.exec_module(worker)\n'
        f'worker.LIBRARY_BYTES = {len(image)}\n'
        f'worker.LIBRARY_SHA256 = {hashlib.sha256(image).hexdigest()!r}\n'
        'worker.main()\n'
    )
    package = str(Path(unicorn.__file__).resolve().parent)
    message = {'op': 'open', 'library': str(library), 'unicorn_package': package,
               'host_uuid': 'a' * 32, 'store': {}}
    completed = subprocess.run(
        [sys.executable, '-I', '-B', '-c', script],
        input=json.dumps(message) + '\n' + json.dumps({'op': 'check'}) + '\n',
        text=True, capture_output=True, timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ''
    assert [json.loads(line) for line in completed.stdout.splitlines()] == [
        {'provisioned': True}, {'provisioned': True},
    ]
