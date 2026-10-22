"""Ordinary Supervisor restore of exact HomeCircle bytes in a synthetic guest.

Only the separately frozen QA parent package intercepts provider transports.
The product manifest, HA requirement installer and Supervisor restore stay real.
No recovery-guard export, import, owner acknowledgment or repair is permitted.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import sys
import tarfile
import tempfile
import time
import zipfile

import legacy_controller as base
import control_publication
from legacy_controller import (CORE, HAOS_XZ_SHA, GUEST_ROOT, CONTROL, RESULTS,
    Refused, canonical, check_archive, digest_value, guest_staging_owner,
    project_default_receipt, project_recorder, require, sha, write_json,
    DEFAULT_API_CLIENT, JOB_OPTIONS_PERSISTENCE_PROGRAM, new_default_receipt)
from storage_context import Context as StorageContext

ROOT = Path(__file__).resolve().parent
PHASES = ('baseline_enabled', 'mutated_enabled', 'automatic_restored_enabled', 'restart_enabled')
PINS = json.loads((ROOT / 'candidate_binding.json').read_bytes())
SOURCE_COMMIT = PINS['source_commit']
CANDIDATE_SHA = PINS['candidate_sha256']
CANDIDATE_FILES = PINS['candidate_files']
base.PHASES = PHASES
base.SOURCE_COMMIT = SOURCE_COMMIT
base.CANDIDATE_SHA = CANDIDATE_SHA
base.ROOT = ROOT

_DIAGNOSTIC_ROOT=ROOT/'guest_helper/homecircle_safe_restore_qa'
_DIAGNOSTIC_SPEC=importlib.util.spec_from_file_location('_ordinary_fixed_failure',_DIAGNOSTIC_ROOT/'failure_diagnostics.py')
_DIAGNOSTICS=importlib.util.module_from_spec(_DIAGNOSTIC_SPEC)
_DIAGNOSTIC_SPEC.loader.exec_module(_DIAGNOSTICS)

def guest_failure_projection(receipt,phase):
    allowed=_DIAGNOSTICS.catalog(_DIAGNOSTIC_ROOT)
    stage=receipt.get('stage')
    stage=stage if type(stage) is str and stage in allowed['stages'] else 'unrecognized'
    details=_DIAGNOSTICS.checked({k:receipt.get(k) for k in ('failure_type','failure_code','frames')},_DIAGNOSTIC_ROOT)
    if stage=='normal_dependencies':
        details['dependency_metadata']=_DIAGNOSTICS.checked_metadata(receipt.get('dependency_metadata'),_DIAGNOSTIC_ROOT)
    else:
        require('dependency_metadata' not in receipt,'ordinary_failed_phase_metadata_scope')
    return {'schema':2,'phase':phase,'outcome':'failed','stage':stage,**details}


def checked_binding(value):
    require(type(value) is dict and set(value) == {'schema','prepared','source_commit',
        'candidate_sha256','candidate_files'} and type(value['schema']) is int and value['schema'] == 1
        and value['prepared'] is True and type(value['candidate_files']) is int
        and 100 <= value['candidate_files'] <= 128 and type(value['source_commit']) is str
        and re.fullmatch('[0-9a-f]{40}',value['source_commit'])
        and digest_value(value['candidate_sha256']), 'ordinary_candidate_binding_refused')
    return value


def phase_proof(value, inventory, name):
    require(value.get('qa_manifest_only_difference') is False
        and value.get('product_manifest_unchanged') is True
        and value.get('qa_manifest_sha256') == inventory['manifest.json']['sha256']
        and value.get('runtime_loaded_source_sha256') == inventory['__init__.py']['sha256']
        and all(value.get(k) is True for k in ('runtime_selection_checked','actual_findmy_session_restored',
            'synthetic_photo_preserved','static_served_bundle_matches')), 'ordinary_runtime_bytes_refused')
    dependencies = base.project_dependencies(value.get('normal_dependencies'), complete=True)
    boundary = value.get('startup_boundary')
    booleans = ('installed_before_product_import','patches_intact','deny_all_external_aiohttp',
        'python_socket_audit_installed','product_manifest_unchanged','normal_requirement_subprocesses_unmodified')
    counters = ('life360_sessions_created','life360_requests_denied','apple_legacy_requests_denied',
        'apple_bounded_requests_denied','apple_report_requests_denied','other_external_requests_denied',
        'recovery_before_dispatch_calls','recovery_command_calls','recovery_transport_attempts_denied',
        'supervisor_requests_allowed','qa_static_requests_allowed','socket_external_attempts_denied',
        'ordinary_uv_installs_observed')
    require(type(boundary) is dict and set(boundary) == {'schema','boundary_revision','loaded_target_kinds',*booleans,*counters}
        and type(boundary['schema']) is int and boundary['schema'] == 2
        and type(boundary['boundary_revision']) is int and boundary['boundary_revision'] == 2
        and all(boundary[k] is True for k in booleans)
        and boundary['loaded_target_kinds'] == sorted(('life360','legacy','bounded','report','guard','escrow'))
        and all(type(boundary[k]) is int and 0 <= boundary[k] <= 1000000 for k in counters)
        and boundary['life360_requests_denied'] >= 1 and boundary['life360_sessions_created'] >= 1
        and sum(boundary[k] for k in ('apple_legacy_requests_denied','apple_bounded_requests_denied',
            'apple_report_requests_denied')) >= 1
        and all(boundary[k] == 0 for k in ('recovery_before_dispatch_calls','recovery_command_calls',
            'recovery_transport_attempts_denied')), 'ordinary_startup_boundary_refused')
    if name in {'baseline_enabled','automatic_restored_enabled'}:
        require(boundary['ordinary_uv_installs_observed'] >= 1, 'ordinary_managed_installer_positive_control')
    restored = name in PHASES[2:]
    counter = 3 if name == 'mutated_enabled' else 2
    guard = value.get('recovery_guard')
    expected = {'identity_matches_saved_sdk_account':True,'counter':counter,
        'blocked':restored or counter >= 3, 'review_required':restored,'witness_absent':restored,
        'attempt_refused_before_body':restored,'manual_guard_imports':0,'owner_acknowledgments_after_restore':0}
    require(type(guard) is dict and guard == expected
        and all(type(guard[k]) is type(v) for k,v in expected.items()), 'ordinary_guard_proof_refused')
    return {'normal_dependencies': dependencies, 'startup_boundary':boundary, 'recovery_guard':guard,
        'product_manifest_unchanged':True,'unchanged_product_members':len(inventory),
        'actual_findmy_session_restored':True,'runtime_selection_checked':True,
        'synthetic_photo_preserved':True,'static_served_bundle_matches':True}


class Controller(base.Controller):
    def __init__(self,args):
        super().__init__(args)
        self.normal_initial_window = None
        self.guest_failures = []

    def prepare_dependencies(self):
        raise Refused('ordinary_prepared_dependency_install_forbidden')

    def preserve_latest_guard(self):
        raise Refused('ordinary_guard_export_forbidden')

    def fresh_restore_control(self):
        raise Refused('ordinary_guard_import_or_repair_forbidden')

    def prepare(self, inventory):
        self.stage = 'ordinary_disposable_configuration'
        self.stop_core()
        staging = self.private/'guest-staging'
        staging.mkdir(mode=0o700)
        components=staging/'custom_components'
        shutil.copytree(ROOT/'guest_helper',components,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
        with zipfile.ZipFile(self.args.candidate_zip) as archive:
            archive.extractall(components/'homecircle')
        manifest=json.loads((components/'homecircle/manifest.json').read_bytes())
        require('homecircle_safe_restore_qa' not in manifest['dependencies'], 'ordinary_qa_dependency_forbidden')
        archive_path=self.private/'guest-staging.tgz'
        with tarfile.open(archive_path,'w:gz',format=tarfile.PAX_FORMAT) as archive:
            archive.add(components,arcname='custom_components',filter=guest_staging_owner)
        raw=archive_path.read_bytes()
        self.guest_write(GUEST_ROOT+'/staging.tgz',raw)
        require(self.guest('sha256sum '+GUEST_ROOT+'/staging.tgz',30).split()[0].decode()==sha(raw),'ordinary_stage_transport')
        self.guest('set -eu; umask 077; tar -xzf '+GUEST_ROOT+'/staging.tgz -C '+self.config_path
            +'; mkdir -m 700 '+self.config_path+'/'+CONTROL+' '+self.config_path+'/'+RESULTS,60)
        self.inputs={'schema':1,'candidate_sha256':CANDIDATE_SHA,'candidate_inventory':inventory,'core_version':CORE,
            'branch_commit':self.args.branch_commit,'generation':self.generation,'source_commit':SOURCE_COMMIT,
            'dependency_fixture':None,'dependency_inventory':None,
            'helper_files_sha256':self.provenance['helper_files_sha256'],
            'storage_source_sha256':{n:inventory[n]['sha256'] for n in
                ('findmy_vault.py','findmy_identity.py','findmy_recovery_guard.py')}}
        config={'homeassistant':{'name':'Disposable ordinary HomeCircle restore QA','latitude':0.0,'longitude':0.0,
            'elevation':0,'unit_system':'metric','time_zone':'UTC'},'frontend':{},'http':{},'lovelace':{},'person':{},
            'zone':[{'name':'Example Saved Storage','latitude':0.01,'longitude':0.01,'radius':50}],
            'websocket_api':{},'image_upload':{},'backup':{},'recorder':{},'hassio':{},
            'homecircle_safe_restore_qa':{'disposable':True}}
        self.inputs['qa_configuration_sha256']=sha(canonical(config))
        self.guest_write(self.config_path+'/'+CONTROL+'/inputs.json',canonical(self.inputs))
        self.guest_write(self.config_path+'/configuration.yaml',canonical(config))
        self.guest('chmod 600 '+self.config_path+'/configuration.yaml '+self.config_path+'/'+CONTROL
            +'/inputs.json; rm '+GUEST_ROOT+'/staging.tgz',30)
        self.verify_candidate()

    def verify_candidate(self):
        target=self.config_path+'/custom_components/homecircle'
        actual=self.guest("find "+target+" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | LC_ALL=C sort",30).decode().splitlines()
        expected=self.inventories['candidate']
        require(actual==[target+'/'+name for name in sorted(expected)],'ordinary_product_member_set')
        for name,metadata in expected.items():
            require(sha(self.guest_read(target+'/'+name))==metadata['sha256'],'ordinary_exact_product_bytes')
        for name,digest in self.provenance['helper_files_sha256'].items():
            require(sha(self.guest_read(self.config_path+'/custom_components/'+name))==digest,'ordinary_environment_helper_bytes')
        self.direct_installs=1

    def publish_inputs(self):
        self.assert_network_closed()
        control=self.config_path+'/'+CONTROL
        temporary_name='.inputs-atomic-'+secrets.token_hex(16)
        temporary=control+'/'+temporary_name
        self.guest('test ! -e '+temporary+' && test ! -L '+temporary,15)
        raw=canonical(self.inputs)
        self.guest_write(temporary,raw)
        self.guest('chmod 600 '+temporary,15)
        program=(ROOT/'control_publication.py').read_bytes()
        self.guest_write(GUEST_ROOT+'/publish-inputs.py',program)
        require(self.guest_read(GUEST_ROOT+'/publish-inputs.py')==program,'ordinary_atomic_input_program_binding')
        result=json.loads(self.guest('/usr/bin/docker exec -i hassio_supervisor python3 -B - '
            +temporary_name+' '+sha(raw)+' < '+GUEST_ROOT+'/publish-inputs.py',30))
        require(result==control_publication.RESULT,'ordinary_atomic_input_publication_refused')

    def boot_request_ready(self, previous, maximum=660):
        limit=time.monotonic()+self.remaining(maximum)
        while time.monotonic()<limit:
            try:
                value=json.loads(self.guest_read(self.config_path+'/'+CONTROL+'/boot-request.json'))
            except (Refused,OSError,ValueError):
                time.sleep(1);continue
            process=value.get('process') if type(value) is dict else None
            if type(process) is dict and type(process.get('start_ticks')) is int and process['start_ticks']>previous:
                require(value.get('source_commit')==SOURCE_COMMIT and value.get('candidate_sha256')==CANDIDATE_SHA
                    and value.get('token')==self.phase_token and value.get('branch_commit')==self.args.branch_commit,
                    'ordinary_boot_request_identity')
                return value
            time.sleep(1)
        raise Refused('ordinary_normal_requirements_boot_deadline')

    def initial_managed_boot(self):
        require(self.network_boundary['link_closed'] and not self.phases,'ordinary_initial_window_order')
        record={'opened':False,'closed':False,'normal_ha_requirement_install':True,'maximum_seconds':750}
        self.normal_initial_window=record
        original_deadline=self.deadline
        require(original_deadline-time.monotonic()>750, 'ordinary_initial_window_cleanup_reserve')
        self.deadline=time.monotonic()+660
        try:
            self.set_restore_network_link(True)
            self.network_boundary['link_closed']=False
            record['opened']=True
            self.network_transitions.append('opened_for_ordinary_requirements')
            require(self.connectivity_probe() is True,'ordinary_initial_internet_positive_control')
            self.start_core()
            self.boot_request_ready(0)
        finally:
            self.deadline=min(original_deadline,time.monotonic()+90)
            try:
                if record['opened']:
                    self.set_restore_network_link(False)
                    self.network_boundary['link_closed']=True
                    self.assert_network_closed()
                    record['closed']=True
                    self.network_transitions.append('closed_after_ordinary_requirements')
            finally:
                self.deadline=original_deadline
        require(record['closed'],'ordinary_initial_window_cleanup')

    def phase(self,name,start=False):
        require(name in PHASES and name==PHASES[len(self.phases)] and name!='automatic_restored_enabled','ordinary_phase_order')
        self.assert_network_closed()
        self.stage=name
        instruction={'schema':1,'token':self.phase_token,'phase':name,'generation':self.generation,'branch_commit':self.args.branch_commit}
        self.guest_write(self.config_path+'/'+CONTROL+'/phase.json',canonical(instruction))
        self.guest('chmod 600 '+self.config_path+'/'+CONTROL+'/phase.json',15)
        if name=='baseline_enabled':self.initial_managed_boot()
        elif start:self.start_core()
        self.grant_closed_boot(name)
        limit=time.monotonic()+self.remaining(660)
        while time.monotonic()<limit:
            try:receipt=json.loads(self.guest_read(self.config_path+'/'+RESULTS+'/'+name+'.json'))
            except (Refused,OSError,ValueError):time.sleep(1);continue
            require(type(receipt) is dict and type(receipt.get('schema')) is int and receipt['schema']==1
                and receipt.get('token')==self.phase_token and receipt.get('phase')==name
                and receipt.get('generation')==self.generation and receipt.get('branch_commit')==self.args.branch_commit,
                'ordinary_phase_receipt_identity_refused')
            if receipt.get('outcome')!='passed':
                public=guest_failure_projection(receipt,name)
                self.guest_failures.append(public)
                write_json(self.public/(name+'.json'),public)
                raise Refused('ordinary_guest_phase_failed')
            public=self.accept_phase(name,receipt)
            self.raw_phase_receipts[name]=receipt
            write_json(self.public/(name+'.json'),public)
            self.phases.append(public)
            self.assert_network_closed()
            return
        raise Refused('ordinary_phase_receipt_deadline')

    def accept_phase(self,name,receipt):
        inventory=self.inventories['candidate']
        require(type(receipt) is dict and receipt.get('core_version')==CORE
            and receipt.get('candidate_archive_sha256')==CANDIDATE_SHA
            and all(receipt.get(k) is True for k in ('entry_loaded','candidate_imported','ha_config_entry_saved',
                'closed_boot_grant_verified','provider_request_attempt_counts_measured','recovery_proof_attempt_counts_measured'))
            and receipt.get('entry_disabled') is False and receipt.get('owner_accounts_used',False) is False
            and receipt.get('production_configuration_used',False) is False
            and type(receipt.get('package_files_count')) is int and receipt['package_files_count']==len(inventory)
            and receipt.get('package_payload_sha256')==sha(canonical(inventory)),'ordinary_phase_scope_refused')
        extra=phase_proof(receipt,inventory,name)
        process=receipt.get('process')
        require(type(process) is dict and set(process)=={'pid','start_ticks'}
            and all(type(v) is int and v>0 for v in process.values())
            and (not self.phases or process['start_ticks']>self.phases[-1]['process']['start_ticks']),'ordinary_distinct_core_process')
        expected=self.storage_proof['mutation'] if name=='mutated_enabled' else self.storage_proof['baseline']
        require(receipt.get('observed_storage')=={k:expected[k] for k in base.RAW_STORAGE_FIELDS},'ordinary_saved_storage_match')
        joins=receipt.get('joins_sha256')
        require(digest_value(joins) and digest_value(receipt.get('guard_sha256')),'ordinary_guard_join_fingerprint')
        if name=='baseline_enabled':
            self.joins_sha256=joins;self.backup_guard_sha256=receipt['guard_sha256']
        elif name=='mutated_enabled':
            require(joins!=self.joins_sha256 and receipt['guard_sha256']!=self.backup_guard_sha256,'ordinary_discriminating_mutation')
            self.latest_guard_sha256=receipt['guard_sha256']
        else:
            require(joins==self.joins_sha256 and receipt['guard_sha256']==self.backup_guard_sha256,'ordinary_restored_old_bytes')
        history=project_recorder(receipt.get('recorder'))
        if self.phases:
            require(history['prebackup_rows']==self.phases[0]['recorder']['prebackup_rows']
                and history['prebackup_sha256']==self.phases[0]['recorder']['prebackup_sha256'],'ordinary_recorder_baseline')
        if name=='mutated_enabled':require(history['postbackup_marker_rows']>0 and history['postbackup_marker_absent'] is False,'ordinary_history_mutation')
        else:require(history['postbackup_marker_rows']==0 and history['postbackup_marker_absent'] is True,'ordinary_removed_postbackup_markers')
        if name in PHASES[2:]:
            require(history['postrestore_exact_match'] is True and type(history['postrestore_rows']) is int
                and history['postrestore_rows']>0,'ordinary_postrestore_rows')
        if name=='restart_enabled':
            require(all(history[k]==self.phases[2]['recorder'][k] for k in ('postrestore_rows','postrestore_sha256')),'ordinary_history_restart_continuity')
        return {'schema':2,'phase':name,'outcome':'passed','generation':self.generation,'process':process,
            'entry_loaded':True,'entry_disabled':False,'candidate_imported':True,'ha_config_entry_saved':True,
            'closed_boot_grant_verified':True,'storage_raw_matches_expected':True,'selected_registry_joins':4,
            'explicit_registry_joins_checked':True,'guard_counter':extra['recovery_guard']['counter'],
            'recorder':history,**extra}

    def inspect_backup(self):
        self.stage = "supervisor_saved_storage_archive_proof"
        require(self.storage_proof is not None and self.storage_proof["mutation"] is None
                and self.joins_sha256 is not None, "baseline_before_archive_required")
        script = 'import hashlib,json,re,tarfile\nfrom pathlib import Path,PurePosixPath\n\ndef require(ok):\n    if not ok: raise RuntimeError("saved_storage_archive_refused")\ndef sha(data): return hashlib.sha256(data).hexdigest()\ndef canonical(data): return json.dumps(data,sort_keys=True,separators=(",",":")).encode()\nexpected=__BASELINE__\nexpected_joins=__JOINS__\nroot=Path("/data/homeassistant")\ninputs=json.loads((root/"homecircle-safe-restore-qa-control/inputs.json").read_bytes())\npath=Path("/data/backup/homecircle-safe-restore-qa.tar")\nrequire(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<=128*1024**2)\npackage,guard,pairs,private={}, {}, {}, {}\ndeps={}\nhelper={}\nconfiguration=None\nphoto=None\nimage_record=None\narchive_manifest=None\nentry=selection=registry=None\ndb=False\nwith tarfile.open(path,"r:") as outer:\n    members=outer.getmembers()\n    require(len(members)<=16 and all(not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members))\n    inner=[m for m in members if m.name.removeprefix("./")=="homeassistant.tar"]\n    require(len(inner)==1 and inner[0].isfile() and inner[0].size<=128*1024**2)\n    with outer.extractfile(inner[0]) as stream,tarfile.open(fileobj=stream,mode="r|") as archive:\n        count,total=0,0\n        for member in archive:\n            count+=1\n            require(count<=16384 and member.size<=64*1024**2)\n            name=member.name.removeprefix("./")\n            require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts and not member.issym() and not member.islnk())\n            require(name not in {"data/homecircle-safe-restore-qa-control/startup-install-failure.json", "data/homecircle-safe-restore-qa-control/restore-barrier.json", "data/homecircle-safe-restore-qa-control/closed-boot-grant.json", "data/homecircle-safe-restore-qa-control/closed-boot-grant.tmp"})\n            if not member.isfile(): continue\n            total+=member.size\n            require(total<=256*1024**2)\n            with archive.extractfile(member) as content:data=content.read(64*1024**2+1)\n            require(len(data)==member.size)\n            require(not name.startswith("data/.cache/"))\n            if name.startswith("data/deps/"):\n                relative=name[len("data/deps/"):]\n                if "__pycache__" in relative.split("/"):\n                    require(relative.endswith(".pyc"))\n                else:\n                    require(member.uid==0 and relative not in deps)\n                    deps[relative]={"bytes":len(data),"sha256":sha(data)}\n            if name=="data/configuration.yaml":configuration=data\n            if name=="data/.storage/image":image_record=json.loads(data)\n            if name=="data/image/cccccccccccccccccccccccccccccccc/original":\n                require(member.uid==0 and member.mode==0o600)\n                photo=data\n            qa="data/custom_components/"\n            if name.startswith(qa) and not name.startswith(qa+"homecircle/") and "__pycache__" not in name and not name.endswith(".pyc"):\n                key=name[len(qa):]\n                require(key not in helper)\n                helper[key]=sha(data)\n            prefix="data/custom_components/homecircle/"\n            if name.startswith(prefix) and "__pycache__" not in name and not name.endswith(".pyc"):\n                package[name[len(prefix):]]={"bytes":len(data),"sha256":sha(data)}\n                if name==prefix+"manifest.json":archive_manifest=data\n            prefix="data/.storage/homecircle_findmy/recovery_guard/"\n            if name.startswith(prefix):guard[name[len(prefix):]]={"bytes":len(data),"sha256":sha(data)}\n            if name.startswith("data/.storage/homecircle_findmy/homecircle_accounts/"):\n                require(re.fullmatch(r"data/[.]storage/homecircle_findmy/homecircle_accounts/[0-9a-f]{32}/session[.](?:key|vault)",name)\n                        and member.mode==0o600 and member.uid==0 and name not in pairs)\n                pairs[name]=sha(data)\n            if name=="data/.storage/core.config_entries":\n                entries=json.loads(data)["data"]["entries"]\n                found=[e for e in entries if e.get("domain")=="homecircle"]\n                require(len(found)==1 and found[0].get("disabled_by") is None and found[0].get("title")=="Synthetic saved storage verified")\n                entry=found[0]\n            if name=="data/.storage/core.entity_registry":registry=json.loads(data)["data"]["entities"]\n            if name=="data/homecircle-safe-restore-qa-control/storage-selection-private.json":selection=json.loads(data)\n            if name=="data/home-assistant_v2.db":\n                require(data[:16]==b"SQLite format 3\\x00" and len(data)>4096);db=True\nexpected_package=inputs["candidate_inventory"]\nrequire(package==expected_package and entry is not None and db and guard and selection is not None and type(registry)is list)\nrequire(sha(archive_manifest)==expected_package[\'manifest.json\'][\'sha256\'])\nrequire(\'homecircle_safe_restore_qa\' not in json.loads(archive_manifest)[\'dependencies\'])\nrequire(entry["data"]==entry["options"] and sha(canonical({"data":entry["data"],"options":entry["options"]}))==expected["config_sha256"])\nrequire(sha(canonical(entry["options"]["life360_account"]))==expected["credentials_sha256"] and sha(canonical(selection))==expected["selection_sha256"])\nrequire(type(selection)is dict and set(selection)=={"schema","entry_id","joins"} and selection["schema"]==1 and selection["entry_id"]==entry["entry_id"]\n        and type(selection["joins"])is list and len(selection["joins"])==4)\nselected=sorted([{k:v[k] for k in ("entity_id","unique_id","config_entry_id")} for v in selection["joins"]],key=lambda x:x["entity_id"])\nrequire(len({v["entity_id"] for v in selected})==len({v["unique_id"] for v in selected})==4 and all(v["config_entry_id"]==entry["entry_id"] for v in selected))\nactual=sorted([{k:v.get(k) for k in ("entity_id","unique_id","config_entry_id")} for v in registry if v.get("entity_id") in {j["entity_id"] for j in selected}],key=lambda x:x["entity_id"])\nrequire(actual==selected and sha(canonical(actual))==expected_joins)\naccounts=entry["options"]["findmy_accounts"]\nrequire(type(accounts)is dict and len(accounts)==1)\nstorage_id=next(iter(accounts.values()))["storage_id"]\nrequire(type(storage_id)is str and re.fullmatch("[0-9a-f]{32}",storage_id))\nprefix="data/.storage/homecircle_findmy/homecircle_accounts/"+storage_id+"/"\nrequire(pairs=={prefix+"session.key":expected["key_sha256"],prefix+"session.vault":expected["vault_sha256"]})\nrequire(photo is not None and len(photo)==72 and sha(photo)=="3a51cbff9fe4d3958488319741b290925e0a0e22447ef2a03309427cfc7d3f0d")\nrequire(type(image_record)is dict and image_record.get("key")=="image" and image_record.get("version")==1\n    and image_record.get("data")=={"items":[{"id":"c"*32,"filesize":len(photo),"content_type":"image/png","name":"synthetic.png","uploaded_at":"2026-01-01T00:00:00+00:00"}]})\nrequire(helper==inputs["helper_files_sha256"] and configuration is not None and sha(configuration)==inputs["qa_configuration_sha256"])\nrequire(json.loads(configuration)["homecircle_safe_restore_qa"]=={"disposable":True})\nrequire(not deps and inputs["dependency_fixture"] is None and inputs["dependency_inventory"] is None)\nprint(json.dumps({"saved_photo_bytes_included":True,"qa_startup_boundary_archive_verified":True,"no_prepared_dependency_bytes":True,"product_manifest_unchanged":True,"cache_witness_excluded":True,"archive_bytes":path.stat().st_size,"database_included":True,"candidate_match":True,"enabled_entry":True,\n    "saved_pair_included":True,"saved_config_included":True,"saved_selection_included":True,"saved_registry_joins_included":True,\n    "guard_sha256":sha(canonical(guard))},sort_keys=True))\n\n'
        script = script.replace("__BASELINE__", repr(self.storage_proof["baseline"])).replace("__JOINS__", repr(self.joins_sha256))
        self.guest_write(GUEST_ROOT + "/inspect-backup.py", script.encode())
        value = json.loads(self.guest("/usr/bin/docker exec -i hassio_supervisor python3 - < " + GUEST_ROOT + "/inspect-backup.py", 120))
        keys = {"saved_photo_bytes_included", "qa_startup_boundary_archive_verified", "no_prepared_dependency_bytes", "product_manifest_unchanged", "cache_witness_excluded", "archive_bytes", "database_included", "candidate_match", "enabled_entry", "saved_pair_included",
                "saved_config_included", "saved_selection_included", "saved_registry_joins_included", "guard_sha256"}
        require(type(value) is dict and set(value)==keys and all(value[key] is True for key in keys-{"archive_bytes","guard_sha256"})
                and value["guard_sha256"]==self.backup_guard_sha256 and type(value["archive_bytes"])is int
                and 0<value["archive_bytes"]<=128*1024**2, "saved_storage_archive_proof_refused")
        self.backup["archive"] = value


    def default_conditions_restore(self):
        self.stage = 'default_conditions_preflight'
        record = new_default_receipt()
        self.default_restore_conditions = record
        original_deadline = self.deadline
        require(original_deadline-time.monotonic() > 180, 'default_cleanup_reserve_required')
        self.deadline = original_deadline-90
        attempted = False
        try:
            self.assert_network_closed(); record['network_closed_before'] = True
            require(self.core_container_state(min(10,self.remaining(10))) == 'stopped', 'default_restore_core_must_be_stopped')
            require(self.backup is not None and self.backup.get('homeassistant_version') == CORE
                and type(self.backup.get('archive')) is dict
                and all(self.backup['archive'].get(key) is True for key in ('candidate_match','enabled_entry','database_included','saved_photo_bytes_included','qa_startup_boundary_archive_verified','no_prepared_dependency_bytes','product_manifest_unchanged','cache_witness_excluded',
                    'saved_pair_included','saved_config_included','saved_selection_included','saved_registry_joins_included')),
                'default_same_core_local_archive_required')
            self.verify_candidate(); record['candidate113_archive_verified'] = True
            require(self.actual_core_image() == self.minimum_core_image, 'default_cached_image_before_refused')
            record['cached_same_core_image_verified_before'] = True
            self.verify_enabled_preopen(); record['enabled_instrumented_config_verified'] = True
            for name,raw in (('job-options-client.sh',DEFAULT_API_CLIENT.encode()),('job-options-persist.py',JOB_OPTIONS_PERSISTENCE_PROGRAM.encode())):
                self.guest_write(GUEST_ROOT+'/'+name,raw)
                require(self.guest_read(GUEST_ROOT+'/'+name) == raw, 'default_readonly_source_refused')
            state,idle = self.default_effective_state(self.deadline)
            persisted = self.default_persisted_state(self.deadline)
            record['foreign_options_refused'] = state != 'empty' or persisted not in {'empty','absent'}
            require(state == 'empty' and persisted in {'empty','absent'}, 'default_original_options_must_be_empty')
            require(idle, 'default_relevant_visible_jobs_must_be_idle')
            record.update(original_effective_empty=True,original_persisted_empty_or_absent=True,relevant_visible_jobs_idle_before=True)
            self.stage = 'default_restore_network_open'
            attempted = True; record['network_open_requests'] = 1
            self.set_restore_network_link(True)
            record['network_open_acknowledged'] = True
            self.network_boundary['link_closed'] = False
            require(self.connectivity_probe() is True, 'default_network_positive_control_required')
            record['network_open_positive_control'] = True
            self.network_transitions.append('opened_for_default_restore')
            self.wait_default_internet(record)
            self.backup_operation(restore=True)
            self.boot_request_ready(self.phases[-1]['process']['start_ticks'])
            record['restore_completed'] = True
        finally:
            previous_stage = self.stage
            self.deadline = original_deadline
            if attempted:
                self.stage = 'default_restore_network_close'
                cleanup_deadline = min(original_deadline,time.monotonic()+90)
                self.deadline = cleanup_deadline
                try:
                    record['network_close_requests'] = 1
                    try:
                        self.set_restore_network_link(False)
                        record['network_close_acknowledged'] = True
                    except Exception:
                        pass
                    connected = self.connectivity_probe()
                    self.qga.call('guest-ping')
                    require(record['network_close_acknowledged'] and connected is False, 'default_network_close_unproven')
                    self.network_boundary.update(link_closed=True,closed_probe_connected=False,guest_agent_remained_available=True)
                    self.network_boundary['closed_probe_observations'] = self.network_boundary.get('closed_probe_observations',0)+1
                    record['network_closed_after'] = True
                    self.network_transitions.append('closed_after_default_restore')
                    state,_idle = self.default_effective_state(cleanup_deadline)
                    persisted = self.default_persisted_state(cleanup_deadline)
                    record['foreign_options_refused'] = state != 'empty' or persisted not in {'empty','absent'}
                    require(state == 'empty' and persisted in {'empty','absent'}, 'default_final_options_not_empty')
                    record.update(final_effective_empty_observed=True,final_persisted_empty_or_absent=True)
                    require(time.monotonic() <= cleanup_deadline, 'default_network_cleanup_deadline_exceeded')
                except BaseException:
                    record['cleanup_failed'] = True
                    raise Refused('default_network_cleanup_failed') from None
                finally:
                    self.deadline = original_deadline
                self.stage = previous_stage
        require(record['restore_completed'] and record['network_closed_after'] and record['final_effective_empty_observed']
            and record['final_persisted_empty_or_absent'], 'default_window_must_close_before_private_reads')
        require(self.actual_core_image() == self.minimum_core_image, 'default_cached_image_after_refused')
        record['cached_same_core_image_verified_after'] = True
        self.verify_candidate()
        self.inputs.update(external_proof=self.external_proof,backup_guard_sha256=self.backup_guard_sha256,latest_guard_sha256=self.latest_guard_sha256,expected_joins_sha256=self.joins_sha256)
        self.publish_inputs()
        self.grant_closed_boot('automatic_restored_enabled')
        record['closed_boot_grant_written'] = True
        project_default_receipt(record,complete=True)

    def verify_enabled_preopen(self):
        require(len(self.phases)==2 and self.phases[-1]['phase']=='mutated_enabled'
            and self.phases[-1]['recovery_guard']['counter']==3
            and self.phases[-1]['recovery_guard']['blocked'] is True
            and self.host_guard_retained,'ordinary_mutated_guard_before_restore')
        self.verify_candidate()

    def restored_boot_barrier(self):
        require(len(self.phases)==2 and self.network_boundary['link_closed'],'ordinary_first_restored_order')
        self.stage='automatic_restored_enabled'
        limit=time.monotonic()+self.remaining(240)
        while time.monotonic()<limit:
            try:value=json.loads(self.guest_read(self.config_path+'/'+CONTROL+'/restore-barrier.json'))
            except (Refused,OSError,ValueError):time.sleep(1);continue
            require(type(value) is dict and type(value.get('schema')) is int and value['schema']==1
                and value.get('token')==self.phase_token and value.get('phase')=='automatic_restored_enabled'
                and value.get('generation')=='before_restore'
                and value.get('branch_commit')==self.args.branch_commit,'ordinary_first_restored_identity')
            process=value.get('process')
            require(type(process) is dict and set(process)=={'pid','start_ticks'}
                and all(type(v) is int and v>0 for v in process.values())
                and process['start_ticks']>self.phases[-1]['process']['start_ticks'],'ordinary_first_restored_process_identity')
            if value.get('outcome')!='passed':
                require(type(value.get('closed_boot_grant_verified')) is bool,'ordinary_failed_automatic_grant_type')
                public={**guest_failure_projection(value,'automatic_restored_enabled'),'process':dict(process),
                    'closed_boot_grant_verified':value['closed_boot_grant_verified']}
                self.guest_failures.append(public)
                write_json(self.public/'automatic_restored_enabled.json',public)
                raise Refused('ordinary_guest_automatic_phase_failed')
            self.after_restore_barrier=True
            public=self.accept_phase('automatic_restored_enabled',value)
            self.raw_phase_receipts['automatic_restored_enabled']=value
            write_json(self.public/'automatic_restored_enabled.json',public)
            self.phases.append(public)
            return
        raise Refused('ordinary_automatic_restored_receipt_deadline')

    def run_storage_context(self,action):
        require(action in base.STORAGE_ACTIONS and [i['action'] for i in self.storage_contexts]
            ==list(base.STORAGE_ACTIONS[:base.STORAGE_ACTIONS.index(action)]),'ordinary_storage_action_order')
        self.assert_network_closed()
        if action.startswith('validate_'):
            require(self.after_restore_barrier and self.generation=='after_restore','ordinary_guard_block_before_offline_storage')
        transfer=(ROOT/'storage_transfer.py').read_bytes()
        self.guest_write(GUEST_ROOT+'/storage-transfer.py',transfer)
        require(self.guest_read(GUEST_ROOT+'/storage-transfer.py')==transfer,'ordinary_storage_source')
        job={'schema':1,'action':action,'token':self.phase_token,'generation':self.generation,'branch_commit':self.args.branch_commit}
        control=self.config_path+'/'+CONTROL
        self.guest_write(control+'/storage-job.json',canonical(job))
        self.guest('chmod 600 '+control+'/storage-job.json',15)
        context=StorageContext(self.guest,self.nonce,action,(self.phase_token,self.generation,self.args.branch_commit),maximum_seconds=self.remaining(60))
        try:
            result=context.run()
            require(result['exitcode']==0 and result['stderr']==b'' and result['truncated'] is False,'ordinary_storage_context_refused')
            public=json.loads(result['stdout'])
            expected_checks={**dict.fromkeys(('actual_fernet','account_identity_bound','selection_and_ledger_bound',
                'pair_private','passwordless_session','config_snapshots_equal','baseline_proof_preserved'),True),
                **base.STORAGE_CHECKS[action]}
            expected_checks['guard_counter']=3 if action=='mutate' else 2
            require(type(public) is dict and set(public)=={'schema','action','outcome','entry_disabled','managed_candidate_imported',
                'synthetic_only','source_files_verified','storage_checks','private_proof_written'}
                and type(public['schema']) is int and public['schema']==1 and public['action']==action
                and public['outcome']=='passed' and public['entry_disabled'] is False
                and public['managed_candidate_imported'] is False and public['synthetic_only'] is True
                and public['source_files_verified'] is True and public['storage_checks']==expected_checks
                and all(type(public['storage_checks'][k]) is type(v) for k,v in expected_checks.items())
                and public['private_proof_written'] is (action in {'seed','mutate'}),'ordinary_storage_result_refused')
            private=json.loads(self.guest_read(control+'/storage-result-private.json'))
            require(type(private) is dict and set(private)=={'schema','action',*base.FINGERPRINT_FIELDS}
                and private['action']==action and type(private['schema']) is int and private['schema']==1,'ordinary_storage_private_schema')
            actual=base.private_fingerprints({k:private[k] for k in base.FINGERPRINT_FIELDS})
            proof=base.private_proof(json.loads(self.guest_read(control+'/storage-proof-private.json')))
            if action=='seed':
                require(proof['mutation'] is None and actual==proof['baseline'],'ordinary_seed_proof')
                self.storage_proof=proof
            elif action=='mutate':
                require(proof['baseline']==self.storage_proof['baseline'] and proof['mutation']==actual
                    and all(proof['baseline'][k]!=actual[k] for k in base.FINGERPRINT_FIELDS),'ordinary_mutated_storage_proof')
                self.storage_proof=proof
            else:
                require(proof['baseline']==self.storage_proof['baseline'] and proof['mutation'] is None
                    and actual==self.storage_proof['baseline'],'ordinary_restored_storage_proof')
            self.storage_results[action]=public
        finally:self.storage_contexts.append(context.record)
        self.assert_network_closed()

    def retain_history_proof(self):
        value=json.loads(self.guest_read(self.config_path+'/'+CONTROL+'/external-proof.json'))
        require(type(value) is dict and set(value)=={'schema','token','generation','branch_commit','postbackup_window'}
            and value['token']==self.phase_token and value['generation']=='before_restore'
            and value['branch_commit']==self.args.branch_commit,'ordinary_history_proof_identity')
        window=value['postbackup_window']
        require(type(window) is dict and set(window)=={'start','end','rows','sha256'}
            and all(type(window[k]) in {int,float} for k in ('start','end'))
            and window['end']>window['start'] and type(window['rows']) is int and 1<=window['rows']<=128
            and digest_value(window['sha256']),'ordinary_history_proof_shape')
        self.external_proof=value
        # This flag is an inherited default-window order precondition only. No
        # guard is exported or retained outside the guest in this procedure.
        self.host_guard_retained=True

    def prepare_restart_observation(self):
        self.stop_core()
        self.generation='after_restore'
        self.phase_token=secrets.token_hex(16)
        self.inputs.update(generation=self.generation,external_proof=self.external_proof,
            backup_guard_sha256=self.backup_guard_sha256,latest_guard_sha256=self.latest_guard_sha256,
            expected_joins_sha256=self.joins_sha256)
        control=self.config_path+'/'+CONTROL
        self.publish_inputs()
        self.guest_write(control+'/storage-expected-private.json',canonical(self.storage_proof))
        self.guest('chmod 600 '+control+'/inputs.json '+control+'/storage-expected-private.json; rm -f '
            +control+'/phase.json '+control+'/job-nonce.json; rm -f '+self.config_path+'/'+RESULTS+'/*.json',30)
        self.run_storage_context('validate_restored')

    def run(self):
        checked_binding(PINS)
        require(sys.platform=='linux' and os.uname().machine=='x86_64'
            and Path('/dev/kvm').exists() and os.access('/dev/kvm',os.R_OK|os.W_OK),'native_linux_amd64_required')
        require(re.fullmatch('[0-9a-f]{40}',self.args.branch_commit),'branch_commit_refused')
        require(not self.args.output.exists() and not self.args.output.is_symlink(),'fresh_output_required')
        self.args.output.mkdir(mode=0o700,parents=True)
        self.public=self.args.output.resolve()/'public-summary';self.public.mkdir(mode=0o700)
        self.private=Path(tempfile.mkdtemp(prefix='private-',dir=self.args.output.resolve()))
        inventory=check_archive(self.args.candidate_zip,CANDIDATE_SHA,CANDIDATE_FILES)
        self.inventories={'candidate':inventory}
        self.provenance={'candidate_source_commit':SOURCE_COMMIT,'candidate_zip_sha256':CANDIDATE_SHA,
            'candidate_files':CANDIDATE_FILES,'candidate_payload_sha256':sha(canonical(inventory)),
            'controller_branch_commit':self.args.branch_commit,'controller_sha256':sha(Path(__file__).read_bytes()),
            'haos_version':'18.3','haos_xz_sha256':HAOS_XZ_SHA,'release_published':False,
            'helper_files_sha256':{p.relative_to(ROOT/'guest_helper').as_posix():sha(p.read_bytes())
                for p in (ROOT/'guest_helper').rglob('*') if p.is_file() and '__pycache__' not in p.parts},
            'storage_transfer_sha256':sha((ROOT/'storage_transfer.py').read_bytes()),
            'storage_context_sha256':sha((ROOT/'storage_context.py').read_bytes()),
            'reset_sha256':sha((ROOT/'reset_fresh_config.py').read_bytes()),
            'qa_manifest_adaptation':False,'unchanged_product_members':len(inventory),
            'prepared_dependency_preload':False,'environmental_parent_fence':True}
        self.start_vm(self.download_haos());self.wait_initial_managed()
        require(self.core_version_before==self.container_core_version_before==CORE
            and self.supervisor_version_observed=='2026.10.3','current_managed_environment_required')
        self.core_version_after=self.container_core_version_after=CORE
        self.verify_cli();self.backup_cli_capabilities()
        self.guest('umask 077; mkdir -m 700 '+GUEST_ROOT,30)
        self.stop_core()
        self.guest_write(GUEST_ROOT+'/reset.py',(ROOT/'reset_fresh_config.py').read_bytes())
        self.reset_receipt=base.checked_reset(json.loads(self.guest('/usr/bin/docker exec -i hassio_supervisor python3 -B - '
            +self.nonce+' < '+GUEST_ROOT+'/reset.py',90)))
        self.start_core();self.minimum_core_image=self.actual_core_image()
        self.prepare(inventory);self.disconnect_external_network()
        self.network_transitions.append('closed_before_synthetic_seed')
        self.run_storage_context('seed');self.phase('baseline_enabled',start=True)
        self.backup_operation();self.inspect_backup();self.stop_core()
        self.run_storage_context('mutate');self.phase('mutated_enabled',start=True)
        self.retain_history_proof();self.stop_core();self.assert_network_closed();self.require_restore_barrier_absent()
        self.default_conditions_restore();project_default_receipt(self.default_restore_conditions,complete=True)
        self.restored_boot_barrier()
        require(self.actual_core_image()==self.minimum_core_image,'ordinary_restored_image_changed')
        self.prepare_restart_observation();self.phase('restart_enabled',start=True)
        self.stop_core();self.run_storage_context('validate_restart');self.verify_candidate()
        require([p['phase'] for p in self.phases]==list(PHASES),'ordinary_four_phases_required')
        self.acceptance=True;self.stage='ordinary_unmodified_product_restore_complete'

    def finish(self,failure):
        self.cleanup_vm()
        passed=self.acceptance and failure is None and not self.cleanup['cleanup_failed'] and len(self.phases)==4
        value={'schema':2,'outcome':'passed' if passed else 'failed_or_incomplete',
            'phase_names':[p['phase'] for p in self.phases],'phases':len(self.phases),
            'failure_or_final_stage':self.stage,'failure_type':type(failure).__name__ if failure else None,
            'failure_code':str(failure) if type(failure) is Refused else None,'provenance':self.provenance,
            'guest_failures':self.guest_failures,
            'actual_kvm_confirmed':self.kvm_confirmed,'actual_core':self.core_version_after,
            'actual_supervisor':self.supervisor_version_observed,'current_core_image':self.minimum_core_image,
            'fresh_owned_config':self.reset_receipt,'core_actions':self.core_actions,'backup_requests':self.backup_requests,
            'backup':{k:v for k,v in (self.backup or {}).items() if k!='slug'},'restore':self.restore,
            'storage_contexts':self.storage_contexts,'storage_results':self.storage_results,
            'normal_initial_requirement_window':self.normal_initial_window,
            'default_restore_conditions':self.default_restore_conditions,
            'network_boundary':self.network_boundary,'network_transitions':self.network_transitions,
            'ordinary_unmodified_product_partial_restore_qualified':passed,'normal_managed_dependencies':passed,
            'product_manifest_unchanged':True,'prepared_dependency_preload_used':False,
            'automatic_guard_rollback_block':passed,'manual_guard_imports':0,'guard_exports':0,
            'owner_acknowledgments_after_restore':0,'environmental_transport_instrumentation':True,
            'real_provider_accounts_configured':False,'owner_credentials_used':False,'production_configuration_used':False,
            'provider_authentication_after_restore_tested':False,'provider_session_renewal_tested':False,
            'full_system_restore_tested':False,'full_encrypted_cloud_backup_tested':False,
            'stable_release_approval':False,'candidate_hacs_download_tested':False,
            'host_elapsed_seconds':round(time.monotonic()-self.started,3),**self.cleanup}
        if self.public is not None:write_json(self.public/'host.json',value)
        print('ordinary_restore_outcome='+value['outcome'],flush=True)
        return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-zip',type=Path,required=True)
    parser.add_argument('--branch-commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    controller=Controller(parser.parse_args())
    def stopping(_signum,_frame):raise Refused('host_interrupted')
    for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,stopping)
    failure=None
    try:controller.run()
    except BaseException as error:failure=error
    return controller.finish(failure)


if __name__=='__main__':raise SystemExit(main())

