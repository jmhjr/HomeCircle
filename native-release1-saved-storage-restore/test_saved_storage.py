"""Composed host/acceptor/privacy contracts. Standard library only; no services."""
import ast
import asyncio
from contextlib import redirect_stdout
import io
import os
import re
import stat
import sys
import subprocess
import tarfile
import copy
import base64
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import controller as c
import accept_saved_storage as a
import guard_context as g
import storage_context as s
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
BASE=PARENT.parent/"safe-restore-staging-owner-20261021/native-release1-safe-restore"
PIN="f"*64

def result(action):
    return {"schema":1,"action":action,"outcome":"passed","entry_disabled":True,"managed_candidate_imported":False,
        "synthetic_only":True,"source_files_verified":True,"private_proof_written":action in {"seed","mutate"},
        "storage_checks":{**dict.fromkeys(c.COMMON_STORAGE_CHECKS,True),**c.STORAGE_CHECKS[action]}}

def record(post=False,mutation=False):
    return {"ready":True,"prebackup_rows":6,"prebackup_sha256":"a"*64,"prebackup_exact_match":True,
        "postbackup_marker_rows":6 if mutation else 0,"postbackup_marker_absent":not mutation,
        "postrestore_rows":6 if post else None,"postrestore_sha256":"b"*64 if post else None,
        "postrestore_exact_match":True if post else None,"integrity_ok":True,"backup_platform_registered":True,
        "commit_proven":True,"no_backup_failure_issue":True}

def packet():
    host=dict.fromkeys(a.HOST_KEYS,None)
    host.update({key:False for key in a.FALSE_GATES})
    host.update(schema=1,outcome="passed",phases=5,failure_or_final_stage="experimental_offline_saved_storage_restore_complete",
        temporary_global_offline_conditions=True,ordinary_default_supervisor_restore_qualified=False,
        tested_experimental_offline_disabled_saved_storage_restore=True,unsupported_conditions_override_used=True,
        actual_kvm_confirmed=True,host_newest_guard_retained=True,guard_repaired_before_storage_load=True,
        tested_disabled_entry_saved_storage_restore=True,synthetic_saved_accounts_seeded=True,qemu_stopped=True,
        private_workspace_removed=True,actual_core="2026.10.2",actual_supervisor="2026.10.3",
        initial_managed_environment={"api_core":"2026.10.2","container_core":"2026.10.2","supervisor":"2026.10.3"},
        current_core_image={"identity_model":"containerd_index_with_verified_stored_oci_chain","official_index_digest":g.IMAGE,
            "verified_oci_config_digest":"sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98",
            "stored_objects_hashed":3,"image_rootfs_matches_verified_config":True},
        provenance={"candidate_source_commit":c.SOURCE_COMMIT,"candidate_zip_sha256":PIN,"candidate_files":113,
                    "candidate_payload_sha256":"c"*64,"release_published":False},
        network_transitions=["closed_before_saved_storage"],network_boundary={"link_closed":True,
            "closed_probe_connected":False,"closed_probe_observations":9},
        core_actions=[{"action":action,"result":"ok","supervisor_running":True,"relevant_core_jobs_idle":True}
            for action in ["stop","start","stop","start","stop","start","stop","stop","start","stop","start","stop"]],
        backup_requests=[{"action":action,"result":"ok","exit_code":0,"exact_job_id_returned":True,"output_truncated":False,"signal":None}
            for action in ["create","restore"]],
        backup={"archive":{**dict.fromkeys(("database_included","candidate_match","disabled_entry","saved_pair_included",
            "saved_config_included","saved_selection_included","saved_registry_joins_included"),True),"guard_sha256":"d"*64}},
        restore={"host_copy_outside_entire_guest":True,"repaired_before_storage_load":True,
            "restored_old_guard_sha256":"d"*64,"promoted_newest_guard_sha256":"e"*64},
        guard_transfer_contexts=[g.public_success(x) for x in ["export","import"]],
        storage_contexts=[s.public_success(x) for x in c.STORAGE_ACTIONS],storage_results={x:result(x) for x in c.STORAGE_ACTIONS})
    offline=c.new_offline_receipt();offline.update({key:key not in {"foreign_options_refused","cleanup_failed"} for key in c.OFFLINE_RECEIPT_BOOL_KEYS})
    offline.update(apply_requests=1,reset_requests=1,apply_ack="confirmed",reset_ack="confirmed");host["offline_restore_conditions"]=offline
    phases={}
    for index,name in enumerate(c.PHASES):
        phase=dict.fromkeys(a.AUTOMATIC_KEYS if name=="automatic_restored_disabled" else a.PHASE_KEYS,None)
        phase.update(schema=1,phase=name,generation="before_restore" if index<3 else "after_restore",outcome="passed",
            entry_disabled=True,entry_loaded=False,candidate_imported=False,ha_config_entry_saved=True,process={"pid":100+index,"start_ticks":100+index},
            storage_raw_matches_expected=True,explicit_registry_joins_checked=True,selected_registry_joins=4,
            guard_counter=2 if index in [0,2] else 3,guard_repaired_before_storage_load=index>=3,
            provider_request_attempt_counts_measured=False,recovery_proof_attempt_counts_measured=False)
        if index!=2:
            phase.update(package_files_count=113,package_payload_sha256="c"*64,nonempty_options=True,nonempty_place=True,
                         recorder=record(index>=3,index==1))
        phases[name]=phase
    return host,phases

def archive_program():
    tree=ast.parse((ROOT/"controller.py").read_bytes())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Controller")
    fun=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="inspect_backup")
    return next(n.value.value for n in ast.walk(fun) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant)
                and isinstance(n.value.value,str) and 'import hashlib,json,re,tarfile' in n.value.value)

