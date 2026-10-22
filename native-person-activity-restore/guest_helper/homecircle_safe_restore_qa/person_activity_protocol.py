"""Finite synthetic Person/activity receipt schema; no Home Assistant imports."""
from datetime import datetime
import hashlib
import json
import re

PERSON_ID = 'person.example_homecircle_restore_person'
PERSON_NAME = 'Example HomeCircle Restore Person'
TRACKER_A = 'device_tracker.example_homecircle_restore_gps_a'
TRACKER_B = 'device_tracker.example_homecircle_restore_gps_b'
TRACKER_C = 'device_tracker.example_homecircle_restore_mutant'
PERSON_BOOLEANS = ('actual_person_component', 'editable_storage_person', 'person_registry_join',
    'tracker_registry_joins', 'normal_person_store_persistence', 'configured_active_selected_distinct',
    'homecircle_uses_only_selected_tracker', 'unselected_tracker_excluded_from_runtime',
    'nonadmin_active_source_masked')
ACTIVITY_BOOLEANS = ('actual_activity_log', 'normal_activity_store_persistence',
    'api_projection_matches_raw', 'state_transition_events_generated', 'configuration_fingerprint_matches', 'startup_suffix_allowlisted')
PHASES = ('baseline_enabled','mutated_enabled','automatic_restored_enabled','restart_enabled')


