"""Observe ordinary managed requirements; do not install or import provider/native code."""
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys
import sysconfig

CORE = '2026.10.2'
CONSTRAINTS_SHA = '7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5'
REQUIREMENTS = ('life360==7.2.0', 'protobuf>=6.32.0,<8.0.0', 'anisette==1.2.4',
                'unicorn==2.1.4', 'srp==1.0.22', 'beautifulsoup4==4.13.3')
MODULES = {'life360': 'life360', 'protobuf': 'google.protobuf', 'anisette': 'anisette',
           'unicorn': 'unicorn', 'srp': 'srp', 'beautifulsoup4': 'bs4'}
CLOSURE = frozenset(('aiohappyeyeballs', 'aiohttp', 'aiosignal', 'anisette', 'appdirs', 'attrs',
    'beautifulsoup4', 'certifi', 'frozenlist', 'fs', 'idna', 'life360', 'multidict', 'propcache',
    'protobuf', 'pyelftools', 'setuptools', 'six', 'soupsieve', 'srp', 'typing-extensions',
    'unicorn', 'urllib3', 'yarl'))


def require(ok, label):
    if not ok:
        raise ValueError(label)


def name_of(value):
    return re.sub(r'[-_.]+', '-', value).lower()


def public_version(value):
    """Only bounded numeric public package versions; never stringify inputs."""
    return value if type(value) is str and re.fullmatch(
        r'[0-9]{1,8}(?:\.[0-9]{1,8}){1,3}', value) else None


def diagnostic_metadata():
    """Fixed 24-package metadata; no provider imports, URLs or origins."""
    constrained = {}
    try:
        from packaging.requirements import Requirement
        spec = importlib.util.find_spec('homeassistant')
        raw = (Path(spec.origin).parent / 'package_constraints.txt').read_bytes()
        require(hashlib.sha256(raw).hexdigest() == CONSTRAINTS_SHA, 'qa_dependency_constraints')
        for line in raw.decode().splitlines():
            line = line.split('#', 1)[0].strip()
            if line:
                req = Requirement(line)
                if req.marker is None or req.marker.evaluate({'extra': ''}):
                    constrained.setdefault(name_of(req.name), []).append(req)
        constraints_available = True
    except Exception:
        constraints_available = False
    result = {}
    for name in sorted(CLOSURE):
        try:
            version = public_version(metadata.version(name))
            satisfied = bool(constraints_available and version is not None and all(
                req.specifier.contains(version, prereleases=True) for req in constrained.get(name, ())))
            result[name] = {'available': True, 'version': version, 'constraints_satisfied': satisfied}
        except Exception:
            result[name] = {'available': False, 'version': None, 'constraints_satisfied': False}
    return result


def observe():
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    from homeassistant.requirements import pip_kwargs
    from homeassistant.util.package import is_docker_env

    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'qa_dependency_platform')
    spec = importlib.util.find_spec('homeassistant')
    require(spec is not None and spec.origin is not None, 'qa_dependency_core_origin')
    constraints = Path(spec.origin).parent / 'package_constraints.txt'
    raw = constraints.read_bytes()
    constraints_match = hashlib.sha256(raw).hexdigest() == CONSTRAINTS_SHA
    constrained = {}
    for line in raw.decode().splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        req = Requirement(line)
        if req.marker is None or req.marker.evaluate({'extra': ''}):
            constrained.setdefault(name_of(req.name), []).append(req)
    roots = {Path(sysconfig.get_path(key)).resolve() for key in ('purelib', 'platlib')}
    versions = {}
    packages = {}
    all_available = True
    for name in sorted(CLOSURE):
        item = {'available': False, 'version': None, 'metadata_system_origin': False, 'constraints_satisfied': False, 'python_satisfied': False}
        try:
            distribution = metadata.distribution(name)
            version = distribution.version
            require(isinstance(version, str) and re.fullmatch(r'[0-9]{1,8}(?:\.[0-9]{1,8}){1,3}', version), 'qa_dependency_version')
            python_requirement = distribution.metadata.get('Requires-Python')
            item.update(available=True, version=version,
                        metadata_system_origin=Path(distribution.locate_file('')).resolve() in roots,
                        python_satisfied=not python_requirement or SpecifierSet(python_requirement).contains(platform.python_version()),
                        constraints_satisfied=all(req.specifier.contains(version, prereleases=True)
                                                 for req in constrained.get(name, ())))
            versions[name] = version
        except metadata.PackageNotFoundError:
            all_available = False
        packages[name] = item
    direct = {}
    for raw_requirement in REQUIREMENTS:
        req = Requirement(raw_requirement)
        name = name_of(req.name)
        item = dict(packages[name])
        item.update(satisfies_requirement=item['available'] and req.specifier.contains(item['version'], prereleases=True),
                    loaded_module_present=False, origin_probe='unavailable', module_system_origin=False)
        if item['available']:
            loaded = sys.modules.get(MODULES[name])
            if loaded is not None:
                origin = getattr(loaded, '__file__', None)
                item.update(loaded_module_present=True, origin_probe='loaded_module')
            else:
                found = importlib.util.find_spec(MODULES[name])
                origin = found.origin if found is not None else None
                item['origin_probe'] = 'import_spec'
            item['module_system_origin'] = origin is not None and any(Path(origin).resolve().is_relative_to(root) for root in roots)
        direct[name] = item
    found, pending = set(), list(REQUIREMENTS)
    graph_valid = all_available
    if all_available:
        while pending:
            req = Requirement(pending.pop())
            if req.marker is not None and not req.marker.evaluate({'extra': ''}):
                continue
            name = name_of(req.name)
            require(req.url is None and name in CLOSURE and name in versions, 'qa_dependency_graph_name')
            require(req.specifier.contains(versions[name], prereleases=True), 'qa_dependency_graph_version')
            if name in found:
                continue
            found.add(name)
            declared = metadata.requires(name) or []
            require(len(declared) <= 256 and all(isinstance(item, str) and len(item) <= 400 for item in declared),
                    'qa_dependency_graph_bounds')
            pending.extend(declared)
            require(len(pending) <= 1024, 'qa_dependency_graph_pending_bound')
        graph_valid = found == CLOSURE
    deps = Path('/config/deps')
    config_deps_empty = not deps.exists() or (not deps.is_symlink()
        and not any(path.is_symlink() or path.is_file() for path in deps.rglob('*')))
    kwargs = pip_kwargs('/config')
    return {'schema': 1, 'core': metadata.version('homeassistant'), 'python': platform.python_version(),
            'constraints_sha256': hashlib.sha256(raw).hexdigest(), 'constraints_match': constraints_match,
            'docker_environment': is_docker_env(), 'ordinary_pip_target_unset': 'target' not in kwargs,
            'config_deps_empty': config_deps_empty, 'direct': direct, 'closure': packages,
            'closure_count': len(packages), 'closure_graph_checked': graph_valid,
            'provider_or_native_imports_requested_by_probe': False}


if __name__ == '__main__':
    print(json.dumps(observe(), sort_keys=True))
