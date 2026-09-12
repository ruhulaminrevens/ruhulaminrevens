import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import core
from reporting import export_report


def complete_rows():
    rows=[]
    for cat,item,weight in [('Memory','Installed RAM',8),('System','CPU',5),
                            ('Battery','Health',12),('Storage','Disk 1',15),
                            ('Display','Display Test',10),('BIOS','BIOS Password Check',6),
                            ('Diagnostics','Built-in Hardware Diagnostics',6),
                            ('Input','Keyboard Test',5)]:
        core.add(rows,cat,item,'Passed','PASS',weight=weight)
    return rows


class ScoringTests(unittest.TestCase):
    def test_complete_inspection_can_buy(self):
        rows=complete_rows()
        self.assertEqual(core.score(rows),100)
        self.assertEqual(core.completion(rows),100)
        self.assertEqual(core.recommendation(rows)[0],'BUY')

    def test_each_critical_check_required(self):
        for item in core.CRITICAL_MANUAL:
            with self.subTest(item=item):
                rows=[r for r in complete_rows() if r['item']!=item]
                self.assertEqual(core.recommendation(rows)[0],'INCOMPLETE')

    def test_critical_failure_overrides_incomplete(self):
        rows=[]
        core.add(rows,'Storage','Disk 1','Unhealthy','FAIL',weight=15)
        core.add(rows,'Display','Display Test','Pending','MANUAL',weight=100)
        self.assertEqual(core.recommendation(rows)[0],'REJECT')

    def test_unknown_not_counted_as_done(self):
        rows=complete_rows(); rows[2]['status']='UNKNOWN'
        self.assertLess(core.completion(rows),100)
        self.assertEqual(core.recommendation(rows)[0],'INCOMPLETE')

    def test_missing_auto_checks_block_buy(self):
        for index in (0,1,2,3):
            rows=complete_rows(); rows.pop(index)
            self.assertEqual(core.recommendation(rows)[0],'INCOMPLETE')

    def test_noncritical_failure_cannot_buy(self):
        rows=complete_rows(); rows[-1]['status']='FAIL'
        self.assertEqual(core.recommendation(rows)[0],'NEGOTIATE')

    def test_empty_incomplete(self):
        self.assertEqual(core.recommendation([])[0],'INCOMPLETE')

    def test_grade_boundaries(self):
        for health,grade in [(90,'A'),(89.9,'B'),(80,'B'),(70,'C'),(60,'D'),(59.9,'F'),(None,'—')]:
            self.assertEqual(core.battery_grade(health),grade)

    def test_invalid_numbers(self):
        for value in (None,'N/A','nan','inf'):
            self.assertIsNone(core.num(value))


class HardwareTests(unittest.TestCase):
    def test_storage_numeric_and_string_health(self):
        for health,status in [(0,'PASS'),('Healthy','PASS'),(1,'WARN'),(2,'FAIL'),('Unhealthy','FAIL'),(5,'UNKNOWN'),(None,'UNKNOWN')]:
            with self.subTest(health=health), patch('core.ps',return_value=({'HealthStatus':health},'')):
                rows=[]; summary={}; core.scan_storage(rows,summary)
                self.assertEqual(rows[0]['status'],status)
                self.assertEqual(summary['storage_status'],status)
                self.assertIn('Read errors Not reported',rows[-1]['value'])

    def test_unhealthy_not_downgraded_by_temperature(self):
        with patch('core.ps',return_value=({'HealthStatus':'Unhealthy','Temperature':80,'ReadErrorsTotal':2},'')):
            rows=[]; core.scan_storage(rows,{})
            self.assertEqual(rows[0]['status'],'FAIL')

    def test_multi_disk_worst_state(self):
        with patch('core.ps',return_value=([{'HealthStatus':'Unhealthy'},{'HealthStatus':'Healthy'}],'')):
            rows=[]; summary={}; core.scan_storage(rows,summary)
            self.assertEqual(summary['storage_status'],'FAIL')
            self.assertEqual(sum(r['weight'] for r in rows),15)

    def test_storage_unavailable(self):
        with patch('core.ps',return_value=(None,'Access denied')):
            rows=[]; core.scan_storage(rows,{})
            self.assertEqual(rows[0]['status'],'UNKNOWN')

    def test_faulty_detected_device_is_not_pass(self):
        with patch('core.ps',return_value=([{'Class':'Camera','FriendlyName':'Webcam','Status':'Error'}],'')):
            rows=[]; core.scan_devices(rows,{})
            self.assertEqual(next(r for r in rows if r['item']=='Camera')['status'],'WARN')

    def test_battery_installed_entries_only(self):
        root=ET.fromstring('<BatteryReport xmlns="urn:test"><Batteries><Battery><Id>Primary</Id><DesignCapacity>50000</DesignCapacity><FullChargeCapacity>40000</FullChargeCapacity></Battery><Battery><DesignCapacity>20000</DesignCapacity><FullChargeCapacity>10000</FullChargeCapacity></Battery></Batteries><History><DesignCapacity>99999</DesignCapacity></History></BatteryReport>')
        batteries=core.parse_batteries(root)
        self.assertEqual([b['health'] for b in batteries],[80,50])

    def test_missing_full_capacity_is_unknown(self):
        root=ET.fromstring('<Batteries><Battery><DesignCapacity>50000</DesignCapacity></Battery></Batteries>')
        self.assertIsNone(core.parse_batteries(root)[0]['health'])

    def test_zero_full_capacity_is_real_failure(self):
        root=ET.fromstring('<Batteries><Battery><DesignCapacity>50000</DesignCapacity><FullChargeCapacity>0</FullChargeCapacity></Battery></Batteries>')
        self.assertEqual(core.parse_batteries(root)[0]['health'],0)

    def test_battery_report_cleanup_and_weak_secondary(self):
        paths=[]
        def fake_run(command):
            path=Path(command[command.index('/output')+1]); paths.append(path)
            path.write_text('<Batteries><Battery><DesignCapacity>50000</DesignCapacity><FullChargeCapacity>50000</FullChargeCapacity></Battery><Battery><DesignCapacity>10000</DesignCapacity><FullChargeCapacity>5000</FullChargeCapacity></Battery></Batteries>')
            return 0,'',''
        with patch('core.run',side_effect=fake_run):
            rows=[]; summary={}; core.scan_battery(rows,summary)
        self.assertEqual(rows[0]['status'],'FAIL')
        self.assertEqual(summary['battery_health'],91.7)
        self.assertFalse(paths[0].exists())

    def test_powercfg_error_unknown(self):
        with patch('core.run',return_value=(1,'','No battery')):
            rows=[]; core.scan_battery(rows,{})
            self.assertEqual(rows[0]['status'],'UNKNOWN')


class ReportTests(unittest.TestCase):
    def test_report_formats_and_escaping(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.html'; rows=complete_rows()
            core.add(rows,'Notes','<script>','=1+1',note='বাংলা <b>text</b>')
            export_report(rows,{'manufacturer':'Test <Brand>','serial':'TEST'},path)
            html=path.read_text(encoding='utf-8')
            self.assertIn('&lt;script&gt;',html)
            self.assertNotIn('<script>',html)
            self.assertIn('@media print',html)
            self.assertEqual(json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))['version'],'1.1.0')
            csv=path.with_suffix('.csv').read_text(encoding='utf-8-sig')
            self.assertIn("'=1+1",csv)
            self.assertIn('বাংলা',csv)

    def test_empty_report_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'empty.html'; export_report([],{},path)
            self.assertIn('INCOMPLETE',path.read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
