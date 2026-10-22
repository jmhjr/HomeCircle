"""Unchanged reviewed requirement graph functions; do not activate integrations."""
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re

class Refused(RuntimeError):
    pass

def check(condition, label):
    if not condition:
        raise Refused(label)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def declared_requirements(value):
    check(isinstance(value, list) and len(value) <= 256, "declared_requirements_refused")
    check(all(isinstance(item, str) and len(item) <= 300 and re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9][A-Za-z0-9_.+!-]*", item)
        for item in value), "declared_requirements_refused")
    return value


def source_literal(raw, name, *, required):
    try:
        module = ast.parse(raw)
        nodes = []
        for node in module.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name
                                                    for target in node.targets):
                nodes.append(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
                nodes.append(node.value)
        check(len(nodes) == 1 or (not required and not nodes), "core_literal_declaration_refused")
        return ast.literal_eval(nodes[0]) if nodes else []
    except (SyntaxError, ValueError, TypeError):
        raise Refused("core_literal_declaration_refused") from None


def default_auth_declarations(config_raw, provider_raw, mfa_raw):
    """Derive the exact unchanged Core defaults, without importing auth modules."""
    try:
        module = ast.parse(config_raw)
        providers, modules = [], []
        for node in ast.walk(module):
            if not isinstance(node, ast.Assign):
                continue
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "auth_conf" in names:
                providers.append(ast.literal_eval(node.value))
            if "mfa_conf" in names:
                value = node.value
                check(isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                      and isinstance(value.func.value, ast.Name) and value.func.value.id == "config"
                      and value.func.attr == "get" and len(value.args) == 2 and not value.keywords
                      and isinstance(value.args[0], ast.Name) and value.args[0].id == "CONF_AUTH_MFA_MODULES",
                      "default_auth_declaration_refused")
                modules.append(ast.literal_eval(value.args[1]))
        check(providers == [[{"type": "homeassistant"}]]
              and modules == [[{"type": "totp", "id": "totp", "name": "Authenticator app"}]],
              "default_auth_declaration_refused")
        provider = declared_requirements(source_literal(provider_raw, "REQUIREMENTS", required=False))
        mfa = declared_requirements(source_literal(mfa_raw, "REQUIREMENTS", required=True))
        check(provider == [] and mfa == ["pyotp==2.10.0", "PyQRCode==1.2.1"],
              "default_auth_requirements_refused")
        return {"homeassistant.auth.providers.homeassistant": provider, "homeassistant.auth.mfa_modules.totp": mfa}
    except (SyntaxError, ValueError, TypeError):
        raise Refused("default_auth_declaration_refused") from None


def requirement_graph(base, roots, preimports, discovery):
    """Mirror Core's requirement traversal, without setting integrations up."""
    def manifest(domain):
        check(isinstance(domain, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", domain),
              "core_component_name_refused")
        path = base / domain / "manifest.json"
        check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024**2,
              "core_component_manifest_refused")
        value = json.loads(path.read_bytes())
        check(isinstance(value, dict) and value.get("domain") == domain, "core_component_manifest_refused")
        return value
    found, requirements = set(), set()
    for domain in preimports:
        requirements.update(declared_requirements(manifest(domain).get("requirements", [])))
    queue = list(roots)
    while queue:
        domain = queue.pop()
        check(isinstance(domain, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", domain),
              "core_component_name_refused")
        if domain in found:
            continue
        found.add(domain)
        check(len(found) <= 256, "core_component_count_refused")
        value = manifest(domain)
        requirements.update(declared_requirements(value.get("requirements", [])))
        for key in ("dependencies", "after_dependencies"):
            dependencies = value.get(key, [])
            check(isinstance(dependencies, list) and len(dependencies) <= 256, "core_dependencies_refused")
            check(all(isinstance(item, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", item)
                      for item in dependencies), "core_dependencies_refused")
            queue.extend(dependencies)
        queue.extend(domain for domain, keys in discovery.items() if any(key in value for key in keys))
    return {"domains": sorted(found), "preimport_own_requirements_modules": sorted(preimports),
            "requirements": sorted(requirements)}


def verify_declared_versions(requirements):
    versions = {}
    for raw in declared_requirements(requirements):
        name, wanted = raw.split("==", 1)
        name = name.split("[", 1)[0]
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            raise Refused("startup_requirement_missing") from None
        check(actual == wanted, "startup_requirement_version_refused")
        versions[name.lower().replace("_", "-")] = actual
    return dict(sorted(versions.items()))


def core_component_requirements(payload):
    spec = importlib.util.find_spec("homeassistant")
    check(spec is not None and spec.origin is not None, "core_origin_refused")
    core = Path(spec.origin).parent
    base = core / "components"
    # Bootstrap imports several optional components before setup. Read its
    # declared roots without importing bootstrap until their wheels are ready.
    from homeassistant.const import BASE_PLATFORMS
    module = ast.parse((core / "bootstrap.py").read_bytes())
    def domain_set(node):
        if isinstance(node, ast.Name) and node.id == "BASE_PLATFORMS":
            return set(BASE_PLATFORMS)
        if isinstance(node, ast.Set):
            result = set()
            for item in node.elts:
                if isinstance(item, ast.Starred):
                    result.update(domain_set(item.value))
                else:
                    check(isinstance(item, ast.Constant) and isinstance(item.value, str),
                          "bootstrap_domain_expression_refused")
                    result.add(item.value)
            return result
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            return domain_set(node.left) - domain_set(node.right)
        raise Refused("bootstrap_domain_expression_refused")
    roots, preimports, seen = set(), set(), set()
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id in {"CORE_INTEGRATIONS", "DEFAULT_INTEGRATIONS"} for target in node.targets):
            roots.update(domain_set(node.value))
            seen.update(target.id for target in node.targets if isinstance(target, ast.Name))
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "components":
            preimports.update(alias.name for alias in node.names)
    check({"CORE_INTEGRATIONS", "DEFAULT_INTEGRATIONS"} <= seen, "bootstrap_domain_roots_refused")
    discovery = source_literal((core / "requirements.py").read_bytes(), "DISCOVERY_INTEGRATIONS", required=True)
    check(discovery == {"dhcp": ("dhcp",), "mqtt": ("mqtt",), "ssdp": ("ssdp",),
                        "zeroconf": ("zeroconf", "homekit")}, "core_discovery_declaration_refused")
    actual_roots = roots | set(json.loads(payload["manifest.json"])["dependencies"]) | {"http", "person", "zone"}
    result = requirement_graph(base, actual_roots, preimports, discovery)
    auth_paths = ("core_config.py", "auth/providers/homeassistant.py", "auth/mfa_modules/totp.py")
    raw = []
    for name in auth_paths:
        path = core / name
        check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024**2,
              "core_auth_source_refused")
        raw.append(path.read_bytes())
    auth = default_auth_declarations(*raw)
    result["default_auth_modules"] = auth
    result["requirements"] = sorted(set(result["requirements"]).union(*(set(value) for value in auth.values())))
    result["source_sha256"] = {name: sha(content) for name, content in zip(auth_paths, raw)}
    for name in ("bootstrap.py", "requirements.py"):
        result["source_sha256"][name] = sha((core / name).read_bytes())
    return result
