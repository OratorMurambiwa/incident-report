import unittest
from contracts import names,durable,assert_accounted


class FaultContractTests(unittest.TestCase):
    def fixture(self):
        row={'event_id':'id','published':True,'status':'RECEIVED','receipts':1,'diagnoses':1,'snapshots':5}
        return [row],{'event_copies':{'id':2},'invalid_records':1,'end':3},{'committed':3,'end':3},{'error':'InvalidEvent','attempts':1}

    def test_private_names(self):
        x=names('20261107t120000z_abcdef01')
        self.assertTrue(x['project'].startswith('incidentiq-fault-'))
        self.assertTrue(x['topic'].startswith('incidentiq.fault.'))
        self.assertNotEqual(x['database'],'incidentiq')

    def test_reject_unrelated_or_injected_identifiers(self):
        for value in ('incidentiq','../incidentiq','20261107t120000z_abcdef01;rm',''):
            with self.subTest(value=value),self.assertRaises(ValueError): names(value)

    def test_duplicate_delivery_with_single_effect_is_valid(self):
        assert_accounted(*self.fixture())

    def test_no_duplicate_database_effects(self):
        for field,value in [('receipts',2),('diagnoses',2),('snapshots',10),('published',False),('status','PENDING')]:
            args=self.fixture();args[0][0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError): assert_accounted(*args)

    def test_missing_kafka_event_rejected(self):
        args=self.fixture();args[1]['event_copies']={}
        with self.assertRaises(AssertionError): assert_accounted(*args)

    def test_lagging_offset_rejected(self):
        args=self.fixture();args[2]['committed']=2
        with self.assertRaises(AssertionError): assert_accounted(*args)

    def test_lost_poison_record_rejected(self):
        args=self.fixture();args[1]['invalid_records']=0
        with self.assertRaises(AssertionError): assert_accounted(*args)

    def test_wrong_quarantine_class_rejected(self):
        args=self.fixture();args[3]['error']='OperationalError'
        with self.assertRaises(AssertionError): assert_accounted(*args)


if __name__=='__main__': unittest.main()
