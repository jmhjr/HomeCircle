"""Validate actual archived synthetic Person/activity bytes against phase hashes."""
import hashlib
import json

PERSON='person.example_homecircle_restore_person'
GPS_A='device_tracker.example_homecircle_restore_gps_a'
GPS_B='device_tracker.example_homecircle_restore_gps_b'
GPS_C='device_tracker.example_homecircle_restore_mutant'


def validate_person_activity_archive(person,activity,baseline,registry,options,entry_id,expected):
    def check(ok):
        if not ok:raise ValueError('qa_person_activity_archive_refused')
    def digest(value):
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    check(type(expected) is dict and set(expected)=={'person_sha256','B_sha256','B_events'})
    check(type(baseline) is dict and set(baseline)=={'schema','association','payload','transitions'}
        and baseline['schema']==1 and type(baseline['schema']) is int)
    association=baseline['association']
    check(type(association) is dict and set(association)=={'item','registry','selected'}
        and association['selected']==[GPS_A] and digest(association)==expected['person_sha256'])
    item=association['item']
    check(type(item) is dict and item.get('name')=='Example HomeCircle Restore Person'
        and type(item.get('id')) is str and item.get('user_id') is None
        and item.get('device_trackers')==[GPS_A,GPS_B])
    check(type(person) is dict and person.get('key')=='person' and person.get('version')==2
        and person.get('data')=={'items':[item]})
    expected_registry=association['registry']
    check(type(expected_registry) is list and len(expected_registry)==3
        and [row.get('entity_id') for row in expected_registry]==[PERSON,GPS_A,GPS_B]
        and all(type(row) is dict and set(row)=={'entity_id','unique_id','platform','config_entry_id','disabled_by'}
            and row['disabled_by'] is None and row['config_entry_id'] is None for row in expected_registry)
        and expected_registry[0]['unique_id']==item['id'] and expected_registry[0]['platform']=='person'
        and all(row['platform']=='homecircle_safe_restore_qa'
            and row['unique_id']==row['entity_id'].split('.',1)[1] for row in expected_registry[1:]))
    actual=[{key:row.get(key) for key in expected_registry[0]} for wanted in expected_registry
        for row in registry if row.get('entity_id')==wanted['entity_id']]
    check(actual==expected_registry and not any(row.get('entity_id')==GPS_C for row in registry)
        and options.get('people')==[PERSON] and options['members'][PERSON]['trackers']==[GPS_A])
    check(type(activity) is dict and activity.get('key')=='homecircle.activity.'+entry_id
        and activity.get('version')==1 and activity.get('data')==baseline['payload'])
    payload=baseline['payload']
    check(type(payload) is dict and payload.get('fingerprint')==hashlib.sha256(
        json.dumps(options,sort_keys=True,default=str).encode()).hexdigest()
        and type(payload.get('events')) is dict and set(payload['events'])==set(options['members'])
        and digest(payload['events'])==expected['B_sha256']
        and sum(len(events) for events in payload['events'].values())==expected['B_events']
        and type(expected['B_events']) is int and 22<=expected['B_events']<=500)
    return {'saved_person_configuration_included':True,'saved_person_registry_joins_included':True,
        'saved_homecircle_activity_included':True}
