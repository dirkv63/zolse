"""
This procedure will test the neostore functionality. No Flask Application items are required.
"""

import unittest
from competition import create_app
from competition.lib import neostore
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
        self.ns.remove_orphan_nodes(lbl)
        loc_node = self.ns.get_node(lbl, **props)
        self.assertFalse(loc_node)

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
        rel_type = person2mf
        end_node = self.ns.get_endnode(start_node, rel_type)
        self.assertTrue(isinstance(end_node, Node))
        self.assertEqual(end_node["name"], "Heren")
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
        rel_type = person2mf
        end_nodes = self.ns.get_endnodes(start_node, rel_type)
        self.assertEqual(len(end_nodes), 1)
        self.assertTrue(isinstance(end_nodes[0], Node))
        self.assertEqual(end_nodes[0]["name"], "Heren")
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

    def test_get_nodes_no_nid(self):
        res = self.ns.get_nodes_no_nid()
        lbl = "TestNode"
        props = dict(name="nodeNoNid")
        component = Node(lbl, **props)
        self.ns.graph.create(component)
        new_res = self.ns.get_nodes_no_nid()
        self.assertEqual(new_res, res+1)
        self.ns.remove_node(component)
        rem_res = self.ns.get_nodes_no_nid()
        self.assertEqual(rem_res, res)

    def test_get_startnode(self):
        # First check that I can get a single start node for normal usage.
        lbl = "Location"
        my_name = "Mol"
        props = dict(city=my_name)
        end_node = self.ns.get_node(lbl, **props)
        self.assertTrue(isinstance(end_node, Node))
        self.assertEqual(end_node["city"], my_name)
        rel_type = organization2location
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

    def test_nr_relations(self):
        self.assertTrue(isinstance(self.ns.get_nr_relations(), int))

    def test_remove_orphan_nodes(self):
        # Count number of nodes and relations to start with.
        nr_nodes_start = len(self.ns.get_nodes())
        nr_rels_start = self.ns.get_nr_relations()
        lbl = "TestNode"
        testnames = ["test1", "test2"]
        for name in  testnames:
            props = dict(name=name)
            self.ns.create_node(lbl, **props)
        # Check number of nodes = start +2, number of relations did not change.
        self.assertEqual(len(self.ns.get_nodes()), nr_nodes_start + len(testnames))
        self.assertEqual(self.ns.get_nr_relations(), nr_rels_start)
        self.ns.remove_orphan_nodes(lbl)
        # Count number of nodes and relations at end.
        self.assertEqual(len(self.ns.get_nodes()), nr_nodes_start)
        self.assertEqual(self.ns.get_nr_relations(), nr_rels_start)


if __name__ == "__main__":
    unittest.main()
