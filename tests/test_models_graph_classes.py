"""
This procedure will test the classes of the models_graph.
"""

import datetime
import unittest
from competition import create_app, neostore
from competition import models_graph as mg
from competition.lib.neostructure import *
from config import TestConfig
from py2neo.data import Node


# @unittest.skip("Focus on Coverage")
class TestModelGraphClass(unittest.TestCase):

    def setUp(self):
        # Initialize Environment
        # Todo: Review why I need to push / pull contexts in setUp - TearDown.
        self.app = create_app(TestConfig)
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.ns = neostore.NeoStore()
        # self.ns.init_graph()
#       # my_env.init_loghandler(__name__, "c:\\temp\\log", "warning")

    def tearDown(self):
        self.app_ctx.pop()

    def test_person(self):
        lbl = lbl_person
        name = "Dirk Vermeylen"
        props = dict(name=name)
        person_node = self.ns.get_node(lbl, **props)
        self.assertTrue(isinstance(person_node, Node))
        self.assertTrue(lbl in person_node.labels)
        self.assertEqual(person_node["name"], name)
        person_obj = mg.Person(person_node["nid"])
        self.assertEqual(person_obj.get_name(), name)

    def test_person_list(self):
        person_list = mg.person_list()
        self.assertTrue(person_list, list)
        if len(person_list) > 5:
            random_person = person_list[len(person_list)-5]
        else:
            random_person = person_list[0]
        self.assertTrue(isinstance(random_person, dict))
        # Dict keys: nid, name, category, cat_seq, mf, and races
        for lbl in ["nid", "name", "category", "mf"]:
            self.assertTrue(isinstance(random_person[lbl], str))
            self.assertIsNotNone(random_person[lbl])
        for lbl in ["cat_seq", "races"]:
            self.assertTrue(isinstance(random_person[lbl], int))
            self.assertIsNotNone(random_person[lbl])
        self.assertNotEqual(random_person["category"], def_not_defined)

    def test_organization_add(self):
        nr_nodes = len(self.ns.get_nodes())
        # This function tests the organization.
        name = "Dwars door Hillesheim"
        city = "Hillesheim_X"
        ds_str = "1963-07-02"
        ds = datetime.datetime.strptime(ds_str, "%Y-%m-%d")
        org_dict = dict(
            name=name,
            location=city,
            datestamp=ds,
            org_type=False
        )
        org = mg.Organization()
        self.assertTrue(org.add(**org_dict))
        org_nid = org.get_org_id()
        self.assertTrue(isinstance(org_nid, str))
        self.assertTrue(isinstance(org.get_node(), Node))
        # Test Location
        loc = org.get_location()
        self.assertTrue(isinstance(loc, Node))
        self.assertEqual(loc["city"], city)
        # Test Datestamp
        self.assertEqual(org.get_date()["key"], ds_str)
        # Test name
        self.assertEqual(org.get_name(), name)
        # Test label
        self.assertTrue(isinstance(org.get_label(), str))
        # Test Type organizatie
        self.assertEqual(org.get_org_type(), "Wedstrijd")
        mg.organization_delete(org_id=org_nid)
        self.assertFalse(mg.get_location(loc["nid"]), "Location is removed as part of Organization removal")
        self.assertEqual(nr_nodes, len(self.ns.get_nodes()))

    def test_organization_edit(self):
        nr_nodes = len(self.ns.get_nodes())
        # This function tests the organization Edit.
        name = "Dwars door Hillesheim"
        city = "Hillesheim_X"
        ds_str = "1963-07-02"
        ds = datetime.datetime.strptime(ds_str, "%Y-%m-%d")
        org_dict = dict(
            name=name,
            location=city,
            datestamp=ds,
            org_type=False
        )
        org = mg.Organization()
        # Test organization is created.
        self.assertTrue(org.add(**org_dict))
        org_nid = org.get_org_id()
        self.assertTrue(isinstance(org_nid, str))
        # Now update organization
        # Update organization
        name = "Rondom Berndorf"
        city = "Berndorf-Y"
        ds_str = "1964-10-28"
        ds = datetime.datetime.strptime(ds_str, "%Y-%m-%d")
        org_dict = dict(
            name=name,
            location=city,
            datestamp=ds,
            org_type=True
        )
        org.edit(**org_dict)
        # Test Location
        loc = org.get_location()
        loc_nid = loc["nid"]
        self.assertEqual(loc["city"], city)
        self.assertTrue(mg.get_location(loc_nid), "Location is available")
        # Test Datestamp
        self.assertEqual(org.get_date()["key"], ds_str)
        # Test name
        self.assertEqual(org.get_name(), name)
        # Test label
        self.assertTrue(isinstance(org.get_label(), str))
        # Test Type organizatie
        self.assertEqual(org.get_org_type(), "Deelname")
        mg.organization_delete(org_id=org_nid)
        self.assertFalse(mg.get_location(loc_nid), "Location is removed as part of Organization removal")
        self.assertEqual(nr_nodes, len(self.ns.get_nodes()), "Number of end nodes not equal to start nodes")

    def test_race_add(self):
        nr_nodes = len(self.ns.get_nodes())
        # This function tests the organization.
        name = "Dwars door Hillesheim"
        city = "Hillesheim_X"
        ds_str = "1963-07-02"
        ds = datetime.datetime.strptime(ds_str, "%Y-%m-%d")
        org_dict = dict(
            name=name,
            location=city,
            datestamp=ds,
            org_type=False
        )
        org = mg.Organization()
        self.assertTrue(org.add(**org_dict))
        org_nid = org.get_org_id()
        # Add Race Seniors Dames
        # Find node for Category 'Seniors'
        props = dict(name='Seniors')
        lbl = 'Category'
        cat_node = self.ns.get_node(lbl, **props)
        race_props = dict(
            categories=[cat_node["nid"]],
            mf="vrouw",
            short=False,
            name=False
        )
        rc = mg.Race(org_id=org_nid)
        rc.add(**race_props)
        self.assertEqual(rc.get_racename(), "Seniors - Dames")
        mg.race_delete(rc.get_node()['nid'])
        mg.organization_delete(org_id=org_nid)
        self.assertEqual(nr_nodes, len(self.ns.get_nodes()))


if __name__ == "__main__":
    unittest.main()
