"""
This procedure will test the classes of the models_graph.
"""

import datetime
import unittest
from competition import create_app
# Create app before import models_graph. Environment settings for Neo4J are required before import.
app = create_app('testing')
from competition import models_graph as mg

# @unittest.skip("Focus on Coverage")
class TestModelGraphClass(unittest.TestCase):

    def setUp(self):
        # Initialize Environment
        # Todo: Review why I need to push / pull contexts in setUp - TearDown.
        self.app_ctx = app.app_context()
        self.app_ctx.push()
        self.ns = mg.get_ns()
        # self.ns = neostore.NeoStore(**neo4j_params)
        self.ns.init_graph()
#       my_env.init_loghandler(__name__, "c:\\temp\\log", "warning")

    def tearDown(self):
        self.app_ctx.pop()

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
        self.assertEqual(org.get_org_type(), "Wedstrijd")
        mg.organization_delete(org_id=org_nid)
        self.assertFalse(mg.get_location(loc_nid), "Location is removed as part of Organization removal")
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
        self.assertEqual(nr_nodes, len(self.ns.get_nodes()))

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
