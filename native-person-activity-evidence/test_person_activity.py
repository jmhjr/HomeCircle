"""Finite adversarial contracts for independent aggregate Person/activity proofs."""
from copy import deepcopy
import unittest

import independent_ordinary as c


def values():
    result={}
    for index,name in enumerate(c.PHASES):
        person={key:True for key in c.PERSON_FLAGS}
        person.update(persons=1,configured_tracker_links=2,selected_tracker_links=1,
            saved_associations_sha256=('e' if index==1 else 'd')*64,
            postbackup_tracker_absent=index!=1,direct_person_state_writes=0)
        activity={key:True for key in c.ACTIVITY_FLAGS}
        activity.update(B_events=24,B_sha256='a'*64,B_preserved=index!=1,B_transitions=2,
            M_events=0 if index==0 else 26,M_sha256=None if index==0 else 'b'*64,
            M_absent=index!=1,M_transitions=0 if index==0 else 2,
            R_events=28 if index>=2 else 0,R_sha256='c'*64 if index>=2 else None,
            R_preserved=True if index>=2 else None,R_transitions=2 if index>=2 else 0,
            manual_activity_store_writes=0,direct_activity_appends=0)
        result[name]={'person_associations':person,'homecircle_activity':activity}
    return result


class PersonActivityContracts(unittest.TestCase):
    def setUp(self):self.values=values()

    def rejects(self,phase,section,key,value):
        changed=deepcopy(self.values);changed[phase][section][key]=value
        with self.assertRaises(c.EvidenceRefused):c.person_activity_check(changed)

    def test_all_four_strict_cohorts_and_association_identities_pass(self):
        c.person_activity_check(self.values)
        self.assertEqual(len(self.values),4)
        self.assertEqual(self.values[c.PHASES[2]]['homecircle_activity']['R_events'],28)

    def test_real_component_selected_active_and_suffix_proofs_required(self):
        for key in c.PERSON_FLAGS:
            with self.subTest(key=key):self.rejects(c.PHASES[2],'person_associations',key,False)
        self.rejects(c.PHASES[3],'homecircle_activity','startup_suffix_allowlisted',False)
        self.rejects(c.PHASES[0],'person_associations','configured_tracker_links',1)
        self.rejects(c.PHASES[0],'person_associations','selected_tracker_links',2)

    def test_person_mutation_must_discriminate_and_restore_original_identity(self):
        self.rejects(c.PHASES[1],'person_associations','saved_associations_sha256','d'*64)
        self.rejects(c.PHASES[2],'person_associations','saved_associations_sha256','e'*64)
        self.rejects(c.PHASES[3],'person_associations','postbackup_tracker_absent',False)

    def test_manual_person_and_activity_injection_are_refused(self):
        self.rejects(c.PHASES[0],'person_associations','direct_person_state_writes',1)
        self.rejects(c.PHASES[1],'homecircle_activity','manual_activity_store_writes',1)
        self.rejects(c.PHASES[2],'homecircle_activity','direct_activity_appends',1)

    def test_startup_only_zero_or_unbounded_cohorts_are_refused(self):
        for phase,kind in ((c.PHASES[0],'B'),(c.PHASES[1],'M'),(c.PHASES[2],'R')):
            for count in (0,20,501):
                with self.subTest(phase=phase,count=count):self.rejects(phase,'homecircle_activity',kind+'_events',count)
            self.rejects(phase,'homecircle_activity',kind+'_transitions',1)

    def test_baseline_and_mutation_cohorts_must_remain_exact_and_separate(self):
        self.rejects(c.PHASES[2],'homecircle_activity','B_sha256','f'*64)
        self.rejects(c.PHASES[3],'homecircle_activity','B_events',25)
        self.rejects(c.PHASES[2],'homecircle_activity','M_sha256','a'*64)
        self.rejects(c.PHASES[3],'homecircle_activity','M_events',27)
        self.rejects(c.PHASES[2],'homecircle_activity','M_absent',False)
        self.rejects(c.PHASES[2],'homecircle_activity','B_preserved',False)

    def test_new_restored_cohort_survives_restart_without_aliasing(self):
        self.rejects(c.PHASES[2],'homecircle_activity','R_sha256','b'*64)
        self.rejects(c.PHASES[3],'homecircle_activity','R_sha256','f'*64)
        self.rejects(c.PHASES[3],'homecircle_activity','R_events',29)
        self.rejects(c.PHASES[3],'homecircle_activity','R_preserved',False)
        self.rejects(c.PHASES[0],'homecircle_activity','R_preserved',True)

    def test_exact_nested_fields_and_scalar_types_are_required(self):
        self.rejects(c.PHASES[0],'person_associations','extra',True)
        self.rejects(c.PHASES[0],'homecircle_activity','extra',True)
        self.rejects(c.PHASES[0],'person_associations','persons',True)
        self.rejects(c.PHASES[0],'person_associations','configured_tracker_links',2.0)
        self.rejects(c.PHASES[2],'homecircle_activity','R_events',28.0)
        self.rejects(c.PHASES[0],'homecircle_activity','manual_activity_store_writes',False)
        self.rejects(c.PHASES[2],'homecircle_activity','actual_activity_log',1)


if __name__=='__main__':unittest.main()