def execute_archive(fault=None):
    with tempfile.TemporaryDirectory(prefix="hc-saved-archive-contract-") as raw:
        folder=Path(raw);config=folder/"homeassistant";control=config/c.CONTROL;control.mkdir(parents=True)
        config_value={"findmy_accounts":{"a":{"storage_id":"1"*32}},"life360_account":{"method":"token","secret":"PRIVATE-CANARY"}}
        entry={"domain":"homecircle","entry_id":"2"*32,"disabled_by":"user","title":"Synthetic saved storage verified","data":copy.deepcopy(config_value),"options":copy.deepcopy(config_value)}
        selected={"schema":1,"entry_id":entry["entry_id"],"joins":[{"entity_id":"device_tracker.synthetic_"+str(i),"unique_id":"homecircle_findmy_"+str(i),"config_entry_id":entry["entry_id"],"kind":"item" if i<2 else "person"} for i in range(4)]}
        registry=[{key:value for key,value in row.items() if key!="kind"} for row in selected["joins"]]
        expected=dict.fromkeys(c.FINGERPRINT_FIELDS,"a"*64)
        expected.update(config_sha256=c.sha(c.canonical({"data":entry["data"],"options":entry["options"]})),credentials_sha256=c.sha(c.canonical(config_value["life360_account"])),
            selection_sha256=c.sha(c.canonical(selected)),key_sha256=c.sha(b"synthetic-key"),vault_sha256=c.sha(b"synthetic-cipher"))
        joins=c.sha(c.canonical(sorted(registry,key=lambda row:row["entity_id"])))
        package={"asset_"+str(i):b"synthetic source" for i in range(113)}
        (control/"inputs.json").write_bytes(c.canonical({"candidate_inventory":{name:{"bytes":len(data),"sha256":c.sha(data)} for name,data in package.items()}}))
        members={"data/custom_components/homecircle/"+name:data for name,data in package.items()}
        members.update({"data/.storage/core.config_entries":c.canonical({"data":{"entries":[entry]}}),
            "data/.storage/core.entity_registry":c.canonical({"data":{"entities":registry}}),
            "data/"+c.CONTROL+"/storage-selection-private.json":c.canonical(selected),
            "data/.storage/homecircle_findmy/recovery_guard/ledger.json":b"synthetic guard",
            "data/.storage/homecircle_findmy/homecircle_accounts/"+"1"*32+"/session.key":b"synthetic-key",
            "data/.storage/homecircle_findmy/homecircle_accounts/"+"1"*32+"/session.vault":b"synthetic-cipher",
            "data/home-assistant_v2.db":b"SQLite format 3\0"+b"0"*4100})
        keyname="data/.storage/homecircle_findmy/homecircle_accounts/"+"1"*32+"/session.key"
        if fault=="key_bytes":members[keyname]=b"different"
        if fault=="credential":entry["options"]["life360_account"]["secret"]="different";members["data/.storage/core.config_entries"]=c.canonical({"data":{"entries":[entry]}})
        if fault=="registry":registry[0]["unique_id"]="different";members["data/.storage/core.entity_registry"]=c.canonical({"data":{"entities":registry}})
        if fault=="enabled":entry["disabled_by"]=None;members["data/.storage/core.config_entries"]=c.canonical({"data":{"entries":[entry]}})
        if fault=="title":entry["title"]="unverified";members["data/.storage/core.config_entries"]=c.canonical({"data":{"entries":[entry]}})
        if fault=="barrier":members["data/"+c.CONTROL+"/restore-barrier.json"]=b"stale"
        if fault=="traversal":members["../private"] = b"private"
        inner=io.BytesIO()
        with tarfile.open(fileobj=inner,mode="w:") as archive:
            for name,data in members.items():
                item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o644 if fault=="key_mode" and name==keyname else 0o600;item.uid=0
                if fault=="symlink" and name==keyname:item.type=tarfile.SYMTYPE;item.linkname="/private";item.size=0
                archive.addfile(item,io.BytesIO(data))
        path=folder/"backup.tar"
        with tarfile.open(path,"w:") as archive:
            raw_inner=inner.getvalue();item=tarfile.TarInfo("homeassistant.tar");item.size=len(raw_inner);archive.addfile(item,io.BytesIO(raw_inner))
        script=archive_program().replace("__BASELINE__",repr(expected)).replace("__JOINS__",repr(joins))
        self_check=[script.count('Path("/data/homeassistant")'),script.count('Path("/data/backup/homecircle-safe-restore-qa.tar")')]
        assert self_check==[1,1]
        script=script.replace('Path("/data/homeassistant")',"Path("+repr(str(config))+")").replace('Path("/data/backup/homecircle-safe-restore-qa.tar")',"Path("+repr(str(path))+")")
        output=io.StringIO()
        with redirect_stdout(output):exec(compile(script,"<actual-scoped-archive-program>","exec"),{})
        return json.loads(output.getvalue())

def managed_functions(names):
    source=(ROOT/"guest_helper/homecircle_safe_restore_qa/__init__.py").read_bytes();tree=ast.parse(source)
    chosen=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    self_check={n.name for n in chosen};assert self_check==set(names)
    class Refused(Exception):pass
    def check(ok,code):
        if not ok:raise Refused(code)
    namespace={"Path":Path,"os":os,"stat":stat,"json":json,"re":re,"check":check,"CONTROL":c.CONTROL,"Refused":Refused}
    exec(compile(ast.Module(body=chosen,type_ignores=[]),"<actual-managed-functions>","exec"),namespace)
    return namespace

def selection_fixture(root):
    entry_id="1"*32
    joins=[{"entity_id":"device_tracker.synthetic_"+str(i),"unique_id":"homecircle_"+("findmy_" if i<2 else "life360_")+str(i),"config_entry_id":entry_id,"kind":"item" if i<2 else "person"} for i in range(4)]
    config={"primary_home":"zone.home","places":["zone.example_saved_storage"],"people":[],"pets":[],"items":[row["entity_id"] for row in joins if row["kind"]=="item"],"people_trackers":[row["entity_id"] for row in joins if row["kind"]=="person"],
        "members":{row["entity_id"]:{"kind":row["kind"],"trackers":[row["entity_id"]],"additional_residences":[],"show_on_map":True} for row in joins}}
    value={"schema":1,"entry_id":entry_id,"joins":joins};control=root/c.CONTROL;control.mkdir(mode=0o700)
    path=control/"storage-selection-private.json";path.write_bytes(c.canonical(value));path.chmod(0o600)
    return SimpleNamespace(entry_id=entry_id,data=copy.deepcopy(config),options=copy.deepcopy(config)),value,path

def offline_host(fault=None):
    clock=[100.0];events=[]
    host=c.Controller.__new__(c.Controller);host.deadline=2000.0;host.offline_restore_conditions=None
    host.minimum_core_image={"pinned":True};host.provenance={"candidate_files":113,"candidate_zip_sha256":c.CANDIDATE_SHA}
    host.backup={"homeassistant_version":c.CORE,"archive":dict.fromkeys(("candidate_match","disabled_entry","database_included","saved_pair_included","saved_config_included","saved_selection_included","saved_registry_joins_included"),True)}
    state={"effective":"foreign" if fault=="foreign_initial" else "empty","persisted":"foreign" if fault=="foreign_initial" else "absent"}
    staged={};writes=[];network_checks=[];gets=[0]
    def network():
        events.append("NIC_closed");network_checks.append(host.deadline)
        if fault=="NIC_before" and len(network_checks)==1:raise c.Refused("network_boundary_refused")
        if fault=="delayed_final_probe" and len(network_checks)==4:clock[0]+=91
    host.assert_network_closed=network
    host.core_container_state=lambda _:(events.append("Core_stopped") or "stopped")
    host.verify_candidate=lambda:events.append("candidate113")
    host.actual_core_image=lambda:(events.append("same_image") or host.minimum_core_image)
    host.guest_write=lambda name,raw:staged.__setitem__(name,raw)
    host.guest_read=lambda name:staged[name]
    def capture(data,ok=True):return {"exitcode":0 if ok else 1,"signal":None,"stdout":c.canonical(data),"stderr":b"","truncated":False}
    def api(action,deadline):
        events.append(action)
        if action=="info":
            gets[0]+=1
            if fault=="GET_preflight" and gets[0]==1:return capture({"result":"error","data":{}},False)
            values=[] if state["effective"]=="empty" else c.OFFLINE_INTERNET_CONDITIONS if state["effective"]=="owned_two" else ["PRIVATE_FOREIGN_CANARY"]
            jobs=[{"name":"backup_manager_partial_backup","done":False,"child_jobs":[]}] if fault=="busy_initial" and gets[0]==1 else []
            return capture({"result":"ok","data":{"ignore_conditions":values,"jobs":jobs}})
        writes.append(action)
        if action=="apply":
            state.update(effective="owned_two",persisted="empty" if fault=="apply_save_failed" else "owned_two")
            if fault=="apply_lost_ACK":raise OSError("PRIVATE_ACK_CANARY")
            if fault=="apply_error":return capture({"result":"error","data":{}},False)
        else:
            state.update(effective="empty",persisted="owned_two" if fault=="clear_save_failed" else "empty")
            if fault=="clear_lost_ACK":raise OSError("PRIVATE_ACK_CANARY")
            if fault=="clear_error":return capture({"result":"error","data":{}},False)
        return capture({"result":"ok","data":{}})
    host.offline_api=api
    persisted_reads=[0]
    def persisted(deadline):
        events.append("persisted");persisted_reads[0]+=1
        if fault=="delayed_final_read" and persisted_reads[0]==4:clock[0]+=91
        return state["persisted"]
    host.offline_persisted_state=persisted
    def backup(restore=False):
        if restore is not True:raise AssertionError("restore only")
        events.append("restore_job_complete")
        if fault=="restore_error":raise c.Refused("backup_operation_api_refused")
        if fault=="restore_deadline":
            clock[0]=host.deadline+1
            raise c.Refused("host_deadline_exceeded")
        if fault=="foreign_cleanup":state.update(effective="foreign",persisted="foreign")
    host.backup_operation=backup
    return host,clock,events,writes,state,network_checks

