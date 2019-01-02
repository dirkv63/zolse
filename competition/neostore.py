"""
This class consolidates functions related to the neo4J datastore.
"""

import os
import uuid
from competition.lib.neostructure import *
from datetime import datetime, date
from flask import current_app
from pandas import DataFrame
from py2neo import Database, Graph, Node, Relationship, NodeMatcher, RelationshipMatch


# Todo: Review on IF True/False, test on ininstance() instead
class NeoStore:

    def __init__(self):
        """
        Method to instantiate the class in an object for the neostore.

        :return: Object to handle neostore commands.
        """
        self.graph = self.connect2db()
        self.nodematcher = NodeMatcher(self.graph)
        return

    @staticmethod
    def connect2db():
        """
        Internal method to create a database connection. This method is called during object initialization.
        Database initialization variables need to be set in environment.

        :return: Database handle and cursor for the database.
        """
        neo4j_config = {
            'user': os.environ["NEO4J_USER"],
            'password': os.environ["NEO4J_PWD"]
        }
        if os.environ.get("NEO4J_HOST"):
            host = os.environ["NEO4J_HOST"]
            neo4j_config['host'] = host
        # Check that Neo4J is running the expected Neo4J Store - to avoid accidents...
        connected_db = Database(**neo4j_config)
        if connected_db.config["dbms.active_database"] != os.environ['NEO4J_DB']:
            msg = "Connected to Neo4J database {d}, but expected to be connected to {n}"\
                .format(d=connected_db.config["dbms.active_database"], n=os.environ['NEO4J_DB'])
            current_app.logger.fatal(msg)
            raise SystemExit()
        # Connect to Graph
        graph = Graph(**neo4j_config)
        return graph

    def clear_locations(self):
        """
        This method will check if there are orphan locations. These are locations without relations. These locations
        can be removed.

        :return:
        """
        # Note that you could DETACH DELETE location nodes here, but then you miss the opportunity to log what is
        # removed.
        query = """
            MATCH (loc:Location) WHERE NOT (loc)--() RETURN loc
        """
        cursor = self.graph.run(query)
        while cursor.forward():
            rec = cursor.current
            loc = rec['loc']
            current_app.logger.info("Remove location {city}".format(city=loc['city']))
            self.remove_node(loc)
        return

    def create_node(self, *labels, **props):
        """
        Function to create node. The function will return the node object.
        Note that a 'nid' attribute will be added to the node. This is a UUID4 unique identifier. This is a temporary
        solution cause there seems to be no other way to extract the node ID from a node.

        :param labels: Labels for the node
        :param props: Value dictionary with values for the node.
        :return: Node that has been created.
        """
        props['nid'] = str(uuid.uuid4())
        current_app.logger.warning("Trying to create node with params {p}".format(p=props))
        component = Node(*labels, **props)
        self.graph.create(component)
        return component

    def create_relation(self, from_node=None, rel=None, to_node=None):
        """
        Function to create relationship between nodes.

        :param from_node: Start node for the relation
        :param rel: Relation type
        :param to_node: End node for the relation
        :return:
        """
        rel = Relationship(from_node, rel, to_node)
        self.graph.merge(rel)
        return

    def clear_date_node(self, label):
        """
        This method will clear every date node as specified by label. Label can be Day, Month or Year. The node will be
        deleted if not used anymore. So it can have only one incoming relation: DAY - MONTH or YEAR.
        Therefore find all relations. If there is only one, then the date node can be deleted.

        :param label: Day, Month or Year
        :return:
        """
        current_app.logger.info("Clearing all date nodes with label {lbl}".format(lbl=label))
        query = """
            MATCH (n:{label})-[rel]-()
            WITH n, count(rel) as rel_cnt
            WHERE rel_cnt=1
            DETACH DELETE n
        """.format(label=label.capitalize())
        self.graph.run(query)
        return

    def clear_date(self):
        """
        This method will clear dates that are no longer connected to an organization, a person's birthday or any other
        item.
        First find days with one relation only, this must be a connection to the month. Remove these days.
        Then find months with one relation only, this must be a connection to the year. Remove these months.
        Finally find years with one relation only, this must be a connection to the Gregorian calendar. Remove these
        years.
        Compare with method remove_date(ds), that will check to remove only a specific date.

        :return:
        """
        # First Remove Days
        self.clear_date_node("Day")
        self.clear_date_node("Month")
        self.clear_date_node("Year")
        return

    def date_node(self, ds):
        """
        This method will get a datetime.date timestamp and return the associated node. The calendar module will
        ensure that the node is created if required.

        :param ds: datetime.date representation of the date, or Calendar key 'YYYY-MM-DD'.
        :return: node associated with the date, of False (ds could not be formatted as a date object).
        """
        # If date format is string, make sure it is a valid date.
        if isinstance(ds, str):
            try:
                ds = datetime.strptime(ds, '%Y-%m-%d').date()
            except ValueError:
                current_app.logger.error("Trying to set date {ds} but got a value error".format(ds=ds))
                return False
        if isinstance(ds, date):
            props = dict(
                key=ds.strftime('%Y-%m-%d')
            )
            lbl = lbl_day
            date_node = self.get_node(lbl, **props)
            if not date_node:
                date_node = self.create_node(lbl, **props)
            return date_node
        else:
            return False

    def get_endnode(self, start_node=None, rel_type=None):
        """
        This method will calculate the end node from an start Node and a relation type. If relation type is not
        specified then any relation type will do.
        The purpose of the function is to find a single end node. If there are multiple end nodes, then a random one
        is returned and an error message will be displayed.

        :param start_node: Start node.
        :param rel_type: Relation type
        :return: End Node, or False.
        """
        if not isinstance(start_node, Node):
            current_app.logger.error("Attribute not type Node (instead type {t})".format(t=type(start_node)))
            return False
        rels = RelationshipMatch(self.graph, (start_node, None), r_type=rel_type)
        if rels.__len__() == 0:
            current_app.logger.warning("No end node found for start node ID: {nid} and relation: {rel}"
                                       .format(nid=start_node["nid"], rel=rel_type))
            return False
        elif rels.__len__() > 1:
            current_app.logger.warning("More than one end node found for start node ID {nid} and relation {rel},"
                                       " returning first".format(nid=start_node["nid"], rel=rel_type))
        return rels.first().end_node

    def get_endnodes(self, start_node=None, rel_type=None):
        """
        This method will calculate all end nodes from a start Node and a relation type. If relation type is not
        specified then any relation type will do.
        The purpose of the function is to find all end nodes.

        :param start_node: Start node.
        :param rel_type: Relation type
        :return: List with End Nodes.
        """
        if not isinstance(start_node, Node):
            current_app.logger.error("Attribute not type Node (instead type {t})".format(t=type(start_node)))
            return False
        node_list = [rel.end_node
                     for rel in RelationshipMatch(self.graph, (start_node, None), r_type=rel_type)]
        # Convert to set to remove duplicate end nodes
        node_set = set(node_list)
        # Then return the result as a list
        return list(node_set)

    def get_cat4part(self, part_nid):
        """
        This method will return category NID for the participant.

        :param part_nid: Nid of the participant node.
        :return: Category NID, or False if no category could be found.
        """
        query = "MATCH (n:Participant {nid:{p}})<-[:is]-()-[:inCategory]->(c:Category) RETURN c.nid as nid"
        res = self.graph.run(query, p=part_nid)
        try:
            rec = res.next()
        except StopIteration:
            return False
        return rec["nid"]

    def get_category_nodes(self):
        """
        This function returns the category nodes in sequence

        :return: List of category nodes in sequence.
        """
        res = []
        query = "MATCH (cat:Category) RETURN cat ORDER BY cat.seq"
        cursor = self.graph.run(query)
        while cursor.forward():
            res.append(cursor.current["cat"])
        return res

    def get_location_nodes(self):
        """
        This function returns the location nodes in sequence

        :return: List of location nodes in sequence.
        """
        res = []
        query = "MATCH (n:Location) RETURN n ORDER BY n.city"
        cursor = self.graph.run(query)
        while cursor.forward():
            rec = cursor.current
            res.append(rec["n"])
        return res

    def get_node(self, *labels, **props):
        """
        This method will select a single (or first) node that have labels and properties

        :param labels: List of labels that are required for node match.
        :param props: Property dictionary required to match.
        :return: node that fulfills the criteria, or False if there is no node
        """
        nodes = self.get_nodes(*labels, **props)
        if not nodes:
            current_app.logger.debug("Looking for 1 node for label {lbl} and props {p}, found none."
                                     .format(lbl=labels, p=props))
            return False
        elif len(nodes) > 1:
            current_app.logger.error("Expected 1 node for label {lbl} and props {p}, found many {m}."
                                     .format(lbl=labels, p=props, m=len(nodes)))
        return nodes[0]

    def get_nodes(self, *labels, **props):
        """
        This method will select all nodes that have labels and properties

        :param labels: List of labels that are required for node match
        :param props: Property dictionary required to match.
        :return: list of nodes that fulfill the criteria, or False if no nodes are found.
        """
        nodes = self.nodematcher.match(*labels, **props)
        nodelist = [node for node in nodes]
        if len(nodelist) == 0:
            # No nodes found that fulfil the criteria
            return False
        else:
            return nodelist

    def get_nodes_no_nid(self):
        """
        This method will select all nodes that have no nid. A nid will be added since this is used as unique reference
        for the node in relations.

        :return: count of number of nodes that have been updated.
        """
        query = "MATCH (n) WHERE NOT EXISTS (n.nid) RETURN id(n) as node_id"
        res = self.graph.run(query)
        cnt = 0
        for rec in res:
            self.set_node_nid(node_id=rec["node_id"])
            cnt += 1
        return cnt

    def get_organization_list(self):
        """
        This method will get a list of all organizations. Each item in the list is a dictionary with fields date,
        organization, city, id (for organization nid) and type.

        :return:
        """
        query = """
            MATCH (day:Day)<-[:On]-(org:Organization)-[:In]->(loc:Location),
                  (org)-[:type]->(ot:OrgType)
            RETURN day.key as date, org.name as organization, loc.city as city, org.nid as id, ot.name as type
            ORDER BY day.key ASC
        """
        res = self.graph.run(query).data()
        # Convert date key from YYYY-MM-DD to DD-MM-YYYY
        for rec in res:
            rec["date"] = datetime.strptime(rec["date"], "%Y-%m-%d").strftime("%d-%m-%Y")
        return res

    def get_part_for_org(self, org_id):
        """
        This method will return a list of people that participate in a race for this organization.

        :param org_id: Nid of the organization
        :return:
        """
        query = """
            MATCH (n:Organization)-[:has]->(m:Race)<-[:participates]-(d:Participant)<-[:is]-(p:Person)
            WHERE n.nid = '{org_id}'
            RETURN p
        """.format(org_id=org_id)
        res = self.graph.run(query)
        return nodelist_from_cursor(res)

    def get_next_parts_for_race(self, race_id):
        """
        This method will get the list of people that can be the next participant of the race. So they are in the range
        of the race, but not yet selected as a participant in this race or another race for this organization (e.g.
        participant for the short cross will not participate in the long cross)..

        :param race_id: Nid of the race.
        :return: Person node list for potential participants.
        """
        query = """
            MATCH (org:Organization)-[:has]->(race:Race)-[:forCategory]->(cat:Category),
                (race)-[:forMF]-(mf:MF),
                (person:Person)-[:inCategory]->(cat),
                (person)-[:mf]->(mf)
            WHERE race.nid='{race_id}'
            AND NOT EXISTS ((person)-[:is]->(:Participant)-[:participates]->(:Race)<-[:has]-(org:Organization))
            RETURN person
        """.format(race_id=race_id)
        res = self.graph.run(query)
        return nodelist_from_cursor(res)

    def get_part_range_for_race(self, race_id):
        """
        This method will get the range of people that can participate in the race. So everyone who is in one of the race
        categories and required MF.

        :param race_id:
        :return:
        """
        query = """
            MATCH (race:Race)-[:forCategory]->(cat:Category),
                (race)-[:forMF]-(mf:MF),
                (person:Person)-[:inCategory]->(cat),
                (person)-[:mf]->(mf)
                WHERE race.nid='{race_id}'
                RETURN (person)
        """.format(race_id=race_id)
        res = self.graph.run(query)
        return nodelist_from_cursor(res)

    def get_persons_in_organization(self, org_name):
        """
        This method will get the person nid for the participants in an organization. This can be used to do the special
        point calculation, e.g. +3 points for PK, +10 points for BK, ...

        :param org_name: Name of the organization
        :return: list of person nid that participate in the organization
        """
        query = """
            MATCH (person:Person)-[:is]->(part:Participant)-[:participates]->(race:Race),
            (race)<-[:has]-(org {name: {org_name}})
            RETURN person.nid as person_nid
        """
        res = self.graph.run(query, org_name=org_name).data()
        person_list = []
        for rec in res:
            person_list.append(rec["person_nid"])
        return person_list

    def get_participant_in_race(self, pers_id=None, race_id=None):
        """
        This function will for a person get the participant node in a race, or False if the person did not
        participate in the race according to current information in the database.

        :param pers_id:
        :param race_id:
        :return: participant node, or False
        """
        query = """
            MATCH (pers:Person)-[:is]->(part:Participant)-[:participates]->(race:Race)
            WHERE pers.nid='{pers_id}' AND race.nid='{race_id}'
            RETURN part
        """.format(pers_id=pers_id, race_id=race_id)
        res = self.graph.run(query)
        nodes = nodelist_from_cursor(res)
        if len(nodes) > 1:
            current_app.logger.error("More than one ({nr}) Participant node for Person {pnid} and Race {rnid}"
                                     .format(pnid=pers_id, rnid=race_id, nr=len(nodes)))
        elif len(nodes) == 0:
            return False
        return nodes[0]

    def get_participant_seq_list(self, race_id):
        """
        This method will return a list of participant nodes in sequence of arrival for a particular race.

        :param race_id:
        :return: Node list
        """
        query = """
            MATCH race_ptn = (race)<-[:participates]-(participant),
                  participants = (participant)<-[:after*0..]-()
            WHERE race.nid = '{race_id}'
            WITH COLLECT(participants) AS results, MAX(length(participants)) AS maxLength
            WITH FILTER(result IN results WHERE length(result) = maxLength) AS result_coll
            UNWIND result_coll as result
            RETURN nodes(result)
        """.format(race_id=race_id)
        # Get the result of the query in a recordlist
        cursor = self.graph.run(query)
        try:
            rec = cursor.next()
        except StopIteration:
            return False
        return rec["nodes(result)"]

    def points_race(self, mf, cat, orgtype):
        """
        This query will for the specified mf and category collect every participant and points for the participation
        for every person in the category.

        :param mf: Dames / Heren
        :param cat: Category Nid
        :param orgtype: Wedstrijd / Deelname
        :return: A dataframe with records having the person_nid and points for each participation on every race.
        """
        query = """
            MATCH (person:Person)-[:mf]->(mf:MF  {name: {mf}}),
                  (person)-[:inCategory]->(cat:Category {nid: {cat}}),
                  (person)-[:is]->(part)-[:participates]-(race:Race),
                  (race)<-[:has]-(org:Organization),
                  (org)-[:type]->(orgtype:OrgType {name: {orgtype}})
            RETURN person.nid as person_nid, part.points as points
        """
        res = self.graph.run(query, mf=mf, cat=cat, orgtype=orgtype).data()
        return DataFrame(res)

    def get_query(self, query):
        """
        This method accepts a Cypher query as parameter, runs the query and returns the result as a cursor.

        :param query: Cypher Query to run
        :return: Result of the Cypher Query as a cursor
        """
        return self.graph.run(query)

    def get_race_list(self, org_id):
        """
        This function will get an organization nid and return the Races associated with the Organization.
        The races will be returned as a list of dictionaries with fields race node and mf node.

        :param org_id: nid of the Organization.
        :return: List of dictionaries with race and mf nodes sorted on category and mf, or empty list which evaluates to
        False.
        """
        query = """
            MATCH (org:Organization)-[:has]->(race:Race)-[:forMF]->(mf:MF)
            WHERE org.nid = '{org_id}'
            RETURN race, mf
            ORDER BY race.seq, mf.name
        """.format(org_id=org_id)
        res = self.graph.run(query)
        # Convert result set in an array of nodes
        res_arr = []
        while res.forward():
            rec = res.current
            race_nodes = dict(
                race=rec["race"],
                mf=rec["mf"]
            )
            res_arr.append(race_nodes)
        return res_arr

    def get_race4person(self, person_id):
        """
        This method will get a list of participant information for a person, sorted on date. The information will be
        provided in a list of dictionaries. The dictionary values are the corresponding node dictionaries.

        :param person_id:
        :return: list of Participant (part),race, date, organization (org) and orgtype and Location (loc) Node
        dictionaries in date sequence.
        """
        race4person = []
        query = """
            MATCH (person:Person)-[:is]->(part:Participant)-[:participates]->(race:Race),
                  (race)<-[:has]-(org:Organization)-[:On]->(day:Day),
                  (org)-[:type]->(orgtype),
                  (org)-[:In]->(loc:Location)
            WHERE person.nid='{pers_id}'
            RETURN race, part, day, org, orgtype, loc
            ORDER BY day.key ASC
        """.format(pers_id=person_id)
        cursor = self.graph.run(query)
        while cursor.forward():
            rec = cursor.current
            res_dict = dict(part=dict(rec['part']),
                            race=dict(rec['race']),
                            date=dict(rec['day']),
                            org=dict(rec['org']),
                            orgtype=dict(rec['orgtype']),
                            loc=dict(rec['loc']))
            race4person.append(res_dict)
        return race4person

    def get_race_seq(self, race_id):
        """
        This method will calculate the sequence for the race with nid race_id. The calculated sequence is the lowest
        sequence for the associated categories.

        :param race_id: nid of the race.
        :return: lowest sequence number of the associated categories.
        """
        query = """
            MATCH (race:Race)-[:forCategory]->(category:Category)
            WHERE race.nid = '{race_id}'
            RETURN category.seq AS seq
            ORDER BY category.seq
            LIMIT 1
        """.format(race_id=race_id)
        res = self.graph.run(query).data()[0]
        return res['seq']

    def get_startnode(self, end_node=None, rel_type=None):
        """
        This method will calculate the start node from an end Node and a relation type. If relation type is not
        specified then any relation type will do.
        The purpose of the function is to find a single start node. If there are multiple start nodes, then a random
        one is returned and an error message will be displayed.

        :param end_node: End node.
        :param rel_type: Relation type
        :return: Start Node, or False.
        """
        if not isinstance(end_node, Node):
            current_app.logger.error("Attribute not type Node (instead type {t})".format(t=type(end_node)))
            return False
        rels = RelationshipMatch(self.graph, (None, end_node), r_type=rel_type)
        if rels.__len__() == 0:
            current_app.logger.warning("No start node found for end node ID: {nid} and relation: {rel}"
                                       .format(nid=end_node["nid"], rel=rel_type))
            return False
        elif rels.__len__() > 1:
            current_app.logger.warning("More than one start node found for end node ID {nid} and relation {rel},"
                                       " returning first".format(nid=end_node["nid"], rel=rel_type))
        return rels.first().start_node

    def get_startnodes(self, end_node=None, rel_type=None):
        """
        This method will calculate all start nodes from an end Node and a relation type. If relation type is not
        specified then any relation type will do.
        The purpose of the function is to find all start nodes.

        :param end_node: The end node.
        :param rel_type: Relation type
        :return: List with start nodes, or False.
        """
        if not isinstance(end_node, Node):
            current_app.logger.error("Attribute not type Node (instead type {t})".format(t=type(end_node)))
            return False
        node_list = [rel.start_node
                     for rel in RelationshipMatch(self.graph, (None, end_node), r_type=rel_type)]
        # Convert to set to remove duplicate end nodes
        node_set = set(node_list)
        # Then return the result as a list
        return list(node_set)

    def init_graph(self):
        """
        This method will initialize the graph. It will set indices and create nodes required for the application
        (on condition that the nodes do not exist already).

        :return:
        """
        stmt = "CREATE CONSTRAINT ON (n:{0}) ASSERT n.{1} IS UNIQUE"
        self.graph.run(stmt.format('Location', 'city'))
        self.graph.run(stmt.format('Person', 'name'))
        self.graph.run(stmt.format('RaceType', 'name'))
        self.graph.run(stmt.format('OrgType', 'name'))
        nid_labels = ['Participant', 'Person', 'Race', 'Organization', 'Location', 'RaceType', 'OrgType']
        stmt = "CREATE CONSTRAINT ON (n:{nid_label}) ASSERT n.nid IS UNIQUE"
        for nid_label in nid_labels:
            self.graph.run(stmt.format(nid_label=nid_label))

        return

    def node(self, nid):
        """
        This method will get a node ID and return a node, or false in case no Node can be associated with the ID.
        Py2neo Release 3.1.2 throws a IndexError in case a none-existing node ID is requested.

        Note that since there seems to be no way to extract the Node ID of a node, the nid attribute is used. As a
        consequence, it is not possible to use the node(nid).

        :param nid: ID of the node to be found.
        :return: Node, or False (None) in case the node could not be found.
        """
        selected = self.nodematcher.match(nid=nid)
        node = selected.first()
        return node

    @staticmethod
    def node_id(node_obj):
        """
        py2neo 3.1.2 doesn't have a method to get the ID from a node.
        Not sure how to get an ID from a node...
        Advice from Neo4J community seems to be not to use internal Node ID, since this can be reused when nodes are
        removed.
        For now each node has an attribute nid which contains a random node ID.

        :param node_obj: Node object
        :return: ID of the node (integer), or False.
        """
        # First check if my object is a node (not sure it is a node, but I am sure it is a sub-graph)
        if isinstance(node_obj, Node):
            # OK, my object is a node. Now return the nid attribute
            return node_obj['nid']
        else:
            current_app.logger.error("Node expected, but got object of type {nodetype}".format(nodetype=type(node_obj)))
            return False

    def node_props(self, nid=None):
        """
        This method will get a node and return the node properties in a dictionary.
        This method can be used to add or modify one property and update the node. The application does not need to know
        all node attributes, only the attribute that is changed.

        :param nid: nid of the node required
        :return: Dictionary of the node properties
        """
        my_node = self.node(nid)
        if my_node:
            return dict(my_node)
        else:
            current_app.logger.error("Could not bind ID {node_id} to a node.".format(node_id=nid))
            return False

    def node_set_attribs(self, **properties):
        """
        This method will set specified properties on the node. Modified properties will be updated and new properties
        will be added. Properties not in the dictionary will be left unchanged.
        Compare with method node_update, where node property set matches the **properties dictionary.
        nid needs to be part of the properties dictionary.

        :param properties: Dictionary of the property set for the node. 'nid' property is mandatory.
        :return: True if successful update, False otherwise.
        """
        try:
            my_node = self.node(properties["nid"])
        except KeyError:
            current_app.logger.error("Attribute 'nid' missing, required in dictionary.")
            return False
        # So I'm sure that nid is still in the property dictionary
        if my_node:
            # Modify properties and add new properties
            for prop in properties:
                my_node[prop] = properties[prop]
            # Now push the changes to Neo4J database.
            self.graph.push(my_node)
            return True
        else:
            current_app.logger.error("No node found for NID {nid}".format(nid=properties["nid"]))
            return False

    def node_update(self, **properties):
        """
        This method will update the node's properties with the properties specified. Modified properties will be
        updated, new properties will be added and removed properties will be deleted.
        Compare with method node_set_attribs, where node properties are never removed.
        nid needs to be part of the properties dictionary.

        :param properties: Dictionary of the property set for the node. 'nid' property is mandatory.
        :return: Updated node if successful, False otherwise.
        """
        try:
            my_node = self.node(properties["nid"])
        except KeyError:
            current_app.logger.error("Attribute 'nid' missing, required in dictionary.")
            return False
        if isinstance(my_node, Node):
            curr_props = self.node_props(properties["nid"])
            # Remove properties
            remove_props = [prop for prop in curr_props if prop not in properties]
            for prop in remove_props:
                # Set value to None to remove a key.
                del my_node[prop]
            # Modify properties and add new properties
            # So I'm sure that nid is still in the property dictionary
            for prop in properties:
                my_node[prop] = properties[prop]
            # Now push the changes to Neo4J database.
            self.graph.push(my_node)
            return my_node
        else:
            current_app.logger.error("No node found for NID {nid}".format(nid=properties["nid"]))
            return False

    def relations(self, nid):
        """
        This method will check if node with ID has relations. Returns True if there are relations, returns False
        otherwise. Do not use graph.degree, because there seems to be a strange error when running on graphenedb...

        :param nid: ID of the object to check relations
        :return: Number of relations - if there are relations, False - there are no relations.
        """
        # obj_node = self.node(nid)
        query = "MATCH (n)--(m) WHERE n.nid='{nid}' return m.nid as m_nid".format(nid=nid)
        res = self.graph.run(query).data()  # This will return the list of dictionaries with results.
        if len(res):
            return len(res)
        else:
            return False

    def remove_node(self, node):
        """
        This method will remove the node on condition that no relations are attached to the node.

        :param node: Node to be removed.
        :return: True if node is deleted, False otherwise
        """
        if not isinstance(node, Node):
            current_app.logger.error("Node expected, but got type {t} Input: {n}".format(t=type(node), n=node))
            return False
        degree = self.relations(node["nid"])
        if degree:
            msg = "Request to delete node nid {node_id}, but {x} relations found. Node not deleted"\
                .format(node_id=node["nid"], x=degree)
            current_app.logger.warning(msg)
            return False
        else:
            self.graph.delete(node)
            return True

    def remove_node_force(self, nid):
        """
        This method will remove node with ID node_id. The node and the relations to/from the node will also be deleted.
        Note that this needs to use nid instead of node, since graph.delete has a CONSTRAINT on relations.

        :param nid: nid of the node
        :return:
        """
        query = "MATCH (n) WHERE n.nid='{nid}' DETACH DELETE n".format(nid=nid)
        self.graph.run(query)
        return

    def remove_relation(self, start_nid=None, end_nid=None, rel_type=None):
        """
        This method will remove the relation rel_type between Node with nid start_nid and Node with nid end_nid.
        Relation is of type rel_type.

        :param start_nid: Node nid of the start node.
        :param end_nid: Node nid of the end node.
        :param rel_type: Type of the relation
        :return:
        """
        # Todo: this method needs to be replaced by remove_relation_node.
        query = """
            MATCH (start_node)-[rel_type:{rel_type}]->(end_node)
            WHERE start_node.nid='{start_nid}'
              AND end_node.nid='{end_nid}'
            DELETE rel_type
        """.format(rel_type=rel_type, start_nid=start_nid, end_nid=end_nid)
        self.graph.run(query)
        return

    def remove_relation_node(self, start_node=None, end_node=None, rel_type=None):
        """
        This method will remove the relation rel_type between start_node and end_node where relation is type rel_type.
        The goal is to use the

        :param start_node:
        :param end_node:
        :param rel_type:
        :return:
        """
        # Todo: rename the method to remove_relation.
        rel = Relationship(start_node, rel_type, end_node)
        # Do I need to merge first?
        self.graph.merge(rel)
        self.graph.separate(rel)
        return

    def set_node_nid(self, node_id):
        """
        This method will set a nid for node with node_id. This should be done only for calendar functions.

        :param node_id: Neo4J ID of the node
        :return: nothing, nid should be set.
        """
        query = "MATCH (n) WHERE id(n)={node_id} SET n.nid='{nid}' RETURN n.nid"
        self.graph.run(query.format(node_id=node_id, nid=str(uuid.uuid4())))
        return


def nodelist_from_cursor(cursor):
    """
    The py2neo Cursor will return a result list that is not necessarily unique. This function gets a cursor from
    a query where the cypher return argument is a single node. The function will return the list of unique nodes.

    :param cursor: Result of a query with single node per result line.
    :return: list of unique nodes, or empty list if there are no nodes.
    """
    node_list = set()
    while cursor.forward():
        current = cursor.current
        (node, ) = current.values()
        node_list.add(node)
    return list(node_list)


def validate_node(node, label):
    """
    BE CAREFUL: has_label does not always work for unknown reason.
    This function will check if a node is of a specific type, so it will check if the node has the label.

    :param node: Node to check
    :param label: Label that needs to be in the node.
    :return: True, if label is in the node. False for all other reasons (e.g. node is not a node.
    """
    if type(node) is Node:
        return node.has_label(label)
    else:
        return False
