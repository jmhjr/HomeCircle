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
    host.update(schema=1,outcome="passed",phases=5,failure_or_final_stage="default_conditions_saved_storage_restore_complete",
        temporary_global_offline_conditions=False,ordinary_default_supervisor_restore_qualified=False,
        tested_default_conditions_disabled_saved_storage_restore=True,unsupported_conditions_override_used=False,
        default_conditions_disabled_synthetic_restore_qualified=True,default_supervisor_conditions_used=True,manual_newest_guard_repair_required=True,
        actual_kvm_confirmed=True,host_newest_guard_retained=True,guard_repaired_before_storage_load=True,
        tested_disabled_entry_saved_storage_restore=True,synthetic_saved_accounts_seeded=True,qemu_stopped=True,
        private_workspace_removed=True,actual_core="2026.10.2",actual_supervisor="2026.10.3",
        initial_managed_environment={"api_core":"2026.10.2","container_core":"2026.10.2","supervisor":"2026.10.3"},
        current_core_image={"identity_model":"containerd_index_with_verified_stored_oci_chain","official_index_digest":g.IMAGE,
            "verified_oci_config_digest":"sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98",
            "stored_objects_hashed":3,"image_rootfs_matches_verified_config":True},
        provenance={"candidate_source_commit":c.SOURCE_COMMIT,"candidate_zip_sha256":PIN,"candidate_files":113,
                    "candidate_payload_sha256":"c"*64,"release_published":False},
        network_transitions=["closed_before_saved_storage","opened_for_default_restore","closed_after_default_restore"],network_boundary={"link_closed":True,
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
    default=c.new_default_receipt();default.update({key:key not in {"foreign_options_refused","cleanup_failed"} for key in c.DEFAULT_RECEIPT_BOOL_KEYS})
    default.update(network_open_requests=1,network_close_requests=1,network_info_requests=1);host["default_restore_conditions"]=default
    phases={}
    for index,name in enumerate(c.PHASES):
        phase=dict.fromkeys(a.AUTOMATIC_KEYS if name=="automatic_restored_disabled" else a.PHASE_KEYS,None)
        phase.update(schema=1,phase=name,generation="before_restore" if index<3 else "after_restore",outcome="passed",
            entry_disabled=True,entry_loaded=False,candidate_imported=False,ha_config_entry_saved=True,closed_boot_grant_verified=True,process={"pid":100+index,"start_ticks":100+index},
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
        if fault in {"grant","grant_temp"}:members["data/"+c.CONTROL+"/closed-boot-grant."+("json" if fault=="grant" else "tmp")]=b"stale"
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


def execute_persistence(path):
    # Only the fixed path and expected UID are localized for owned Mac temp I/O.
    program=c.JOB_OPTIONS_PERSISTENCE_PROGRAM
    assert program.count("path=Path('/data/jobs.json')")==program.count("OWNER=0")==1
    program=program.replace("path=Path('/data/jobs.json')","path=Path("+repr(str(path))+")").replace("OWNER=0","OWNER="+str(os.geteuid()))
    output=io.StringIO()
    with redirect_stdout(output):exec(compile(program,"<actual-fixed-persisted-options-consumer>","exec"),{})
    return json.loads(output.getvalue())


def default_host(fault=None):
    clock=[100.0];events=[];staged={};state={'effective':'foreign' if fault=='foreign_initial' else 'empty','persisted':'absent'}
    host=c.Controller.__new__(c.Controller);host.deadline=2000.;host.default_restore_conditions=None
    host.minimum_core_image={'pinned':True};host.provenance={'candidate_files':113,'candidate_zip_sha256':c.CANDIDATE_SHA}
    host.backup={'homeassistant_version':c.CORE,'archive':dict.fromkeys(('candidate_match','disabled_entry','database_included','saved_pair_included','saved_config_included','saved_selection_included','saved_registry_joins_included'),True)}
    host.network_boundary={'link_closed':True};host.network_transitions=['closed_before_saved_storage'];closed=[True];checks=[]
    def network():
        events.append('assert_closed');checks.append(host.deadline)
        if not closed[0]:raise c.Refused('external_network_not_closed')
    host.assert_network_closed=network
    host.core_container_state=lambda _: 'stopped'
    host.verify_candidate=lambda:events.append('candidate113')
    host.actual_core_image=lambda:host.minimum_core_image
    def config():
        events.append('disabled_config')
        if fault=='config':raise c.Refused('default_disabled_config_before_open_refused')
    host.verify_disabled_preopen=config
    host.guest_write=lambda name,raw:staged.__setitem__(name,raw)
    host.guest_read=lambda name:staged[name]
    def effective(deadline):
        events.append('GET_info')
        if fault=='GET':raise c.Refused('offline_options_GET_refused')
        return state['effective'],fault!='busy'
    host.default_effective_state=effective
    def persisted(deadline):
        events.append('persisted')
        if fault=='late_read' and 'close' in events:clock[0]+=91
        return state['persisted']
    host.default_persisted_state=persisted
    def link(up):
        events.append('open' if up else 'close');closed[0]=not up
        if fault==('open_ack' if up else 'close_ack'):raise OSError('PRIVATE_LINK_CANARY')
    host.set_restore_network_link=link
    def probe():
        events.append('probe_closed' if closed[0] else 'probe_open')
        if fault=='positive_probe' and not closed[0]:return False
        if fault=='negative_probe' and closed[0]:return True
        if fault=='late_probe' and closed[0]:clock[0]+=91
        return not closed[0]
    host.connectivity_probe=probe
    host.qga=SimpleNamespace(call=lambda action:events.append(action))
    def ready(record):
        events.append('network_ready');record['network_info_requests']=1
        if fault=='readiness':raise c.Refused('default_internet_readiness_deadline')
        record.update(supervisor_host_internet_true=True,supervisor_internet_true=True)
    host.wait_default_internet=ready
    def restore(restore=False):
        assert restore is True;events.append('restore')
        if fault=='restore_error':raise c.Refused('backup_operation_api_refused')
        if fault=='restore_lost_ACK':raise OSError('PRIVATE_RESTORE_ACK')
        if fault=='cancel':raise KeyboardInterrupt
        if fault=='restore_deadline':clock[0]=host.deadline+1;raise c.Refused('host_deadline_exceeded')
        if fault=='foreign_final':state['effective']='foreign'
    host.backup_operation=restore
    def grant(name):
        assert name=='automatic_restored_disabled' and closed[0] is True;events.append('grant')
    host.grant_closed_boot=grant
    return host,clock,events,state,checks

def grant_functions():
    names={'closed_boot_request','consume_closed_boot_grant'}
    namespace=managed_functions(names)
    namespace['CANDIDATE']=c.CANDIDATE_SHA
    namespace['process']=lambda:{'pid':4321,'start_ticks':1234}
    namespace['secrets']=SimpleNamespace(token_hex=lambda _: 'e'*32)
    return namespace

def request_fixture(namespace):
    phase={'token':'a'*32,'generation':'before_restore','phase':'baseline_disabled'}
    inputs={'source_commit':c.SOURCE_COMMIT,'branch_commit':'b'*40}
    return namespace['closed_boot_request'](phase,inputs,True)



def execute_poll(name,baseline_present,mode,change=False):
    tree=ast.parse((ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Rehearsal')
    poll=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='poll')
    events=[];calls=[0];sleeps=[0];generation='after_restore' if name in {'repaired_storage_disabled','restart_disabled'} else 'before_restore'
    with tempfile.TemporaryDirectory() as raw:
        directory=Path(raw);control=directory/'control';control.mkdir()
        phase={'schema':1,'token':'a'*32,'generation':generation,'phase':name,'branch_commit':'b'*40}
        (control/'phase.json').write_bytes(c.canonical(phase))
        if name not in {'baseline_disabled','repaired_storage_disabled'}:
            (control/'job-nonce.json').write_bytes(c.canonical({'token':phase['token'],'generation':generation}))
        if baseline_present:(control/'baseline.json').write_bytes(b'not read before grant')
        observed={'fixed':'fingerprint'};inputs={'generation':generation,'branch_commit':'b'*40,'source_commit':c.SOURCE_COMMIT}
        def read(path):
            if path.name=='baseline.json':
                assert 'grant' in events;events.append('baseline_private')
                return {'observed_storage':observed,'joins_sha256':'c'*64,'guard_sha256':'d'*64}
            return json.loads(path.read_bytes())
        def write(path,value):
            events.append('request' if path.name=='boot-request.json' else 'barrier' if path.name=='restore-barrier.json' else 'nonce')
            path.write_bytes(c.canonical(value))
            if path.name=='restore-barrier.json':hass.is_running=False
        def consume(*_):
            calls[0]+=1
            if mode=='invalid':raise ValueError('invalid')
            granted=mode=='valid' or mode=='later' and calls[0]>1
            events.append('grant' if granted else 'no_grant')
            return granted
        async def sleep(_):
            sleeps[0]+=1
            if mode=='absent' or change and sleeps[0]>2:hass.is_running=False
        async def executor(function,*args):return function(*args)
        hass=SimpleNamespace(is_running=True,async_add_executor_job=executor)
        ns={'PHASES':c.PHASES,'RESULTS':'results','_LOGGER':SimpleNamespace(error=lambda *_:events.append('refused')),
            'asyncio':SimpleNamespace(sleep=sleep),'re':re,'inputs_at':lambda _:inputs,'read_json':read,'write_json':write,
            'current_entry':lambda _:SimpleNamespace(),'assert_unimported':lambda *_:None,
            'closed_boot_request':lambda phase,inputs,automatic:{'token':phase['token'],'generation':phase['generation'],'phase':phase['phase'],'branch_commit':inputs['branch_commit'],'process':{'pid':2,'start_ticks':20}},
            'consume_closed_boot_grant':consume,'process':lambda:{'pid':2,'start_ticks':20},
            'check':lambda ok,label:None if ok else (_ for _ in ()).throw(ValueError(label))}
        def guard(_):
            assert 'grant' in events;events.append('guard_private');return 'd'*64
        ns['guard_files']=guard
        module=ast.Module(body=[ast.ClassDef(name='Poll',bases=[],keywords=[],body=[poll],decorator_list=[])],type_ignores=[])
        exec(compile(ast.fix_missing_locations(module),'<actual-async-helper-poll>','exec'),ns)
        host=ns['Poll']();host.hass=hass;host.directory=directory;host.control=control
        async def raw_snapshot(_):
            assert 'grant' in events;events.append('pair_private');return observed,'c'*64
        async def run(_phase,_inputs):
            assert 'grant' in events;events.append('run')
            if change:
                phase['phase']='baseline_disabled';(control/'phase.json').write_bytes(c.canonical(phase))
            else:hass.is_running=False
        host.raw_snapshot=raw_snapshot;host.run=run
        asyncio.run(host.poll())
    return events



def execute_preopen(fault=None):
    tree=ast.parse((ROOT/'controller.py').read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Controller')
    fun=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='verify_disabled_preopen')
    script=next(n.value.value for n in fun.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='script' for x in n.targets))
    assert script.count("root=Path('/data/homeassistant')")==1
    with tempfile.TemporaryDirectory() as raw:
        folder=Path(raw);(folder/'.storage').mkdir();(folder/c.CONTROL).mkdir()
        selection={'schema':1,'entry_id':'1'*32,'joins':[]};config={'synthetic':'metadata'}
        entry={'domain':'homecircle','disabled_by':'user','title':'Synthetic saved storage verified','entry_id':'1'*32,'data':config,'options':copy.deepcopy(config)}
        expected=c.sha(c.canonical({'data':entry['data'],'options':entry['options']}));selected=c.sha(c.canonical(selection))
        if fault=='enabled':entry['disabled_by']=None
        if fault=='changed_config':entry['options']['changed']=True
        if fault=='title':entry['title']='not verified'
        configpath=folder/'.storage/core.config_entries';configpath.write_bytes(c.canonical({'data':{'entries':[entry]}}));configpath.chmod(0o666 if fault=='mode' else 0o644)
        if fault=='selection':selection['entry_id']='2'*32
        selectedpath=folder/c.CONTROL/'storage-selection-private.json';selectedpath.write_bytes(c.canonical(selection));selectedpath.chmod(0o600)
        if fault=='symlink':configpath.unlink();configpath.symlink_to(selectedpath)
        script=script.replace("root=Path('/data/homeassistant')","root=Path("+repr(raw)+")").replace('st.st_uid==0','st.st_uid=='+str(os.geteuid())).replace('__CONFIG__',repr(expected)).replace('__SELECTION__',repr(selected))
        output=io.StringIO()
        with redirect_stdout(output):exec(compile(script,'<actual-stopped-config-preopen>','exec'),{})
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
                "entry_disabled":True,"entry_loaded":False,"candidate_imported":False,"ha_config_entry_saved":True,"closed_boot_grant_verified":True,
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
            self.assertEqual(names[names.index("require_restore_barrier_absent"):names.index("restored_boot_barrier")+1],["require_restore_barrier_absent","default_conditions_restore","restored_boot_barrier"])

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


    def test_actual_default_wrapper_one_restore_no_option_writes_and_closed_grant_order(self):
        host,clock,events,state,checks=default_host()
        with patch.object(c.time,'monotonic',lambda:clock[0]):host.default_conditions_restore()
        self.assertEqual(events.count('open'),1);self.assertEqual(events.count('close'),1);self.assertEqual(events.count('restore'),1)
        self.assertLess(events.index('disabled_config'),events.index('open'));self.assertLess(events.index('open'),events.index('restore'))
        self.assertLess(events.index('close'),events.index('grant'));self.assertLess(events.index('probe_closed'),events.index('grant'))
        self.assertEqual(host.deadline,2000);self.assertEqual(state,{'effective':'empty','persisted':'absent'})
        self.assertEqual(host.default_restore_conditions['jobs_option_mutation_requests'],0)
        c.project_default_receipt(host.default_restore_conditions,True)

    def test_default_preflight_config_foreign_busy_and_readonly_capability_refuse_before_open(self):
        for fault in ('config','foreign_initial','busy','GET'):
            host,clock,events,_,_=default_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,'monotonic',lambda:clock[0]),self.assertRaises(c.Refused):host.default_conditions_restore()
            self.assertNotIn('open',events);self.assertNotIn('restore',events);self.assertNotIn('grant',events)
            self.assertEqual(host.deadline,2000)

    def test_open_lost_ACK_and_positive_probe_failure_still_close_once_without_restore_or_grant(self):
        for fault in ('open_ack','positive_probe','readiness'):
            host,clock,events,_,_=default_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,'monotonic',lambda:clock[0]),self.assertRaises(Exception):host.default_conditions_restore()
            self.assertEqual(events.count('open'),1);self.assertEqual(events.count('close'),1)
            self.assertIn('probe_closed',events);self.assertIn('guest-ping',events)
            self.assertNotIn('restore',events);self.assertNotIn('grant',events)

    def test_restore_failure_lost_ACK_and_cancellation_close_but_never_grant(self):
        for fault in ('restore_error','restore_lost_ACK','cancel','restore_deadline'):
            host,clock,events,_,_=default_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,'monotonic',lambda:clock[0]),self.assertRaises(BaseException):host.default_conditions_restore()
            self.assertEqual(events.count('restore'),1);self.assertEqual(events.count('close'),1);self.assertNotIn('grant',events)
            self.assertIs(host.default_restore_conditions['network_closed_after'],True)
            self.assertEqual(host.deadline,2000)

    def test_unknown_final_options_close_ACK_probe_or_deadline_failure_never_grant(self):
        for fault in ('foreign_final','close_ack','negative_probe','late_read','late_probe'):
            host,clock,events,_,_=default_host(fault)
            with self.subTest(fault=fault),patch.object(c.time,'monotonic',lambda:clock[0]),self.assertRaisesRegex(c.Refused,'default_network_cleanup_failed'):host.default_conditions_restore()
            self.assertEqual(events.count('close'),1);self.assertNotIn('grant',events)
            self.assertIs(host.default_restore_conditions['cleanup_failed'],True)

    def test_default_success_acceptor_requires_scope_no_overrides_every_grant_and_receipt_field(self):
        host,phases=packet();accepted=self.accept(host,phases)
        self.assertIs(accepted['default_conditions_disabled_synthetic_restore_qualified'],True)
        self.assertIs(accepted['ordinary_default_supervisor_restore_qualified'],False)
        for key in c.DEFAULT_RECEIPT_BOOL_KEYS:
            changed=copy.deepcopy(host);changed['default_restore_conditions'][key]=not changed['default_restore_conditions'][key]
            with self.subTest(key=key),self.assertRaises(Exception):self.accept(changed,phases)
        for name in phases:
            changed=copy.deepcopy(phases);changed[name]['closed_boot_grant_verified']=False
            with self.subTest(phase=name),self.assertRaises(Exception):self.accept(host,changed)
        changed=copy.deepcopy(host);changed['default_restore_conditions']['jobs_option_mutation_requests']=1
        with self.assertRaises(Exception):self.accept(changed,phases)

    def test_get_only_client_has_stdin_token_two_fixed_GETs_and_no_mutation_routes(self):
        self.assertNotIn('POST',c.DEFAULT_API_CLIENT);self.assertNotIn('jobs/options',c.DEFAULT_API_CLIENT)
        token='PRIVATE_SYNTHETIC_TOKEN_CANARY'
        stub='#!'+sys.executable+"\nimport sys,json,os\nargs=sys.argv[1:];header=sys.stdin.read();print(json.dumps({'args':args,'auth':header.startswith('Authorization: Bearer '+os.environ['SUPERVISOR_TOKEN']+'\\n'),'secret_in_argv':any(os.environ['SUPERVISOR_TOKEN'] in a for a in args)}))\n"
        with tempfile.TemporaryDirectory() as raw:
            curl=Path(raw)/'curl';curl.write_text(stub);curl.chmod(0o700)
            env={'PATH':raw+':'+os.defpath,'SUPERVISOR_TOKEN':token}
            for action in ('info','network'):
                result=subprocess.run(['/bin/sh','-s','--',action],input=c.DEFAULT_API_CLIENT.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=5,check=False)
                self.assertEqual(result.returncode,0);value=json.loads(result.stdout)
                self.assertEqual(value['args'][0],'-q');self.assertEqual(value['args'][value['args'].index('--request')+1],'GET')
                self.assertIs(value['auth'],True);self.assertIs(value['secret_in_argv'],False);self.assertNotIn(token,result.stdout.decode())
                self.assertNotIn('-L',value['args']);self.assertEqual(value['args'][-1],'http://supervisor/'+('jobs/info' if action=='info' else 'network/info'))
            for action,secret in [('apply',token),('clear',token),('info',''),('info',token+'\nBAD')]:
                result=subprocess.run(['/bin/sh','-s','--',action],input=c.DEFAULT_API_CLIENT.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**env,'SUPERVISOR_TOKEN':secret},timeout=5,check=False)
                self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertEqual(result.stderr,b'')

    def test_actual_network_readiness_wait_requires_two_exact_booleans_and_is_bounded(self):
        def run(values):
            host=c.Controller.__new__(c.Controller);host.deadline=1000.;clock=[100.];calls=[]
            def api(action,deadline):
                calls.append(action);data=values[min(len(calls)-1,len(values)-1)]
                return {'exitcode':0,'signal':None,'stdout':c.canonical({'result':'ok','data':data}),'stderr':b'','truncated':False}
            host.default_api=api;record=c.new_default_receipt()
            with patch.object(c.time,'monotonic',lambda:clock[0]),patch.object(c.time,'sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds)):
                host.wait_default_internet(record)
            return calls,record
        calls,receipt=run([{'host_internet':False,'supervisor_internet':None},{'host_internet':True,'supervisor_internet':True}])
        self.assertEqual(calls,['network','network']);self.assertEqual(receipt['network_info_requests'],2)
        for data in ({'host_internet':True,'supervisor_internet':False},{'host_internet':1,'supervisor_internet':True},{}):
            with self.subTest(data=data),self.assertRaises(c.Refused):run([data])

    def test_actual_one_use_grant_missing_wait_valid_consume_and_reuse_refuse(self):
        namespace=grant_functions();request=request_fixture(namespace)
        with tempfile.TemporaryDirectory() as raw:
            control=Path(raw);path=control/'closed-boot-grant.json';consume=namespace['consume_closed_boot_grant']
            self.assertIs(consume(control,request),False)
            path.write_bytes(c.canonical({**request,'external_network_closed':True,'default_conditions_verified':True}));path.chmod(0o600)
            self.assertIs(consume(control,request),True);self.assertFalse(path.exists());self.assertIs(consume(control,request),False)

    def test_actual_grant_refuses_stale_process_nonce_phase_source_shapes_and_unsafe_private_paths(self):
        namespace=grant_functions();request=request_fixture(namespace);consume=namespace['consume_closed_boot_grant'];valid={**request,'external_network_closed':True,'default_conditions_verified':True}
        with tempfile.TemporaryDirectory() as raw:
            control=Path(raw);path=control/'closed-boot-grant.json'
            for key,value in [('token','f'*32),('source_commit','f'*40),('branch_commit','f'*40),('generation','after_restore'),('phase','mutated_disabled'),('boot_nonce','f'*32),('process',{'pid':4321,'start_ticks':1233}),('external_network_closed',False),('default_conditions_verified',False),('schema',True),('extra','PRIVATE_CANARY')]:
                path.write_bytes(c.canonical(dict(valid,**{key:value})));path.chmod(0o600)
                with self.subTest(key=key),self.assertRaises(Exception):consume(control,request)
                self.assertTrue(path.exists());path.unlink()
            path.write_bytes(c.canonical(valid));path.chmod(0o644)
            with self.assertRaises(Exception):consume(control,request)
            path.unlink();path.symlink_to(control/'absent')
            with self.assertRaises(Exception):consume(control,request)

    def test_automatic_and_phase_dispatch_wait_for_grant_before_all_private_calls(self):
        tree=ast.parse((ROOT/'guest_helper/homecircle_safe_restore_qa/__init__.py').read_bytes())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Rehearsal')
        poll=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='poll')
        text=ast.unparse(poll)
        self.assertLess(text.index('consume_closed_boot_grant'),text.index('observed_boot = True'))
        self.assertLess(text.index('consume_closed_boot_grant'),text.index('self.raw_snapshot'))
        self.assertLess(text.index('consume_closed_boot_grant'),text.index('guard_files'))
        self.assertLess(text.index('consume_closed_boot_grant'),text.index('await self.run'))
        self.assertIn('continue',text[text.index('consume_closed_boot_grant'):text.index('observed_boot = True')])

    def test_host_grant_is_exact_newer_request_and_never_regrants_unexpected_restart(self):
        host=c.Controller.__new__(c.Controller);host.config_path='/mnt/data/supervisor/homeassistant';host.phase_token='a'*32;host.generation='before_restore';host.args=SimpleNamespace(branch_commit='b'*40)
        host.phases=[{'process':{'start_ticks':1200}}];host.deadline=1000.;host.assert_network_closed=lambda:None;host.remaining=lambda n:n
        ns=grant_functions();request=request_fixture(ns);request['phase']='mutated_disabled';request['purpose']='phase'
        scripts=[];host.guest_read=lambda _:c.canonical(request);host.guest_write=lambda name,data:scripts.append(data)
        host.guest=lambda command,timeout: c.canonical({'schema':1,'grant_written':True}) if 'grant-closed-boot.py' in command else b''
        host.grant_closed_boot('mutated_disabled');self.assertEqual(len(scripts),1)
        self.assertIn(b'os.rename(t,p)',scripts[0]);self.assertNotIn(b'os.link',scripts[0])
        request['process']['start_ticks']=1200
        with patch.object(c.time,'monotonic',side_effect=[100,101,200]),patch.object(c.time,'sleep',lambda _:None),self.assertRaises(c.Refused):host.grant_closed_boot('mutated_disabled')
        self.assertEqual(len(scripts),1)

    def test_scope_and_default_window_precede_all_restored_guard_and_vault_observation(self):
        tree=ast.parse((ROOT/'controller.py').read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Controller');run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        calls=[n.func.attr for n in ast.walk(run) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='self']
        self.assertLess(calls.index('default_conditions_restore'),calls.index('restored_boot_barrier'))
        self.assertLess(calls.index('default_conditions_restore'),calls.index('fresh_restore_control'))
        self.assertFalse(hasattr(c.Controller,'experimental_offline_restore'))


    def test_actual_async_poll_absent_or_malformed_grant_blocks_every_boot_and_partial_restore_shape(self):
        cases=[('baseline_disabled',False),('baseline_disabled',True),('mutated_disabled',True),('mutated_disabled',False),('repaired_storage_disabled',True),('restart_disabled',True)]
        for name,baseline in cases:
            for mode in ('absent','invalid'):
                with self.subTest(name=name,baseline=baseline,mode=mode):
                    events=execute_poll(name,baseline,mode)
                    self.assertIn('request',events)
                    self.assertFalse({'baseline_private','pair_private','guard_private','run','barrier'}&set(events))

    def test_actual_async_poll_later_valid_grant_dispatches_only_after_wait_for_every_boot(self):
        for name,baseline in [('baseline_disabled',False),('baseline_disabled',True),('mutated_disabled',True),('mutated_disabled',False),('repaired_storage_disabled',True),('restart_disabled',True)]:
            with self.subTest(name=name,baseline=baseline):
                events=execute_poll(name,baseline,'later')
                self.assertLess(events.index('no_grant'),events.index('grant'))
                terminal='barrier' if name=='baseline_disabled' and baseline else 'run'
                self.assertLess(events.index('grant'),events.index(terminal));self.assertEqual(events.count(terminal),1)
                for private in ('baseline_private','pair_private','guard_private'):
                    if private in events:self.assertLess(events.index('grant'),events.index(private))

    def test_actual_async_poll_consumed_grant_cannot_authorize_changed_phase_in_same_process(self):
        events=execute_poll('mutated_disabled',False,'valid',change=True)
        self.assertEqual(events.count('run'),1);self.assertEqual(events.count('grant'),1)
        self.assertIn('refused',events)

    def test_actual_grant_writer_atomic_publish_has_no_two_link_window_or_consumer_readback_race(self):
        host=c.Controller.__new__(c.Controller);host.config_path='/mnt/data/supervisor/homeassistant';host.phase_token='a'*32;host.generation='before_restore';host.args=SimpleNamespace(branch_commit='b'*40)
        host.phases=[];host.deadline=1000.;host.assert_network_closed=lambda:None;host.remaining=lambda n:n
        ns=grant_functions();request=request_fixture(ns);request['purpose']='phase';scripts=[]
        host.guest_read=lambda _:c.canonical(request);host.guest_write=lambda name,data:scripts.append(data)
        host.guest=lambda command,timeout:c.canonical({'schema':1,'grant_written':True}) if 'grant-closed-boot.py' in command else b''
        host.grant_closed_boot('baseline_disabled')
        with tempfile.TemporaryDirectory() as raw:
            control=Path(raw);program=scripts[0].decode().replace(host.config_path+'/'+c.CONTROL,raw).replace('s.st_uid==0','s.st_uid=='+str(os.geteuid()))
            output=io.StringIO()
            with redirect_stdout(output):exec(compile(program,'<actual-exclusive-grant-writer>','exec'),{})
            self.assertEqual(json.loads(output.getvalue()),{'schema':1,'grant_written':True})
            path=control/'closed-boot-grant.json';self.assertEqual(path.stat().st_nlink,1);self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertIs(ns['consume_closed_boot_grant'](control,request),True);self.assertFalse(path.exists())


    def test_actual_preopen_program_requires_disabled_exact_config_and_selection_without_pair_or_guard_reads(self):
        self.assertEqual(execute_preopen(),{'schema':1,'verified':True})
        for fault in ('enabled','changed_config','title','selection','mode','symlink'):
            with self.subTest(fault=fault),self.assertRaises(Exception):execute_preopen(fault)
        text=ast.unparse(ast.parse((ROOT/'controller.py').read_bytes()))
        method=text[text.index('def verify_disabled_preopen'):text.index('def grant_closed_boot')]
        self.assertNotIn('session.key',method);self.assertNotIn('session.vault',method);self.assertNotIn('guard_fingerprint',method)

    def test_actual_archive_excludes_consumable_grant_and_temp_not_only_old_restore_barrier(self):
        for fault in ('grant','grant_temp'):
            with self.subTest(fault=fault),self.assertRaises(Exception):execute_archive(fault)


if __name__=="__main__":unittest.main()