def execute_persistence(path):
    # Only the fixed path and expected UID are localized for owned Mac temp I/O.
    program=c.JOB_OPTIONS_PERSISTENCE_PROGRAM
    assert program.count("path=Path('/data/jobs.json')")==program.count("OWNER=0")==1
    program=program.replace("path=Path('/data/jobs.json')","path=Path("+repr(str(path))+")").replace("OWNER=0","OWNER="+str(os.geteuid()))
    output=io.StringIO()
    with redirect_stdout(output):exec(compile(program,"<actual-fixed-persisted-options-consumer>","exec"),{})
    return json.loads(output.getvalue())

class Contracts(unittest.TestCase):
    def accept(self,host,phases):
        with patch.object(a,"CANDIDATE_SHA",PIN):return a.accept(host,phases)

    def test_complete_composed_five_phase_packet_accepts_only_disabled_scope(self):
        value=self.accept(*packet())
        self.assertIs(value["tested_disabled_entry_saved_storage_restore"],True)
        for key in ("ordinary_enabled_restore_safety_accepted","automatic_guard_antirollback","provider_authentication_after_restore_tested","full_encrypted_cloud_backup_tested","stable_release_approval"):
            self.assertIs(value[key],False)

    def test_all_action_public_results_have_strict_bool_and_count_semantics(self):
        for action in c.STORAGE_ACTIONS:
            self.assertEqual(c.project_storage_result(result(action),action),result(action))
            for key,value in result(action)["storage_checks"].items():
                bad=result(action);bad["storage_checks"][key]=not value if type(value)is bool else True
                with self.subTest(action=action,key=key),self.assertRaises(c.Refused):c.project_storage_result(bad,action)

    def test_public_result_extra_secret_and_wrong_proof_written_are_refused(self):
        for action in c.STORAGE_ACTIONS:
            for change in [{"private_canary":"SECRET"},{"private_proof_written":action not in {"seed","mutate"}},{"schema":True}]:
                bad={**result(action),**change}
                with self.assertRaises(c.Refused):c.project_storage_result(bad,action)

    def test_private_fingerprint_schema_never_accepts_raw_missing_extra_or_bool(self):
        good=dict.fromkeys(c.FINGERPRINT_FIELDS,"a"*64)
        self.assertEqual(c.private_fingerprints(good),good)
        for bad in [{**good,"secret":"SECRET"},{key:value for key,value in good.items() if key!="key_sha256"},
                    dict(good,key_sha256="SECRET"),dict(good,key_sha256=True)]:
            with self.assertRaises(c.Refused):c.private_fingerprints(bad)

    def test_private_proof_requires_exact_version_and_nested_fingerprints(self):
        good={"schema":1,"baseline":dict.fromkeys(c.FINGERPRINT_FIELDS,"a"*64),"mutation":None}
        self.assertEqual(c.private_proof(good),good)
        for bad in [dict(good,schema=True),dict(good,secret="SECRET"),dict(good,baseline=None),dict(good,mutation={})]:
            with self.assertRaises(c.Refused):c.private_proof(bad)

    def test_every_scope_exclusion_is_required_false(self):
        for key in a.FALSE_GATES:
            host,phases=packet();host[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):self.accept(host,phases)

    def test_every_host_completion_cleanup_gate_is_required_true(self):
        for key in ("actual_kvm_confirmed","host_newest_guard_retained","guard_repaired_before_storage_load",
                    "tested_disabled_entry_saved_storage_restore","synthetic_saved_accounts_seeded","qemu_stopped","private_workspace_removed"):
            host,phases=packet();host[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):self.accept(host,phases)

    def test_extra_public_host_or_phase_state_is_refused(self):
        host,phases=packet();host["private_credential"]="SECRET"
        with self.assertRaises(ValueError):self.accept(host,phases)
        for name in c.PHASES:
            host,phases=packet();phases[name]["private_baseline_sha256"]="a"*64
            with self.subTest(name=name),self.assertRaises(ValueError):self.accept(host,phases)

    def test_each_phase_disabled_imported_or_early_decryption_flag_refuses(self):
        for name in c.PHASES:
            for key,value in [("entry_disabled",False),("entry_loaded",True),("candidate_imported",True),
                ("ha_config_entry_saved",False),("storage_raw_matches_expected",False),("explicit_registry_joins_checked",False),("selected_registry_joins",True),
                ("guard_repaired_before_storage_load",name not in c.PHASES[3:])]:
                host,phases=packet();phases[name][key]=value
                with self.subTest(name=name,key=key),self.assertRaises(ValueError):self.accept(host,phases)

    def test_phase_and_context_missing_extra_wrong_order_fail(self):
        host,phases=packet()
        for bad in [{key:value for key,value in phases.items() if key!="baseline_disabled"},{**phases,"extra":phases[c.PHASES[0]]}]:
            with self.assertRaises(ValueError):self.accept(host,bad)
        for field in ["storage_contexts","guard_transfer_contexts"]:
            for kind in ["missing","reversed","extra"]:
                host,phases=packet();values=host[field]
                host[field]=values[:-1] if kind=="missing" else values[::-1] if kind=="reversed" else values+[values[0]]
                with self.subTest(field=field,kind=kind),self.assertRaises(Exception):self.accept(host,phases)

    def test_versions_image_and_unbound_candidate_refuse(self):
        for field,value in [("actual_core","2026.10.3"),("actual_supervisor","2026.10.2"),("actual_core",None)]:
            host,phases=packet();host[field]=value
            with self.assertRaises(ValueError):self.accept(host,phases)
        host,phases=packet();host["current_core_image"]["stored_objects_hashed"]=True
        with self.assertRaises(ValueError):self.accept(host,phases)
        with self.assertRaises(ValueError):a.accept(*packet())

    def test_reopened_network_unproven_probe_or_changed_management_refuses(self):
        for field,value in [("network_transitions",["closed_before_saved_storage","reopen"]),
                            ("network_boundary",{"link_closed":True,"closed_probe_connected":True,"closed_probe_observations":9})]:
            host,phases=packet();host[field]=value
            with self.assertRaises(ValueError):self.accept(host,phases)
        host,phases=packet();host["core_actions"][0]["action"]="restart"
        with self.assertRaises(ValueError):self.accept(host,phases)

    def test_actual_backup_scope_and_guard_timeline_must_be_proven(self):
        for field in ("saved_pair_included","saved_config_included","saved_selection_included","saved_registry_joins_included","disabled_entry"):
            host,phases=packet();host["backup"]["archive"][field]=False
            with self.assertRaises(ValueError):self.accept(host,phases)
        for name in c.PHASES:
            host,phases=packet();phases[name]["guard_counter"]=1
            with self.assertRaises(ValueError):self.accept(host,phases)
        host,phases=packet();host["restore"]["promoted_newest_guard_sha256"]="d"*64
        with self.assertRaises(ValueError):self.accept(host,phases)

    def test_recorder_rollback_and_postrestore_restart_are_required(self):
        for name,key,value in [("mutated_disabled","postbackup_marker_rows",0),("repaired_storage_disabled","postbackup_marker_absent",False),
            ("restart_disabled","postrestore_sha256","9"*64),("restart_disabled","integrity_ok",False)]:
            host,phases=packet();phases[name]["recorder"][key]=value
            with self.subTest(name=name,key=key),self.assertRaises(Exception):self.accept(host,phases)

    def test_original_thirty_two_infrastructure_method_asts_are_unchanged(self):
        expected=json.loads((ROOT/"baseline-controls.json").read_text())["controller_methods"]
        t=ast.parse((ROOT/"controller.py").read_bytes());cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=="Controller")
        methods={n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertEqual(len(expected),32)
        self.assertEqual({name:methods[name] for name in expected},expected)

    def test_original_guard_transfer_context_reset_wrapper_bytes_unchanged(self):
        for name in ("guard_transfer.py","guard_context.py","reset_fresh_config.py","run_host.sh"):
            expected=json.loads((ROOT/"baseline-controls.json").read_text())["infrastructure_files"][name]
            raw=(ROOT/name).read_bytes()
            self.assertEqual({"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()},expected,name)

    def test_actual_run_call_order_closes_network_and_never_activates(self):
        t=ast.parse((ROOT/"controller.py").read_bytes());cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=="Controller")
        run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="run")
        calls=[(n.func.attr,ast.literal_eval(n.args[0]) if n.args and isinstance(n.args[0],ast.Constant) else None)
               for n in ast.walk(run) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=="self"]
        self.assertNotIn("reopen_after_repaired_disabled",[name for name,_ in calls])
        phases=[arg for name,arg in calls if name=="phase"]
        self.assertEqual(phases,["baseline_disabled","mutated_disabled","repaired_storage_disabled","restart_disabled"])
        self.assertLess(calls.index(("disconnect_external_network",None)),calls.index(("run_storage_context","seed")))
        self.assertLess(calls.index(("fresh_restore_control",None)),calls.index(("phase","repaired_storage_disabled")))

    def test_managed_helper_has_no_product_import_setup_or_enable_path(self):
        t=ast.parse((ROOT/"guest_helper/homecircle_safe_restore_qa/__init__.py").read_bytes())
        for n in ast.walk(t):
            if isinstance(n,ast.ImportFrom):self.assertFalse((n.module or "").startswith("custom_components.homecircle"))
            if isinstance(n,ast.Import):self.assertFalse(any(x.name.startswith("custom_components.homecircle") for x in n.names))
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
                self.assertNotIn(n.func.attr,{"async_add","async_set_disabled_by","async_setup_entry","client_factory","async_start"})
                if n.func.attr == "poll":
                    self.assertIsInstance(n.func.value,ast.Call)
                    self.assertEqual(n.func.value.func.id,"Rehearsal")

    def test_archive_inspector_is_actual_composed_program_and_contains_no_decrypt(self):
        t=ast.parse((ROOT/"controller.py").read_bytes());cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=="Controller")
        fun=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="inspect_backup")
        script=next(n.value.value for n in ast.walk(fun) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str) and 'import hashlib,json,re,tarfile' in n.value.value)
        tree=ast.parse(script.replace('__BASELINE__',repr(dict.fromkeys(c.FINGERPRINT_FIELDS,'a'*64))).replace('__JOINS__',repr('b'*64)))
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'load','decrypt','save_account'} for n in ast.walk(tree)))
        self.assertIn('saved_pair_included',script)
        self.assertIn('core.entity_registry',script)

    def test_actual_archive_program_executes_full_bounded_nested_archive(self):
        value=execute_archive()
        for key in ("saved_pair_included","saved_config_included","saved_selection_included","saved_registry_joins_included","disabled_entry"):
            self.assertIs(value[key],True)
        self.assertNotIn("PRIVATE-CANARY",json.dumps(value))
        self.assertEqual(set(value),{"archive_bytes","database_included","candidate_match","disabled_entry","saved_pair_included","saved_config_included","saved_selection_included","saved_registry_joins_included","guard_sha256"})

    def test_actual_archive_program_refuses_changed_pair_credentials_registry_scope_and_paths(self):
        for fault in ("key_bytes","credential","registry","enabled","title","barrier","traversal","key_mode","symlink"):
            with self.subTest(fault=fault),self.assertRaisesRegex(RuntimeError,"saved_storage_archive_refused"):
                execute_archive(fault)

    def test_actual_managed_mapping_accepts_explicit_shape_and_rejects_name_inference(self):
        namespace=managed_functions({"read_json","selected_mapping"})
        with tempfile.TemporaryDirectory(prefix="hc-managed-mapping-") as raw:
            root=Path(raw);entry,value,path=selection_fixture(root)
            self.assertEqual(namespace["selected_mapping"](root,entry),value)
            entry.options["members"][value["joins"][0]["entity_id"]]["trackers"]=[value["joins"][1]["entity_id"]]
            entry.data=copy.deepcopy(entry.options)
            with self.assertRaisesRegex(namespace["Refused"],"qa_product_member_shape"):
                namespace["selected_mapping"](root,entry)

    def test_actual_managed_mapping_refuses_divergent_snapshots_and_invalid_household_keys(self):
        namespace=managed_functions({"read_json","selected_mapping"})
        for fault in ("divergence","primary_home","places","kind","duplicate"):
            with tempfile.TemporaryDirectory(prefix="hc-managed-invalid-") as raw:
                root=Path(raw);entry,value,path=selection_fixture(root)
                if fault=="divergence":entry.options["primary_home"]="zone.different"
                elif fault=="primary_home":entry.options.pop("primary_home")
                elif fault=="places":entry.options["places"]=[{"name":"invalid"}]
                elif fault=="kind":entry.options["members"][value["joins"][0]["entity_id"]]["kind"]="pet"
                else:value["joins"][1]=dict(value["joins"][0]);path.write_bytes(c.canonical(value))
                if fault!="divergence":entry.data=copy.deepcopy(entry.options)
                with self.subTest(fault=fault),self.assertRaises(namespace["Refused"]):namespace["selected_mapping"](root,entry)

    def test_actual_guard_preservation_stages_only_guard_source_and_retains_bound_bundle(self):
        payload={"schema":1,"files":{"ledger.json":base64.b64encode(b"synthetic ledger").decode(),
            "ledger.lock":"","account-"+"a"*64+".lock":""}}
        bundle=c.canonical(payload)
        latest=c.guard_fingerprint(c.decode_guard(bundle))
        proof={"schema":1,"token":"1"*32,"generation":"before_restore","branch_commit":"2"*40,
            "postbackup_window":{"start":10,"end":11,"rows":6,"sha256":"3"*64}}
        writes=[];actions=[]
        host=c.Controller.__new__(c.Controller)
        host.config_path="/mnt/data/supervisor/homeassistant";host.phase_token=proof["token"]
        host.args=SimpleNamespace(branch_commit=proof["branch_commit"])
        host.latest_guard_sha256=latest;host.backup_guard_sha256="0"*64
        host.stop_core=lambda:actions.append("stop")
        host.guest_read=lambda path:c.canonical(proof)
        host.guest_write=lambda path,data:writes.append((path,data))
        host.run_guard_transfer=lambda action:(actions.append(action) or {"exitcode":0,"signal":None,"truncated":False,"stdout":bundle,"stderr":b""})
        with tempfile.TemporaryDirectory(prefix="hc-guard-preservation-") as raw:
            host.private=Path(raw)
            host.preserve_latest_guard()
            self.assertEqual(actions,["stop","export"])
            self.assertEqual(writes,[(c.GUEST_ROOT+"/guard-transfer.py",(ROOT/"guard_transfer.py").read_bytes())])
            self.assertEqual(host.host_guard.read_bytes(),bundle)
            self.assertEqual(stat.S_IMODE(host.host_guard.stat().st_mode),0o600)
            self.assertIs(host.host_guard_retained,True)

    def test_actual_managed_title_update_waits_for_real_store_without_changing_configuration(self):
        namespace=managed_functions({"read_json","read_managed_json","assert_unimported","persist_verified_entry"})
        disabled,state=object(),object()
        namespace.update(asyncio=asyncio,sys=SimpleNamespace(modules={}),VERIFIED_TITLE="Synthetic saved storage verified",
            ConfigEntryDisabler=SimpleNamespace(USER=disabled),ConfigEntryState=SimpleNamespace(NOT_LOADED=state))
        with tempfile.TemporaryDirectory(prefix="hc-entry-save-") as raw:
            root=Path(raw);store=root/".storage/core.config_entries";store.parent.mkdir(mode=0o700)
            entry=SimpleNamespace(entry_id="1"*32,disabled_by=disabled,state=state,title="Synthetic saved storage",data={"nested":{"token":"private-fixture"}},options={"nested":{"token":"private-fixture"}},runtime_data=None)
            before=copy.deepcopy({"data":entry.data,"options":entry.options})
            row={"entry_id":entry.entry_id,"domain":"homecircle","disabled_by":"user","title":entry.title,**copy.deepcopy(before)}
            store.write_bytes(c.canonical({"data":{"entries":[row]}}));store.chmod(0o644)
            calls=[];reads=[]
            def update(actual,**changes):
                self.assertIs(actual,entry);calls.append(changes);entry.title=changes["title"];return True
            async def executor(function,*arguments):
                value=function(*arguments);reads.append(value)
                if len(reads)==1:
                    row["title"]=entry.title;store.write_bytes(c.canonical({"data":{"entries":[row]}}))
                return value
            hass=SimpleNamespace(config=SimpleNamespace(components=set()),data={},config_entries=SimpleNamespace(async_update_entry=update),async_add_executor_job=executor)
            async def no_wait(_):pass
            with patch.object(asyncio,"sleep",no_wait):
                self.assertIs(asyncio.run(namespace["persist_verified_entry"](hass,root,entry,True)),True)
                self.assertEqual(calls,[{"title":namespace["VERIFIED_TITLE"]}]);self.assertEqual(len(reads),2)
                self.assertIs(asyncio.run(namespace["persist_verified_entry"](hass,root,entry)),True)
            self.assertEqual(calls,[{"title":namespace["VERIFIED_TITLE"]}])
            self.assertEqual({"data":entry.data,"options":entry.options},before)
            self.assertEqual(json.loads(store.read_bytes())["data"]["entries"][0]["title"],namespace["VERIFIED_TITLE"])

    def test_actual_managed_title_update_refuses_no_change_configuration_mutation_and_import(self):
        for fault in ("unchanged","configuration","imported","enabled"):
            namespace=managed_functions({"read_json","read_managed_json","assert_unimported","persist_verified_entry"})
            disabled,state=object(),object()
            namespace.update(asyncio=asyncio,sys=SimpleNamespace(modules={}),VERIFIED_TITLE="Synthetic saved storage verified",
                ConfigEntryDisabler=SimpleNamespace(USER=disabled),ConfigEntryState=SimpleNamespace(NOT_LOADED=state))
            entry=SimpleNamespace(entry_id="1"*32,disabled_by=disabled,state=state,title="Unverified",data={"nested":{"value":1}},options={"nested":{"value":1}},runtime_data=None)
            calls=[]
            def update(actual,**changes):
                calls.append(changes);entry.title=changes["title"]
                if fault=="configuration":entry.data["nested"]["value"]=2
                return fault!="unchanged"
            async def executor(*_):self.fail("refusal must precede private store reads")
            hass=SimpleNamespace(config=SimpleNamespace(components=set()),data={},config_entries=SimpleNamespace(async_update_entry=update),async_add_executor_job=executor)
            if fault=="imported":namespace["sys"].modules["custom_components.homecircle"]=object()
            if fault=="enabled":entry.disabled_by=None
            with self.subTest(fault=fault),self.assertRaises(namespace["Refused"]):
                asyncio.run(namespace["persist_verified_entry"](hass,Path("/unused"),entry,True))
            self.assertEqual(len(calls),int(fault not in {"imported","enabled"}))

    def test_actual_restored_barrier_requires_newer_process_before_repair_or_storage_load(self):
        for ticks in (99,100,101):
            host=c.Controller.__new__(c.Controller);host.network_boundary={"link_closed":True};host.host_guard_retained=True
            host.phases=[{"process":{"start_ticks":90}},{"process":{"start_ticks":100}}]
            host.config_path="/owned";host.phase_token="1"*32;host.args=SimpleNamespace(branch_commit="2"*40)
            host.storage_proof={"baseline":dict.fromkeys(c.FINGERPRINT_FIELDS,"a"*64)}
            host.joins_sha256="b"*64;host.backup_guard_sha256="c"*64;host.public=Path("/not-written")
            value={"schema":1,"token":host.phase_token,"generation":"before_restore","branch_commit":host.args.branch_commit,
                "entry_disabled":True,"entry_loaded":False,"candidate_imported":False,"ha_config_entry_saved":True,
                "observed_storage":{key:"a"*64 for key in c.RAW_STORAGE_FIELDS},"joins_sha256":host.joins_sha256,
                "guard_sha256":host.backup_guard_sha256,"process":{"pid":123,"start_ticks":ticks}}
            host.guest_read=lambda _:c.canonical(value);host.guard_fingerprint=lambda _:host.backup_guard_sha256
            host.remaining=lambda _:5;host.assert_network_closed=lambda:None
            writes=[]
            with patch.object(c,"write_json",lambda path,value:writes.append((path,value))):
                if ticks<=100:
                    with self.subTest(ticks=ticks),self.assertRaisesRegex(c.Refused,"automatic_distinct_process_required"):host.restored_boot_barrier()
                    self.assertEqual(writes,[]);self.assertEqual(len(host.phases),2)
                else:
                    host.restored_boot_barrier();self.assertEqual(len(writes),1);self.assertIs(host.after_restore_barrier,True)

    def test_actual_pre_restore_barrier_absence_rejects_regular_and_dangling_symlink(self):
        with tempfile.TemporaryDirectory(prefix="hc-barrier-absence-") as raw:
            root=Path(raw);control=root/c.CONTROL;control.mkdir(mode=0o700);barrier=control/"restore-barrier.json"
            host=c.Controller.__new__(c.Controller);host.config_path=str(root);host.network_boundary={"link_closed":True}
            host.host_guard_retained=True;host.phases=[{},{}]
            def guest(command,timeout):
                completed=subprocess.run(["/bin/sh","-c",command],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
                c.require(completed.returncode==0,"guest_command_failed");return completed.stdout
            host.guest=guest;host.require_restore_barrier_absent()
            barrier.write_bytes(b"stale")
            with self.assertRaises(c.Refused):host.require_restore_barrier_absent()
            barrier.unlink();barrier.symlink_to(root/"missing")
            with self.assertRaises(c.Refused):host.require_restore_barrier_absent()
            t=ast.parse((ROOT/"controller.py").read_bytes());cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=="Controller")
            run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="run")
            direct=[n.value for n in run.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)]
            names=[node.func.attr for node in direct if isinstance(node.func,ast.Attribute)]
            self.assertEqual(names[names.index("require_restore_barrier_absent"):names.index("restored_boot_barrier")+1],["require_restore_barrier_absent","experimental_offline_restore","restored_boot_barrier"])

    def test_failure_stage_catalog_exactly_matches_source_producer(self):
        source=ast.parse((ROOT/"storage_transfer.py").read_bytes())
        assignment=next(n for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="STAGES" for t in n.targets))
        self.assertEqual(c.STORAGE_FAILURE_STAGES,frozenset(ast.literal_eval(assignment.value.args[0])))
        for action in c.STORAGE_ACTIONS:
            for stage in c.STORAGE_FAILURE_STAGES:
                result={"exitcode":1,"signal":None,"stdout":c.canonical({"schema":1,"outcome":"failed","stage":stage}),"stderr":b"","truncated":False}
                self.assertEqual(c.project_storage_failure(result,action),{"schema":1,"action":action,"stage":stage})

    def test_failure_stage_parser_suppresses_private_canaries_and_malformed_shapes(self):
        good={"schema":1,"outcome":"failed","stage":"private_state"}
        canary="PRIVATE_FAILURE_CANARY_"+"x"*40
        payloads=[{**good,"secret":canary},{**good,"schema":True},{**good,"schema":"1"},{**good,"outcome":"passed"},
            {**good,"stage":canary},{**good,"stage":["seed"]},{"schema":1,"outcome":"failed"},[good],None]
        encoded=[c.canonical(value) for value in payloads]+[b'{"schema":1,"outcome":"failed","stage":"seed","stage":"guard"}',
            b'\xff',b'not json',b' '*513,c.canonical(good)+b' '*513]
        for raw in encoded:
            returned=c.project_storage_failure({"exitcode":1,"signal":None,"stdout":raw,"stderr":b"","truncated":False},"seed")
            self.assertIs(returned,None)
            self.assertNotIn(canary,json.dumps(returned))

    def test_failure_stage_parser_requires_clean_exact_failure_boundary(self):
        good={"exitcode":1,"signal":None,"stdout":c.canonical({"schema":1,"outcome":"failed","stage":"seed"}),"stderr":b"","truncated":False}
        for key,value in [("exitcode",True),("exitcode",0),("exitcode",2),("exitcode",None),("signal",False),("signal",11),
            ("stderr",b"PRIVATE_CANARY"),("stderr",""),("truncated",True),("truncated",0),("stdout","{}")] :
            with self.subTest(key=key,value=value):self.assertIs(c.project_storage_failure(dict(good,**{key:value}),"seed"),None)
        self.assertIs(c.project_storage_failure(dict(good,extra="PRIVATE_CANARY"),"seed"),None)
        self.assertIs(c.project_storage_failure(good,"unknown"),None)
        self.assertEqual(c.project_storage_failure(dict(good,signal=0),"seed"),{"schema":1,"action":"seed","stage":"seed"})

    def test_actual_failed_context_projects_fixed_stage_then_refuses_without_reading_private_results(self):
        host=c.Controller.__new__(c.Controller);host.storage_contexts=[];host.storage_results={};host.generation="before_restore"
        host.nonce="1"*32;host.phase_token="2"*32;host.args=SimpleNamespace(branch_commit="3"*40);host.config_path="/owned"
        host.assert_network_closed=lambda:None;host.remaining=lambda _:60
        source=(ROOT/"storage_transfer.py").read_bytes();writes=[]
        host.guest_write=lambda path,raw:writes.append((path,raw))
        def read(path):
            self.assertEqual(path,c.GUEST_ROOT+"/storage-transfer.py","failed transfer must not read private result/proof")
            return source
        host.guest_read=read;host.guest=lambda *_:b""
        cleaned=[]
        class FailedContext:
            def __init__(self,*args,**kwargs):self.record={"schema":1,"action":"seed","outcome":"failed_or_incomplete"}
            def run(self):
                cleaned.append(True);self.record.update(owned_container_removed=True,managed_core_same_stopped_process=True)
                return {"exitcode":1,"signal":None,"stdout":c.canonical({"schema":1,"outcome":"failed","stage":"private_state"}),"stderr":b"","truncated":False}
        with patch.object(c,"StorageContext",FailedContext),self.assertRaisesRegex(c.Refused,"storage_transfer_refused"):
            host.run_storage_context("seed")
        self.assertEqual(cleaned,[True]);self.assertEqual(host.storage_results,{})
        self.assertEqual(host.storage_contexts[0]["storage_transfer_failure"],{"schema":1,"action":"seed","stage":"private_state"})
        self.assertIs(host.storage_contexts[0]["owned_container_removed"],True)

    def test_actual_managed_reader_is_narrow_and_private_reader_stays_private(self):
        namespace=managed_functions({"read_json","read_managed_json"})
        with tempfile.TemporaryDirectory(prefix="hc-managed-modes-") as raw:
            root=Path(raw);store=root/".storage";store.mkdir(mode=0o700)
            for name in ("core.config_entries","core.entity_registry"):
                path=store/name;path.write_bytes(b'{"data":{}}')
                for mode in (0o600,0o644):
                    path.chmod(mode);self.assertEqual(namespace["read_managed_json"](root,name),{"data":{}})
                with self.assertRaises(namespace["Refused"]):namespace["read_json"](path)
                for mode in (0o400,0o640,0o664,0o666):
                    path.chmod(mode)
                    with self.assertRaises(namespace["Refused"]):namespace["read_managed_json"](root,name)
                path.unlink();path.symlink_to(root/"absent")
                with self.assertRaises(OSError):namespace["read_managed_json"](root,name)
                path.unlink()
            with self.assertRaises(namespace["Refused"]):namespace["read_managed_json"](root,"session.key")

    def test_actual_experimental_wrapper_single_apply_restore_clear_and_all_scope_gates(self):
        host,clock,events,writes,state,checks=offline_host()
        with patch.object(c.time,"monotonic",lambda:clock[0]):host.experimental_offline_restore()
        self.assertEqual(writes,["apply","clear"]);self.assertEqual(events.count("restore_job_complete"),1)
        self.assertEqual(state,{"effective":"empty","persisted":"empty"});self.assertEqual(host.deadline,2000)
        self.assertEqual(checks,[1910,1910,190,190])
        self.assertEqual(c.project_offline_receipt(host.offline_restore_conditions,True),host.offline_restore_conditions)
        self.assertLess(events.index("apply"),events.index("restore_job_complete"));self.assertLess(events.index("restore_job_complete"),events.index("clear"))
        self.assertIs(host.offline_restore_conditions["ordinary_default_restore_qualified"],False)

    def test_foreign_prior_options_busy_jobs_and_missing_GET_capability_abort_before_writes(self):
        for fault in ("foreign_initial","busy_initial","GET_preflight","NIC_before"):
            host,clock,events,writes,state,checks=offline_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaises(c.Refused):host.experimental_offline_restore()
            self.assertEqual(writes,[]);self.assertNotIn("restore_job_complete",events);self.assertEqual(host.deadline,2000)

    def test_apply_lost_ACK_or_error_cleans_once_and_never_invokes_restore(self):
        for fault in ("apply_lost_ACK","apply_error","apply_save_failed"):
            host,clock,events,writes,state,_=offline_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaises(c.Refused):host.experimental_offline_restore()
            self.assertEqual(writes,["apply","clear"]);self.assertNotIn("restore_job_complete",events)
            self.assertEqual(state,{"effective":"empty","persisted":"empty"})
            self.assertIs(host.offline_restore_conditions["original_options_restored"],True)
            with self.assertRaises(c.Refused):c.project_offline_receipt(host.offline_restore_conditions,True)
            self.assertNotIn("PRIVATE_ACK_CANARY",json.dumps(host.offline_restore_conditions))

    def test_restore_failure_still_restores_original_options_without_retry(self):
        host,clock,events,writes,state,_=offline_host("restore_error")
        with patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaisesRegex(c.Refused,"backup_operation_api_refused"):host.experimental_offline_restore()
        self.assertEqual(writes,["apply","clear"]);self.assertEqual(events.count("restore_job_complete"),1)
        self.assertEqual(state,{"effective":"empty","persisted":"empty"})
        self.assertIs(host.offline_restore_conditions["original_options_restored"],True)

    def test_clear_lost_ACK_error_or_save_failure_never_qualifies_completion(self):
        for fault in ("clear_lost_ACK","clear_error","clear_save_failed"):
            host,clock,events,writes,state,_=offline_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaisesRegex(c.Refused,"offline_options_cleanup_failed"):host.experimental_offline_restore()
            self.assertEqual(writes,["apply","clear"]);self.assertIs(host.offline_restore_conditions["original_options_restored"],False)
            self.assertIs(host.offline_restore_conditions["cleanup_failed"],True)
            with self.assertRaises(c.Refused):c.project_offline_receipt(host.offline_restore_conditions,True)

    def test_foreign_options_appearing_during_restore_are_not_overwritten(self):
        host,clock,events,writes,state,_=offline_host("foreign_cleanup")
        with patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaisesRegex(c.Refused,"offline_options_cleanup_failed"):host.experimental_offline_restore()
        self.assertEqual(writes,["apply"]);self.assertEqual(state,{"effective":"foreign","persisted":"foreign"})
        self.assertIs(host.offline_restore_conditions["foreign_options_refused"],True)

    def test_finally_regains_reserved_deadline_after_restore_budget_exhaustion(self):
        host,clock,events,writes,state,checks=offline_host("restore_deadline")
        with patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaisesRegex(c.Refused,"host_deadline_exceeded"):host.experimental_offline_restore()
        self.assertEqual(writes,["apply","clear"]);self.assertIs(host.offline_restore_conditions["original_options_restored"],True)
        self.assertEqual(host.deadline,2000);self.assertTrue(all(value==2000 for value in checks[2:]))

    def test_delayed_final_persistence_or_network_probe_refuses_ninety_second_claim(self):
        for fault in ("delayed_final_read","delayed_final_probe"):
            host,clock,events,writes,state,checks=offline_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,"monotonic",lambda:clock[0]),self.assertRaisesRegex(c.Refused,"offline_options_cleanup_failed"):host.experimental_offline_restore()
            self.assertIs(host.offline_restore_conditions["original_options_restored"],False)
            self.assertEqual(writes,["apply","clear"]);self.assertEqual(host.deadline,2000)

    def test_experimental_success_acceptor_requires_all_new_scope_and_restoration_fields(self):
        host,phases=packet();value=self.accept(host,phases)
        self.assertIs(value["tested_experimental_offline_disabled_saved_storage_restore"],True)
        self.assertIs(value["ordinary_default_supervisor_restore_qualified"],False)
        for key in c.OFFLINE_RECEIPT_BOOL_KEYS:
            altered=copy.deepcopy(host);altered["offline_restore_conditions"][key]=not altered["offline_restore_conditions"][key]
            with self.subTest(key=key),self.assertRaises(Exception):self.accept(altered,phases)
        for key in ("apply_ack","reset_ack"):
            altered=copy.deepcopy(host);altered["offline_restore_conditions"][key]="unconfirmed"
            with self.assertRaises(Exception):self.accept(altered,phases)
        for key,value in [("temporary_global_offline_conditions",False),("ordinary_default_supervisor_restore_qualified",True),
            ("tested_experimental_offline_disabled_saved_storage_restore",False),("unsupported_conditions_override_used",False)]:
            altered=copy.deepcopy(host);altered[key]=value
            with self.assertRaises(Exception):self.accept(altered,phases)

    def test_jobs_projection_accepts_only_exact_internet_pair_and_checks_visible_relevant_jobs(self):
        for ignored,expected in [([],"empty"),(c.OFFLINE_INTERNET_CONDITIONS,"owned_two"),(["healthy"],"foreign"),(["internet_host"],"foreign")]:
            state,idle=c.offline_jobs_info(c.canonical({"result":"ok","data":{"ignore_conditions":ignored,"jobs":[]}}))
            self.assertEqual((state,idle),(expected,True))
        raw=c.canonical({"result":"ok","data":{"ignore_conditions":[],"jobs":[{"name":"outer","done":True,"child_jobs":[{"name":"home_assistant_core_start","done":False}]}]}})
        self.assertEqual(c.offline_jobs_info(raw),("empty",False))
        for raw in [b'{"result":"ok","data":{"ignore_conditions":[],"ignore_conditions":[],"jobs":[]}}',
            c.canonical({"result":"ok","data":{"ignore_conditions":False,"jobs":[]}}),b"PRIVATE_RESPONSE_CANARY"]:
            with self.assertRaises(Exception):c.offline_jobs_info(raw)

    def test_actual_internal_curl_script_has_token_only_on_header_stdin_and_fixed_public_requests(self):
        token="PRIVATE_SYNTHETIC_TOKEN_CANARY"
        stub="""#!"""+sys.executable+"""
import sys,json,os
args=sys.argv[1:];header=sys.stdin.read();method=args[args.index('--request')+1]
print(json.dumps({'first':args[0],'method':method,'endpoint':args[-1],'body':args[args.index('--data-binary')+1] if '--data-binary' in args else None,
'header_auth':header.startswith('Authorization: Bearer '+os.environ['SUPERVISOR_TOKEN']+'\\n'),'header_count':len(header.splitlines()),
'secret_in_argv':any(os.environ['SUPERVISOR_TOKEN'] in value for value in args),'args':args}))
"""
        with tempfile.TemporaryDirectory(prefix="hc-curl-bridge-") as raw:
            folder=Path(raw);curl=folder/"curl";curl.write_text(stub);curl.chmod(0o700)
            env={"PATH":str(folder)+":"+os.defpath,"SUPERVISOR_TOKEN":token,"LANG":"C"}
            for action,method,endpoint,body in [("info","GET","http://supervisor/jobs/info",None),("apply","POST","http://supervisor/jobs/options",{"ignore_conditions":c.OFFLINE_INTERNET_CONDITIONS}),("clear","POST","http://supervisor/jobs/options",{"ignore_conditions":[]})]:
                result=subprocess.run(["/bin/sh","-s","--",action],input=c.OFFLINE_API_CLIENT.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=5,check=False)
                self.assertEqual(result.returncode,0,result.stderr);value=json.loads(result.stdout)
                self.assertEqual((value["first"],value["method"],value["endpoint"]),("-q",method,endpoint))
                self.assertEqual(json.loads(value["body"]) if value["body"] else None,body)
                self.assertIs(value["header_auth"],True);self.assertEqual(value["header_count"],2);self.assertIs(value["secret_in_argv"],False)
                self.assertNotIn("-L",value["args"]);self.assertEqual(value["args"][value["args"].index("--noproxy")+1],"*")
                self.assertEqual(value["args"][value["args"].index("--max-redirs")+1],"0")
                self.assertNotIn(token,result.stdout.decode())
            for action,secret in [("invalid",token),("info",""),("apply",token+"\nBAD")]:
                result=subprocess.run(["/bin/sh","-s","--",action],input=c.OFFLINE_API_CLIENT.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**env,"SUPERVISOR_TOKEN":secret},timeout=5,check=False)
                self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b"");self.assertEqual(result.stderr,b"")

    def test_actual_persistence_reader_classifies_only_fixed_options_and_rejects_unsafe_inputs(self):
        with tempfile.TemporaryDirectory(prefix="hc-job-options-") as raw:
            path=Path(raw)/"jobs.json"
            self.assertEqual(execute_persistence(path),{"schema":1,"state":"absent"})
            for value,state in [({"ignore_conditions":[]},"empty"),({"ignore_conditions":c.OFFLINE_INTERNET_CONDITIONS},"owned_two"),
                ({"ignore_conditions":["PRIVATE_FOREIGN_CANARY"]},"foreign"),({"ignore_conditions":False},"refused"),({"extra":"PRIVATE_CANARY"},"refused")]:
                path.write_bytes(c.canonical(value));path.chmod(0o644);result=execute_persistence(path)
                self.assertEqual(result,{"schema":1,"state":state});self.assertNotIn("PRIVATE",json.dumps(result))
            path.write_bytes(b'{"ignore_conditions":[],"ignore_conditions":[]}');path.chmod(0o600)
            self.assertEqual(execute_persistence(path)["state"],"refused")
            path.unlink();path.symlink_to(Path(raw)/"absent")
            self.assertEqual(execute_persistence(path)["state"],"refused")
            path.unlink();path.write_bytes(c.canonical({"ignore_conditions":[]}));path.chmod(0o666)
            self.assertEqual(execute_persistence(path)["state"],"refused")

    def test_persistence_reader_rejects_detached_old_inode_during_atomic_replacement(self):
        with tempfile.TemporaryDirectory(prefix="hc-detached-job-options-") as raw:
            path=Path(raw)/"jobs.json";path.write_bytes(c.canonical({"ignore_conditions":[]}));path.chmod(0o644)
            original=os.read
            def replaced(descriptor,count):
                value=original(descriptor,count)
                fresh=path.with_suffix(".new");fresh.write_bytes(c.canonical({"ignore_conditions":[]}));fresh.chmod(0o644);os.replace(fresh,path)
                return value
            with patch.object(os,"read",replaced):self.assertEqual(execute_persistence(path),{"schema":1,"state":"refused"})

    def test_offline_ACK_parser_rejects_unknown_types_shapes_and_expired_transport(self):
        good={"exitcode":0,"signal":None,"stdout":c.canonical({"result":"ok","data":{}}),"stderr":b"","truncated":False}
        self.assertIs(c.offline_api_ack(good),True)
        for key,value in [("exitcode",False),("signal",False),("stderr",b"PRIVATE_CANARY"),("truncated",0),
            ("stdout",b'{"result":"ok","result":"ok","data":{}}'),("stdout",c.canonical({"result":"ok","data":{},"extra":"PRIVATE"})),
            ("stdout",c.canonical({"result":"ok","data":{"ignore_conditions":[]}}))]:
            with self.subTest(key=key,value=value):self.assertIs(c.offline_api_ack(dict(good,**{key:value})),False)
        host=c.Controller.__new__(c.Controller)
        host.guest=lambda *_args,**_kwargs:good
        with patch.object(c.time,"monotonic",side_effect=[100,113]),self.assertRaisesRegex(c.Refused,"offline_api_deadline_exceeded"):
            host.offline_api("info",112)

    def test_fixed_computed_backup_stages_and_window_order_are_catalogued(self):
        self.assertTrue({"supervisor_partial_create","supervisor_partial_restore"}<=c.FAILURE_STAGES)
        tree=ast.parse((ROOT/"controller.py").read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Controller")
        run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="run")
        calls=[n.value.func.attr for n in run.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute)]
        self.assertLess(calls.index("experimental_offline_restore"),calls.index("restored_boot_barrier"))
        self.assertLess(calls.index("experimental_offline_restore"),calls.index("fresh_restore_control"))

if __name__=="__main__":unittest.main()
