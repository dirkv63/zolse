"""
This procedure will test the neostore functionality. No Flask Application items are required.
"""

import os
import unittest
from competition import create_app, neostore
from competition.lib.neostructure import *
from config import TestConfig
from py2neo.data import Node


# @unittest.skip("Focus on Coverage")
class TestNeoStore(unittest.TestCase):

    def setUp(self):
        # Initialize Environment
        self.app = create_app(TestConfig)
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.ns = neostore.NeoStore()
        # self.ns.init_graph()
        # my_env.init_loghandler(__name__, "c:\\temp\\log", "warning")

    def tearDown(self):
        self.app_ctx.pop()

    def test_clear_locations(self):
        # Create a location not connected to anything else.
        lbl = lbl_location
        city_name = "Hillesheim"
        props = dict(city=city_name)
        loc_node = self.ns.create_node(lbl, **props)
        self.assertTrue(isinstance(loc_node, Node))
        self.assertEqual(loc_node["city"], city_name)
        # Clear locations not connected to anything else
        self.ns.clear_locations()
        loc_node = self.ns.get_node(lbl, **props)
        self.assertFalse(loc_node)

    def test_nodelist_from_cursor(self):
        query = "MATCH (n:Person) RETURN n"
        res = self.ns.get_query(query)
        nodelist = neostore.nodelist_from_cursor(res)
        self.assertTrue(isinstance(nodelist, list))
        self.assertTrue(isinstance(nodelist[0], Node))
        query = "MATCH (n:DoesNotExist) RETURN n"
        res = self.ns.get_query(query)
        nodelist = neostore.nodelist_from_cursor(res)
        self.assertFalse(nodelist)

    def test_remove_relation(self):
        nr_nodes = self.ns.get_nodes()
        # First create 2 nodes and a relation
        label = "TestNode"
        node1_params = dict(
            testname="Node1"
        )
        node1_node = self.ns.create_node(label, **node1_params)
        node2_params = dict(
            testname="Node2"
        )
        node2_node = self.ns.create_node(label, **node2_params)
        rel = "TestRel"
        self.ns.create_relation(from_node=node1_node, rel=rel, to_node=node2_node)
        # Then remove the relation
        self.ns.remove_relation_node(start_node=node1_node, end_node=node2_node, rel_type=rel)
        self.ns.remove_node_force(node1_node["nid"])
        self.ns.remove_node_force(node2_node["nid"])
        self.assertEqual(self.ns.get_nodes(), nr_nodes)

    def test_get_nodes(self):
        nr_nodes = self.ns.get_nodes()
        # First create 2 nodes and a relation
        label = "Test_Get_Nodes"
        node1_params = dict(
            testname="Node1"
        )
        # Verify that node does not exist
        self.assertFalse(self.ns.get_node(label, **node1_params))
        self.assertFalse(self.ns.get_nodes(label, **node1_params))
        node1_node = self.ns.create_node(label, **node1_params)
        # Test if Nodes are found
        res = self.ns.get_nodes(label, **node1_params)
        self.assertEqual(len(res), 1)
        res_node_1 = res[0]
        self.assertEqual(node1_node, res_node_1)
        self.assertEqual(res_node_1["testname"], "Node1")
        node2_params = dict(
            testname="Node2"
        )
        node2_node = self.ns.create_node(label, **node2_params)
        res = self.ns.get_node(label)
        self.assertEqual(len(res), 2)
        # Remove res_node_1
        self.ns.remove_node_force(res_node_1["nid"])
        # Get remaining node with label Test_Get_Nodes
        res = self.ns.get_nodes(label)
        res_node_2 = res[0]
        self.assertEqual(res_node_2, node2_node)
        self.ns.remove_node_force(res_node_2["nid"])
        # Verify all nodes are removed
        self.assertFalse(self.ns.get_nodes(label))
        # Check same number of nodes at the end as on the beginning
        self.assertEqual(self.ns.get_nodes(), nr_nodes)

    def test_node_count(self):
        # 2 MF Nodes
        label = "MF"
        nr = len(self.ns.get_nodes(label))
        self.assertEqual(nr, 2)
        # 2 OrgType Nodes
        label = "OrgType"
        nr = len(self.ns.get_nodes(label))
        self.assertEqual(nr, 2)
        # 1 User Node
        label = "User"
        nr = len(self.ns.get_nodes(label))
        self.assertEqual(nr, 1)
        # 12 Category Nodes
        label = "Category"
        nr = len(self.ns.get_nodes(label))
        self.assertEqual(nr, 12)
        # 1 CategoryGroup Node
        label = "categoryGroup"
        nr = len(self.ns.get_nodes(label))
        self.assertEqual(nr, 1)

    def test_get_endnode(self):
        # First check that I can get a single end node for normal usage.
        lbl = "Person"
        my_name = "Dirk Vermeylen"
        props = dict(name=my_name)
        start_node = self.ns.get_node(lbl, **props)
        self.assertTrue(isinstance(start_node, Node))
        self.assertEqual(start_node["name"], my_name)
        rel_type = person2category
        end_node = self.ns.get_endnode(start_node, rel_type)
        self.assertTrue(isinstance(end_node, Node))
        self.assertEqual(end_node["name"], "Masters +50")
        # Check I get multiple results if relation type is not specified
        end_node = self.ns.get_endnode(start_node)
        self.assertTrue(isinstance(end_node, Node))
        # I also get multiple relations for relation type "is"
        rel_type = person2participant
        end_node = self.ns.get_endnode(start_node, rel_type)
        self.assertTrue(isinstance(end_node, Node))
        # No return on invalid relation
        rel_type = "DoesNotExist"
        end_node = self.ns.get_endnode(start_node, rel_type)
        self.assertFalse(end_node)
        # No return on invalid Node
        start_node = "DoesNotExist"
        end_node = self.ns.get_endnode(start_node, rel_type)
        self.assertFalse(end_node)

    def test_get_endnodes(self):
        # First check that I can get a single end node.
        lbl = "Person"
        my_name = "Dirk Vermeylen"
        props = dict(name=my_name)
        start_node = self.ns.get_node(lbl, **props)
        self.assertTrue(isinstance(start_node, Node))
        self.assertEqual(start_node["name"], my_name)
        rel_type = person2category
        end_nodes = self.ns.get_endnodes(start_node, rel_type)
        self.assertEqual(len(end_nodes), 1)
        self.assertTrue(isinstance(end_nodes[0], Node))
        self.assertEqual(end_nodes[0]["name"], "Masters +50")
        # Check I get multiple results if relation type is not specified
        end_nodes = self.ns.get_endnodes(start_node)
        self.assertTrue(len(end_nodes) > 1)
        # I also get multiple relations for relation type "is"
        rel_type = person2participant
        end_nodes = self.ns.get_endnodes(start_node, rel_type)
        self.assertTrue(len(end_nodes) > 1)
        # No return on invalid relation
        rel_type = "DoesNotExist"
        end_nodes = self.ns.get_endnodes(start_node, rel_type)
        self.assertFalse(end_nodes)
        # No return on invalid Node
        start_node = "DoesNotExist"
        end_nodes = self.ns.get_endnodes(start_node, rel_type)
        self.assertFalse(end_nodes)

    def test_get_location_nodes(self):
        res = self.ns.get_location_nodes()
        self.assertTrue(isinstance(res, list))
        self.assertTrue(isinstance(res[0]["city"], str))
        for n in res:
            print(n["city"])

    def test_get_race4person(self):
        lbl = lbl_person
        props = dict(name="Dirk Vermeylen")
        person_node = self.ns.get_node(lbl, **props)
        res = self.ns.get_race4person(person_node["nid"])
        self.assertTrue(isinstance(res, list))
        first_race = res[0]
        self.assertTrue(isinstance(first_race["part"], dict))
        self.assertTrue(isinstance(first_race["race"], dict))
        self.assertTrue(isinstance(first_race["date"], dict))
        self.assertTrue(isinstance(first_race["org"], dict))
        self.assertTrue(isinstance(first_race["orgtype"], dict))
        self.assertTrue(isinstance(first_race["loc"], dict))
        # Test on invalid node
        lbl = lbl_organization
        props = dict(name="Veldloop Arendonk")
        person_node = self.ns.get_node(lbl, **props)
        res = self.ns.get_race4person(person_node["nid"])
        self.assertFalse(res)
        res = self.ns.get_race4person("DoesNotExist")
        self.assertFalse(res)

    def test_get_race_list(self):
        # First get org_id for organization
        lbl = lbl_organization
        props = dict(name="Veldloop Arendonk")
        org_node = self.ns.get_node(lbl, **props)
        race_list = self.ns.get_race_list(org_node["nid"])
        self.assertTrue(isinstance(race_list, list))
        first_race = race_list[0]
        self.assertTrue(isinstance(first_race, dict))
        self.assertTrue(lbl_race in first_race["race"].labels)
        self.assertTrue(lbl_mf in first_race["mf"].labels)
        # Also test False for non-existing organization (other node type or invalid node type)
        lbl = lbl_person
        props = dict(name="Dirk Vermeylen")
        name_node = self.ns.get_node(lbl, **props)
        race_list = self.ns.get_race_list(name_node["nid"])
        self.assertFalse(race_list)
        race_list = self.ns.get_race_list("DoesNotExist")
        self.assertFalse(race_list)

    def test_get_startnode(self):
        # First check that I can get a single start node for normal usage.
        lbl = "Location"
        my_name = "Mol"
        props = dict(city=my_name)
        end_node = self.ns.get_node(lbl, **props)
        self.assertTrue(isinstance(end_node, Node))
        self.assertEqual(end_node["city"], my_name)
        rel_type = org2loc
        start_node = self.ns.get_startnode(end_node, rel_type)
        self.assertTrue(isinstance(start_node, Node))
        self.assertEqual(start_node["name"], "Cross Cup")
        # Check I get no failure if relation type is not specified
        start_node = self.ns.get_startnode(end_node)
        self.assertTrue(isinstance(start_node, Node))
        # No return on invalid relation
        rel_type = "DoesNotExist"
        start_node = self.ns.get_startnode(end_node, rel_type)
        self.assertFalse(start_node)
        # No return on invalid Node
        end_node = "DoesNotExist"
        start_node = self.ns.get_startnode(end_node, rel_type)
        self.assertFalse(start_node)


if __name__ == "__main__":
    unittest.main()
