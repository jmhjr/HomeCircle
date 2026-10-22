"""Real editable HA Person links and product-observed activity in one owned guest.

Only synthetic GPS tracker states are written. Person states and HomeCircle
activity are produced by their real entity/listener code and ordinary stores.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat

from .person_activity_protocol import (PERSON_ID, PERSON_NAME, TRACKER_A, TRACKER_B,
    TRACKER_C, PERSON_BOOLEANS, ACTIVITY_BOOLEANS, check, digest, event_groups,
    count_events, preserved_prefix, absent_events, suffix, person_proof, activity_proof, external_proof, observation_suffix)

CONTROL='homecircle-safe-restore-qa-control'
PERSON_API_SHA256='de930932cb411f2ab60bb27919bd50c8b82aecb815b1dae7a004c71ce19277a7'


def private_read(path):
    info=path.lstat()
    check(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1
        and stat.S_IMODE(info.st_mode)==0o600 and 0<info.st_size<=2*1024**2,'qa_person_activity_private_file')
    return json.loads(path.read_bytes())


def private_write(path,value):
    temporary=path.with_suffix('.tmp')
    check(not temporary.exists() and not temporary.is_symlink(),'qa_person_activity_private_collision')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def managed_data(directory,key):
    check(key in {'person','core.entity_registry'} or key.startswith('homecircle.activity.')
        and len(key)==len('homecircle.activity.')+32
        and all(c in '0123456789abcdef' for c in key[-32:]),'qa_person_activity_store_key')
    path=directory/'.storage'/key
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(descriptor)
        check(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and before.st_nlink==1
            and stat.S_IMODE(before.st_mode) in {0o600,0o644}
            and 0<before.st_size<=2*1024**2,'qa_person_activity_managed_file')
        with os.fdopen(descriptor,'rb') as stream:
            descriptor=None;raw=stream.read(2*1024**2+1)
    finally:
        if descriptor is not None:os.close(descriptor)
    value=json.loads(raw)
    check(type(value) is dict and value.get('key')==key and type(value.get('data')) is dict,
        'qa_person_activity_managed_envelope')
    return value['data']


async def wait_until(function):
    async with asyncio.timeout(120):
        while True:
            result=await function()
            if result is not None:return result
            await asyncio.sleep(0.2)


def registry_projection(record):
    return {key:getattr(record,key) for key in
        ('entity_id','unique_id','platform','config_entry_id','disabled_by')}


async def person_setup(hass,phase,*,create=False):
    from homeassistant.components import person
    from homeassistant.helpers import entity_registry as er
    check(await hass.async_add_executor_job(lambda:hashlib.sha256(Path(person.__file__).read_bytes()).hexdigest())
        ==PERSON_API_SHA256,'qa_person_api_source')
    registry=er.async_get(hass)
    collection=hass.data['person'][1]
    component=hass.data['person'][2]
    check(type(collection) is person.PersonStorageCollection,'qa_real_person_collection')
    expected_links=[TRACKER_A,TRACKER_C if phase=='mutated_enabled' else TRACKER_B]
    for entity_id in expected_links:
        record=registry.async_get(entity_id)
        if record is None:
            check(phase in {'baseline_enabled','mutated_enabled'},'qa_restored_tracker_registry_missing')
            record=registry.async_get_or_create('device_tracker','homecircle_safe_restore_qa',
                entity_id.split('.',1)[1],suggested_object_id=entity_id.split('.',1)[1],
                original_name='Synthetic Person GPS tracker',disabled_by=None)
        check(record.entity_id==entity_id and record.platform=='homecircle_safe_restore_qa'
            and record.unique_id==entity_id.split('.',1)[1] and record.config_entry_id is None
            and record.disabled_by is None,'qa_person_tracker_registry_identity')
    if phase=='baseline_enabled' and create:
        check(registry.async_get(PERSON_ID) is None and component.get_entity(PERSON_ID) is None
            and not collection.async_items(),'qa_person_creation_collision')
        await person.async_create_person(hass,PERSON_NAME,device_trackers=expected_links)
    async def ready():
        entity=component.get_entity(PERSON_ID)
        if entity is None or hass.states.get(PERSON_ID) is None:return None
        return entity
    entity=await wait_until(ready)
    check(type(entity) is person.Person and entity.editable is True,'qa_real_editable_person')
    if phase=='mutated_enabled':
        before=list(entity.device_trackers)
        check(before==[TRACKER_A,TRACKER_B],'qa_person_mutation_baseline_links')
        await collection.async_update_item(entity.unique_id,{'device_trackers':expected_links})
    check(list(entity.device_trackers)==expected_links
        and person.entities_in_person(hass,PERSON_ID)==expected_links,'qa_person_exact_configured_links')
    return person,entity,expected_links


async def drive_transitions(hass,entry,active):
    from homeassistant.util import dt as dt_util
    runtime=entry.runtime_data
    before=len(runtime.activity.events[PERSON_ID])
    for state in ('not_home','home','not_home'):
        for tracker in (TRACKER_A,active):
            point=(0.0,0.0) if state=='home' else (1.25,2.5)
            hass.states.async_set(tracker,state,{'friendly_name':'Synthetic Person GPS tracker',
                'source_type':'gps','latitude':point[0],'longitude':point[1],'gps_accuracy':5,
                'last_seen':dt_util.utcnow().isoformat()})
            await asyncio.sleep(0.02)
        async def observed():
            person_state=hass.states.get(PERSON_ID)
            members=[member for member in runtime.household.members if member.id==PERSON_ID]
            expected='home' if state=='home' else 'away'
            if (person_state is None or person_state.attributes.get('source')!=active or len(members)!=1
                    or members[0].presence!=expected or members[0].active_source_entity!=active
                    or members[0].location is None or members[0].location.evidence.source_entity!=TRACKER_A):
                return None
            return True
        await wait_until(observed)
    generated=runtime.activity.events[PERSON_ID][before:]
    values=[event.get('value') for event in generated if event['kind']=='presence']
    check('home' in values and values[-1:] == ['away'] and values.count('away')>=1,
        'qa_actual_activity_transition_events')
    check(2<=len(values)<=10,'qa_actual_activity_transition_bound')
    return len(values)


async def durable_person(hass,directory,person,entity,links,phase):
    from homeassistant.helpers import entity_registry as er
    registry=er.async_get(hass)
    record=registry.async_get(PERSON_ID)
    check(record is not None and record.platform=='person' and record.unique_id==entity.unique_id
        and record.config_entry_id is None and record.disabled_by is None,'qa_person_registry_join')
    items=[deepcopy(item) for item in hass.data['person'][1].async_items() if item['id']==entity.unique_id]
    check(len(items)==1 and items[0]['name']==PERSON_NAME and items[0]['device_trackers']==links
        and items[0].get('user_id') is None,'qa_person_storage_identity')
    identities=[registry_projection(registry.async_get(key)) for key in (PERSON_ID,*links)]
    async def persisted():
        try:
            stored=await hass.async_add_executor_job(managed_data,directory,'person')
            registered=await hass.async_add_executor_job(managed_data,directory,'core.entity_registry')
        except FileNotFoundError:return None
        saved=[item for item in stored['items'] if item.get('id')==entity.unique_id]
        actual=[{key:item.get(key) for key in identities[0]} for wanted in identities
            for item in registered['entities'] if item.get('entity_id')==wanted['entity_id']]
        if saved!=items or actual!=identities:return None
        return {'item':items[0],'registry':identities,'selected':[TRACKER_A]}
    saved=await wait_until(persisted)
    active=links[1]
    state=hass.states.get(PERSON_ID)
    runtime=hass.config_entries.async_entries('homecircle')[0].runtime_data
    from custom_components.homecircle import api
    from custom_components.homecircle.selection import person_tracker_references, household_errors, member_errors
    check(not household_errors(hass,runtime.config)
        and all(not member_errors(hass,member,runtime.config["primary_home"],member_id)
            for member_id,member in runtime.config["members"].items()),"qa_actual_product_household_selection_valid")
    configured,current=person_tracker_references(hass,PERSON_ID)
    check(configured==links and current==active and active!=TRACKER_A
        and runtime.config['members'][PERSON_ID]['trackers']==[TRACKER_A]
        and TRACKER_A in runtime.states and active not in runtime.states,'qa_person_selection_nonconflation')
    member=next(member for member in runtime.household.members if member.id==PERSON_ID)
    check(member.active_source_entity==active and member.location is not None
        and member.location.evidence.source_entity==TRACKER_A,'qa_person_selected_gps_evidence')
    projected=next(row for row in api.snapshot(runtime,registry=registry,admin=False)['members'] if row['id']==PERSON_ID)
    check(projected['diagnostics']['active_source']=='other'
        and [row['entity_id'] for row in projected['diagnostics']['selected_trackers']]==[TRACKER_A]
        and state.attributes.get('source')==active,'qa_person_nonadmin_active_mask')
    absent=registry.async_get(TRACKER_C) is None and component_missing(hass,TRACKER_C)
    if phase!='mutated_enabled':
        check(hass.states.get(TRACKER_C) is None,'qa_person_mutant_state_absent')
    check(absent is (phase!='mutated_enabled'),'qa_person_postbackup_tracker_rollback')
    result={key:True for key in PERSON_BOOLEANS}
    result.update(persons=1,configured_tracker_links=2,selected_tracker_links=1,
        saved_associations_sha256=digest(saved),postbackup_tracker_absent=absent,direct_person_state_writes=0)
    return person_proof(result,phase),saved


def component_missing(hass,tracker):
    return tracker not in [linked for entity in hass.data['person'][2].entities for linked in entity.device_trackers]


async def durable_activity(hass,entry,directory):
    from custom_components.homecircle.activity import ActivityLog
    from homeassistant.helpers.storage import Store
    log=entry.runtime_data.activity
    check(type(log) is ActivityLog and isinstance(log.store,Store),'qa_actual_product_activity_store')
    expected=hashlib.sha256(json.dumps(dict(entry.options),sort_keys=True,default=str).encode()).hexdigest()
    check(log.fingerprint==expected,'qa_activity_actual_configuration_fingerprint')
    async def persisted():
        payload=deepcopy(log.payload())
        try:saved=await hass.async_add_executor_job(managed_data,directory,'homecircle.activity.'+entry.entry_id)
        except FileNotFoundError:return None
        if saved!=payload:return None
        return payload
    payload=await wait_until(persisted)
    event_groups(payload['events'])
    check(set(payload['events'])==set(entry.options['members'])
        and all(event.get('value') is None or event['value'] in log.sources
            for events in payload['events'].values() for event in events if event['kind']=='source'),
        'qa_activity_only_selected_sources')
    from custom_components.homecircle import api
    from homeassistant.helpers import entity_registry as er
    registry=er.async_get(hass)
    projected={row['id']:row['activity'] for row in api.snapshot(entry.runtime_data,registry=registry)['members']}
    for member,events in payload['events'].items():
        expected=[{**event,'value':api.location_source_label(entry.runtime_data,event['value'],registry)}
            if event['kind']=='source' else dict(event) for event in reversed(events)]
        check(projected[member]['persistent'] is True and projected[member]['events']==expected,
            'qa_activity_actual_api_projection')
    return payload


async def phase_receipt(hass,entry,phase,inputs,directory):
    person,entity,links=await person_setup(hass,phase)
    transitions=await drive_transitions(hass,entry,links[1])
    person_receipt,association=await durable_person(hass,directory,person,entity,links,phase)
    payload=await durable_activity(hass,entry,directory)
    events=payload['events']
    control=directory/CONTROL
    baseline_path=control/'person-activity-baseline.json'
    if phase=='baseline_enabled':
        check(not baseline_path.exists(),'qa_person_activity_baseline_collision')
        observation_suffix(events)
        baseline={'schema':1,'association':association,'payload':payload,'transitions':transitions}
        await hass.async_add_executor_job(private_write,baseline_path,baseline)
    else:baseline=await hass.async_add_executor_job(private_read,baseline_path)
    B=event_groups(baseline['payload']['events'])
    R=None;M=None
    if phase=='mutated_enabled':
        check(digest(association)!=digest(baseline['association'])
            and payload['fingerprint']!=baseline['payload']['fingerprint'] and absent_events(events,B),
            'qa_person_activity_discriminating_mutation')
        M=observation_suffix(events)
        await hass.async_add_executor_job(private_write,control/'person-activity-external.json',
            {'schema':1,'association_sha256':digest(association),'events':M,'transitions':transitions})
    elif phase in {'automatic_restored_enabled','restart_enabled'}:
        external=external_proof(inputs.get('person_activity_external'))
        M=event_groups(external['events'])
        check(digest(association)==digest(baseline['association'])
            and digest(association)!=external['association_sha256']
            and payload['fingerprint']==baseline['payload']['fingerprint']
            and preserved_prefix(events,B) and absent_events(events,M),'qa_person_activity_restored_baseline')
        restored_path=control/'person-activity-restored.json'
        if phase=='automatic_restored_enabled':
            R=observation_suffix(suffix(events,B))
            check(count_events(R)>0,'qa_person_activity_new_restored_events')
            await hass.async_add_executor_job(private_write,restored_path,{'schema':1,'events':events,'R':R,'transitions':transitions})
        else:
            restored=await hass.async_add_executor_job(private_read,restored_path)
            check(preserved_prefix(events,event_groups(restored['events'])),'qa_person_activity_restart_prefix')
            observation_suffix(suffix(events,restored['events']))
            R=restored['R']
            transitions=restored['transitions']
    result={key:True for key in ACTIVITY_BOOLEANS}
    result.update(B_events=count_events(B),B_sha256=digest(B),B_preserved=phase!='mutated_enabled',
        B_transitions=baseline['transitions'],M_transitions=(transitions if phase=='mutated_enabled' else inputs['person_activity_external']['transitions']) if M is not None else 0,
        R_transitions=transitions if R is not None else 0,manual_activity_store_writes=0,direct_activity_appends=0,
        M_events=count_events(M) if M is not None else 0,M_sha256=digest(M) if M is not None else None,
        M_absent=phase!='mutated_enabled',R_events=count_events(R) if R is not None else 0,
        R_sha256=digest(R) if R is not None else None,R_preserved=True if R is not None else None)
    return {'person_associations':person_receipt,'homecircle_activity':activity_proof(result,phase)}