def check(ok, code):
    if not ok:
        raise ValueError(code)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def hash_value(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def person_proof(value, phase):
    check(phase in PHASES and type(value) is dict and set(value)=={
        *PERSON_BOOLEANS,'persons','configured_tracker_links','selected_tracker_links',
        'saved_associations_sha256','postbackup_tracker_absent','direct_person_state_writes'},'qa_person_proof_shape')
    check(all(value[key] is True for key in PERSON_BOOLEANS)
        and type(value['persons']) is int and value['persons']==1
        and type(value['configured_tracker_links']) is int and value['configured_tracker_links']==2
        and type(value['selected_tracker_links']) is int and value['selected_tracker_links']==1
        and type(value['direct_person_state_writes']) is int and value['direct_person_state_writes']==0
        and hash_value(value['saved_associations_sha256'])
        and value['postbackup_tracker_absent'] is (phase!='mutated_enabled'),'qa_person_proof_values')
    return dict(value)


def activity_proof(value, phase):
    check(phase in PHASES and type(value) is dict and set(value)=={
        *ACTIVITY_BOOLEANS,'B_events','B_sha256','B_preserved','M_events','M_sha256','M_absent',
        'R_events','R_sha256','R_preserved','B_transitions','M_transitions','R_transitions',
        'manual_activity_store_writes','direct_activity_appends'},'qa_activity_proof_shape')
    check(all(value[key] is True for key in ACTIVITY_BOOLEANS)
        and type(value['manual_activity_store_writes']) is int and value['manual_activity_store_writes']==0
        and type(value['direct_activity_appends']) is int and value['direct_activity_appends']==0
        and type(value['B_transitions']) is int and 2<=value['B_transitions']<=10
        and type(value['B_events']) is int and 20+value['B_transitions']<=value['B_events']<=500
        and hash_value(value['B_sha256'])
        and value['B_preserved'] is (phase!='mutated_enabled')
        and value['M_absent'] is (phase!='mutated_enabled'),'qa_activity_baseline_proof')
    if phase=='baseline_enabled':
        check(type(value['M_events']) is int and value['M_events']==0
            and value['M_sha256'] is None and type(value['M_transitions']) is int and value['M_transitions']==0,'qa_activity_mutation_not_applicable')
    else:
        check(type(value['M_transitions']) is int and 2<=value['M_transitions']<=10
            and type(value['M_events']) is int and 20+value['M_transitions']<=value['M_events']<=500
            and hash_value(value['M_sha256']) and value['M_sha256']!=value['B_sha256'],
            'qa_activity_mutation_proof')
    if phase in PHASES[:2]:
        check(type(value['R_events']) is int and value['R_events']==0
            and value['R_sha256'] is None and value['R_preserved'] is None
            and type(value['R_transitions']) is int and value['R_transitions']==0,'qa_activity_restored_not_applicable')
    else:
        check(type(value['R_transitions']) is int and 2<=value['R_transitions']<=10
            and type(value['R_events']) is int and 20+value['R_transitions']<=value['R_events']<=500
            and hash_value(value['R_sha256']) and value['R_sha256'] not in {
                value['B_sha256'],value['M_sha256']} and value['R_preserved'] is True,
            'qa_activity_restored_proof')
    return dict(value)


def event_groups(value):
    """Validate bounded synthetic event material only for private control use."""
    check(type(value) is dict and len(value)==5,'qa_activity_event_groups')
    allowed_values={'presence':{'home','away','driving','unavailable'},
        'freshness':{'fresh','stale','unknown','unavailable'},
        'automatic_refresh':{'requested','send_failed'},
        'refresh':{'requested','checked','cooldown','busy','limited','disabled','not_allowed',
            'unsupported','no_position','fresh','send_failed','unavailable'}}
    for member,events in value.items():
        check(type(member) is str and re.fullmatch('(?:person|device_tracker)[.][a-z0-9_]{1,120}',member)
            and type(events) is list and 1<=len(events)<=100,'qa_activity_group_bound')
        previous=None
        for event in events:
            check(type(event) is dict and set(event)<={'kind','value','observed_at','reported_at'}
                and {'kind','observed_at'}<=set(event)
                and event['kind'] in {'started','presence','source','freshness','refresh','automatic_refresh'}
                and type(event['observed_at']) is str and len(event['observed_at'])<=40
                and re.fullmatch(r'[0-9T:+.Z-]{10,40}',event['observed_at'])
                and ('reported_at' not in event or type(event['reported_at']) is str
                    and re.fullmatch(r'[0-9T:+.Z-]{10,40}',event['reported_at'])),'qa_activity_event_shape')
            observed=datetime.fromisoformat(event['observed_at'])
            check(observed.tzinfo is not None and (previous is None or observed>=previous),
                'qa_activity_ordered_timestamp')
            previous=observed
            if 'reported_at' in event:
                check(datetime.fromisoformat(event['reported_at']).tzinfo is not None,
                    'qa_activity_report_timestamp')
            if event['kind']=='started':
                check('value' not in event,'qa_activity_started_value')
            elif event['kind']=='source':
                check(event.get('value') is None or type(event.get('value')) is str
                    and re.fullmatch('(?:person|device_tracker)[.][a-z0-9_]{1,120}',event['value']),
                    'qa_activity_source_value')
            else:
                check(type(event.get('value')) is str and event['value'] in allowed_values[event['kind']],
                    'qa_activity_fixed_value')
    return value


def count_events(groups):
    return sum(len(events) for events in groups.values())


def preserved_prefix(groups, prefix):
    return set(groups)==set(prefix) and all(groups[member][:len(events)]==events
        for member,events in prefix.items())


def absent_events(groups, other):
    return not any(event in groups.get(member,()) for member,events in other.items() for event in events)


def suffix(groups, prefix):
    check(preserved_prefix(groups,prefix),'qa_activity_baseline_prefix')
    return {member:events[len(prefix[member]):] for member,events in groups.items()}


def external_proof(value):
    check(type(value) is dict and set(value)=={'schema','association_sha256','events','transitions'}
        and type(value['schema']) is int and value['schema']==1
        and hash_value(value['association_sha256']) and type(value['transitions']) is int
        and 2<=value['transitions']<=10,'qa_person_activity_external_shape')
    event_groups(value['events'])
    check(20<=count_events(value['events'])<=500,'qa_person_activity_external_event_bound')
    return json.loads(json.dumps(value))


def observation_suffix(groups):
    event_groups(groups)
    check(all([event['kind'] for event in events[:4]]==['started','presence','source','freshness']
        and sum(event['kind']=='started' for event in events)==1
        and all(event['kind'] in {'started','presence','source','freshness'} for event in events)
        for events in groups.values()),'qa_activity_observation_suffix')
    return groups
