"""
This procedure will test the classes of the models_graph.
"""

import datetime
import unittest
from competition import create_app
from competition.lib import neostore, models_graph as mg
from competition.lib.neostructure import *
from config import TestConfig
from pandas import DataFrame
from py2neo.data import Node


def organization_create():
    """
    This method will create an organization for the purpose of testing other methods.

    :return: organization object
    """
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
    org.add(**org_dict)
    return org


def organization_delete(org):
    """
    This method will delete an organization.

    :param org: Organization object.
    :return:
    """
    mg.organization_delete(org_id=org.get_org_id())
    return


# @unittest.skip("Focus on Coverage")
class TestModelGraphClass(unittest.TestCase):

    def setUp(self):
        # Initialize Environment
        # Todo: Review why I need to push / pull contexts in setUp - TearDown.
        self.app = create_app(TestConfig)
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.ns = neostore.NeoStore()
        mg.init_graph()

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
        # Dict keys: nid, name, mf, and races
        for lbl in ["nid", "name", "mf"]:
            self.assertTrue(isinstance(random_person[lbl], str))
            self.assertIsNotNone(random_person[lbl])
        for lbl in ["races"]:
            self.assertTrue(isinstance(random_person[lbl], int))
            self.assertIsNotNone(random_person[lbl])

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
        self.assertEqual(org.get_type(), "Wedstrijd")
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
        self.assertEqual(org.get_type(), "Deelname")
        mg.organization_delete(org_id=org_nid)
        self.assertFalse(mg.get_location(loc_nid), "Location is removed as part of Organization removal")
        self.assertEqual(nr_nodes, len(self.ns.get_nodes()), "Number of end nodes not equal to start nodes")

    def test_organization_participants(self):
        """
        This method will test the participants method of the Organization object.
        """
        # Find organization for Lilse Bergen
        props = dict(name="Lilse Bergen")
        org_node = self.ns.get_node(lbl_organization, **props)
        org = mg.Organization(org_id=org_node["nid"])
        participants = org.get_participants()
        for part_node in participants:
            self.assertTrue(part_node, Node)

    def test_get_location_list(self):
        res = mg.get_location_list()
        self.assertTrue(isinstance(res, list))
        self.assertTrue(isinstance(res[0][0], str))
        self.assertTrue(isinstance(res[0][1], str))
        self.assertEqual(len(res[0]), 2)
        for n in res:
            print(n[1])

    def test_organization_list(self):
        res = mg.organization_list()
        rec = res[0]
        for key in ["organization", "city", "id", "date", "type"]:
            self.assertTrue(isinstance(rec[key], str))

    def test_participation_points(self):
        res = mg.participation_points(mf="Heren", orgtype="Wedstrijd")
        self.assertTrue(isinstance(res, DataFrame))

    def test_race(self):
        org = organization_create()
        race1 = mg.Race(org_id=org.get_org_id())
        props = dict(
            name="16k",
            type="Hoofdwedstrijd"
        )
        race1.add(**props)
        self.assertEqual(race1.get_racetype(), "Hoofdwedstrijd")
        # Create new race, set to 'Hoofdwedstrijd'. Race 1 needs to change to Nevenwedstrijd.
        race2 = mg.Race(org_id=org.get_org_id())
        props = dict(
            name="14k",
            type="Hoofdwedstrijd"
        )
        race2.add(**props)
        self.assertEqual(race2.get_racetype(), "Hoofdwedstrijd")
        self.assertEqual(race1.get_racetype(), "Nevenwedstrijd")
        mg.race_delete(race1.get_nid())
        mg.race_delete(race2.get_nid())
        organization_delete(org=org)


if __name__ == "__main__":
    unittest.main()
