import datetime
from competition import lm
from competition.lib import my_env, neostore
from competition.lib.neostructure import *
from flask import current_app
from flask_login import UserMixin
from py2neo.data import Node
from werkzeug.security import generate_password_hash, check_password_hash

ns = neostore.NeoStore()

# mf_tx translates from man/vrouw (form value to Node name).
mf_tx = dict(
    man="Heren",
    vrouw="Dames"
)
# mf_tx_inf translates from Node name to man/vrouw value.
mf_tx_inv = {y: x for x, y in mf_tx.items()}

# Calculate points
points_deelname = 20


class User(UserMixin):
    """
    The user class manages the registered users of the application. The Person class is for the people that participate
    in the race.
    """
    def __init__(self, user_id=None):
        if user_id:
            self.user_node = ns.node(user_id)
        else:
            self.user_node = "NotDefined"

    def __repr__(self):
        return "<User: {user}>".format(user=self.user_node["name"])

    def find(self, username):
        """
        This function will find the User object for the user with the specified username.
        If found, then the hashed password is returned. If not found, False is returned.

        :param username:
        :return: User node, then the caller can do whatever he wants with the information.
        """
        label = "User"
        props = dict(name=username)
        user_node = ns.get_node(label, **props)
        if user_node:
            try:
                self.user_node = user_node
                return self.user_node
            except KeyError:
                # Password not defined for user, return False
                return False
        else:
            # User not defined
            return False

    def get_id(self):
        return self.user_node["nid"]

    def register(self, username, password):
        if self.find(username):
            return False
        else:
            label = "User"
            props = dict(
                name=username,
                pwd=generate_password_hash(password)
            )
            user_node = ns.create_node(label, **props)
            return user_node["nid"]

    def validate_password(self, name, pwd):
        """
        Find the user. If the user exists, verify the password. If the passwords match, return nid of the User node.
        If the passwords don't match, return False.
        If the user does not exists, return False.

        :param name:
        :param pwd:
        :return:
        """
        if self.find(name):
            return check_password_hash(self.user_node["pwd"], pwd)
        else:
            return False


@lm.user_loader
def load_user(user_id):
    """
    This function will return the User object. user_id is the nid of the User node.

    :param user_id: nid of the user node.
    :return: user object.
    """
    return User(user_id)


class Participant:

    # List of calculated properties for the participant node.
    calc_props = ["nid", "points", "rel_pos"]

    def __init__(self, part_id=None, race_id=None, person_id=None):
        """
        A Participant Object is the path: (person)-[:is]->(participant)-[:participates]->(race).
        If participant id is provided, then set race object and person object.
        If race id and person id are provided, then find participant node. If participant node does not exist then
        create it. The application must call the 'add' method and specify the previous runner.
        At the end of initialization, participant node, race object and person object are set.
        When a participant is added or deleted, then the points for the race will be recalculated.

        :param part_id: nid of the participant
        :param race_id: nid of the race
        :param person_id: nid of the person
        :return: Participant object with participant node and nid, race nid and person nid are set.
        """
        self.part_node = None
        if part_id:
            # I have a participant ID, find race and person information
            self.part_node = ns.node(part_id)
            race_node = ns.get_endnode(start_node=self.part_node, rel_type=participant2race)
            self.race = Race(race_id=race_node["nid"])
            person_node = ns.get_startnode(end_node=self.part_node, rel_type=person2participant)
            self.person = Person(person_id=person_node["nid"])
        elif person_id and race_id:
            self.race = Race(race_id=race_id)
            self.person = Person(person_id=person_id)
            self.part_node = self.get_node()
        else:
            current_app.logger.fatal("Insufficient input provided.")
            raise ValueError("CannotCreateObject")
        return

    def add(self, prev_person_id=None):
        """
        This method will add the participant in the chain of arrivals.
        If there is no previous person, then check for first arrival in race. If found, add first arrival with previous
        runner this participant.
        If there is previous person, check if there is next person. If so, remove link and add next person with previous
        runner  this participant.
        Create relation between previous person and this participant.
        Note that I cannot use a race.part_person method, since the current participant is in an invalid state.

        :param prev_person_id: nid of previous arrival, or -1 if current participant is first arrival
        :return:
        """
        if prev_person_id == '-1':
            # First arrival - was there another first arrival that needs to become second?
            next_person_id = self.race.part_person_first_id(excl_part_nid=self.get_nid())
            if isinstance(next_person_id, str):
                next_part = Participant(race_id=self.race.get_nid(), person_id=next_person_id)
                next_part.add(prev_person_id=self.get_nid())
        else:
            prev_part = Participant(race_id=self.race.get_nid(), person_id=prev_person_id)
            next_part_id = prev_part.next_runner()
            # Is previous runner not last? Add current runner in-between.
            if isinstance(next_part_id, str):
                next_part = Participant(part_id=next_part_id)
                next_part.remove()
                next_part.add(prev_person_id=self.get_nid())
            ns.create_relation(from_node=self.get_node(), rel=participant2participant, to_node=prev_part.get_node())
        return

    def delete(self):
        """
        This method will delete the participant node from the race. If there was a previous runner and a next runner,
        then connect next runner (arrival) to previous runner.
        Force remove the current participation node.

        :return:
        """
        prev_part_id = self.prev_runner()
        next_part_id = self.next_runner()
        ns.remove_node_force(self.get_nid())
        if isinstance(prev_part_id, str) and isinstance(next_part_id, str):
            prev_part = Participant(part_id=prev_part_id)
            next_part = Participant(part_id=next_part_id)
            next_part.add(prev_person_id=prev_part.get_person_nid())
        return

    def remove(self):
        """
        This method breaks the connection between the participant and the previous runner. It is an method that should
        only be called when a previous runner can be removed.

        :return:
        """
        prev_part_id = self.prev_runner()
        prev_part = Participant(part_id=prev_part_id)
        ns.remove_relation(start_node=self.get_node(), rel_type=participant2participant, end_node=prev_part.get_node())
        return

    def down(self):
        """
        This method will move the runner one position down in the race. Participant P start position:
        A<--P<--B<--C, end position A<--B<--P<--C.
        A and C are optional, B must exist.
        Find B, call up for B.

        :return:
        """
        next_part_nid = self.next_runner()
        if not isinstance(next_part_nid, str):
            current_app.logger.error("Method DOWN not possible because no next runner")
            return
        next_part = Participant(part_id=next_part_nid)
        next_part.up()
        return

    def up(self):
        """
        This method will move the runner one position up in the race. Participant P start position:
        A<--B<--P<--C, end position A<--P<--B<--C.
        A and C are optional, B must exist.

        :return:
        """
        prev_part_nid = self.prev_runner()
        if not isinstance(prev_part_nid, str):
            current_app.logger.error("Method UP not possible because no previous runner")
            return
        prev_part = Participant(part_id=prev_part_nid)
        prev2_part_nid = prev_part.prev_runner()
        next_part_nid = self.next_runner()
        self.remove()
        if isinstance(next_part_nid, str):
            next_part = Participant(part_id=next_part_nid)
            next_part.remove()
            next_part.add(prev_person_id=prev_part.get_person_nid())
        if isinstance(prev2_part_nid, str):
            prev_part.remove()
            prev2_part = Participant(part_id=prev2_part_nid)
            self.add(prev_person_id=prev2_part.get_person_nid())
        prev_part.add(prev_person_id=self.get_person_nid())
        return

    def create_node(self):
        """
        This method will create a participant node and link it to the person and the race.

        :return: participant node
        """
        part_node = ns.create_node(lbl_participant)
        ns.create_relation(from_node=self.person.get_node(), rel=person2participant, to_node=part_node)
        ns.create_relation(from_node=part_node, rel=participant2race, to_node=self.race.get_node())
        return part_node

    def get_nid(self):
        """
        This method will return the Participant Node ID of this person's participation in the race.

        :return: Participant Node ID (nid)
        """
        return self.part_node["nid"]

    def get_node(self):
        """
        This method will return the participant node for a known person and race. If the participant node does not
        exist, it will be created.

        :return: Participant node, or False if participant node does not exist.
        """
        query = """
            MATCH (pers:Person)-[:is]->(part:Participant)-[:participates]->(race:Race)
            WHERE pers.nid='{pers_id}' AND race.nid='{race_id}'
            RETURN part
        """.format(pers_id=self.person.get_nid(), race_id=self.race.get_nid())
        res = ns.get_query_data(query)
        if len(res) > 1:
            current_app.logger.error("More than one ({nr}) Participant node for Person {pnid} and Race {rnid}"
                                     .format(pnid=self.person.get_nid(), rnid=self.race.get_nid(), nr=len(res)))
        elif len(res) == 0:
            return self.create_node()
        return res[0]['part']

    def get_person_nid(self):
        """
        This method will return the Person Node ID for this participant.

        :return:
        """
        return self.person.get_nid()

    def get_props(self):
        """
        This method will get the properties for the node. All properties for the participant node will be collected,
        then the calculated properties (points, rel_pos, ...) will be removed from the dictionary.

        :return:
        """
        # Get participant node to ensure latest values for all calculated properties.
        # Ignore the user configurable properties, since these are managed in the **props dictionary.
        # Convert node to node-dictionary.
        part_dict = dict(self.part_node)
        # Remove calculated properties from dictionary
        for attrib in self.calc_props:
            part_dict.pop(attrib, None)
        return part_dict

    def get_race_nid(self):
        """
        This method will return the Race Node ID for this participant.

        :return: Nid of the race
        """
        return self.race.get_nid()

    def set_props(self, **props):
        """
        This method will set the properties for the node. The calculated properties (points, rel_pos, ...) will be
        collected from the participant node and added to the list of properties that are set by the user.

        :param props: list of user properties for the participant node.
        :return:
        """
        # ToDo: It may be better to use ns.node_set_attribs.
        # Get participant node to ensure latest values for all calculated properties.
        # Ignore the user configurable properties, since these are managed in the **props dictionary.
        # Convert node to node-dictionary. This ensures that KeyError exception can be used.
        part_dict = dict(self.part_node)
        for attrib in self.calc_props:
            try:
                props[attrib] = part_dict[attrib]
            except KeyError:
                pass
        return ns.node_update(**props)

    def prev_runner(self):
        """
        This method will get the node ID for this Participant's previous runner.
        The participant must have been created before.

        :return: ID of previous runner participant Node, False if there is no previous runner.
        """
        if not neostore.validate_node(self.part_node, "Participant"):       # pragma: no cover
            current_app.logger.error("Participant node expected, got {t}".format(t=type(self.part_node)))
            return False
        prev_part = ns.get_endnode(start_node=self.part_node, rel_type=participant2participant)
        if isinstance(prev_part, Node):
            return prev_part["nid"]
        else:
            return False

    def next_runner(self):
        """
        This method will get the node ID for this Participant's next runner.
        The participant must have been created before.

        :return: ID of next runner participant Node, False if there is no next runner.
        """
        if not neostore.validate_node(self.part_node, "Participant"):       # pragma: no cover
            current_app.logger.error("Participant node expected, got {t}".format(t=type(self.part_node)))
            return False
        next_part = ns.get_startnode(end_node=self.part_node, rel_type=participant2participant)
        if isinstance(next_part, Node):
            return next_part["nid"]
        else:
            return False


class Person:
    """
    A person is uniquely identified by the name. A person must have link to mf and to one category. The person object
    always has the person node.
    """
    # Todo: add a person.remove() method: remove MF link, check no participant links available.
    # Todo: add voornaam/familienaam

    def __init__(self, person_id=None):
        if person_id:
            self.person_node = self.get_node(person_id)
        else:
            self.person_node = None

    @staticmethod
    def find(name):
        """
        Find ID of the person with name 'name'. Return node ID, else return false.
        This function must be called from add(), so make it an internal function?

        :param name: Name of the person.
        :return: True if found (Person Node will be set in the object), or false if no node could be found.
        """
        props = {
            "name": name
        }
        person_node = ns.get_node("Person", **props)
        if isinstance(person_node, Node):
            return True
        else:
            return False

    def add(self, **props):
        """
        Attempt to add the person with name 'name'. The name must be unique. Person object is set to current
        participant. Name is set in this procedure, ID is set in the find procedure.

        :param props: Properties (in dict) for the person. Name, mf are mandatory.
        :return: True, if registered. False otherwise.
        """
        if self.find(props["name"]):
            # Person is found, Node set, do not create object.
            return False
        else:
            # Person not found, register participant.
            person_props = dict(
                name=props["name"]
            )
            self.person_node = ns.create_node(lbl_person, **person_props)
            # Link to MF
            link_mf(props["mf"], self.person_node, person2mf)
            return True

    def edit(self, **props):
        """
        This method will update an existing person node. A check is done to guarantee that the name is not duplicated
        to an existing name on another node. Modified properties will be updated and removed properties will be deleted.

        :param props: New set of properties (name, mf (boolean) for the node)
        :return: True - in case node is rewrite successfully.
        """
        # Name change?
        cn = self.get_name()
        if props["name"] != cn:
            if self.find(props["name"]):
                current_app.logger.error("Change name {cn} to new name {nn}, but this exists already!"
                                         .format(cn=cn, nn=props["name"]))
                return False
            else:
                self.set_name(props["name"])
        link_mf(props["mf"], self.person_node, person2mf)
        return True

    def get_name(self):
        return self.person_node["name"]

    def get_nid(self):
        return self.person_node["nid"]

    def get_dict(self):
        """
        This function will return a dictionary with the person attributes. This can then be used for display in a
        html macro

        :return: Dictionary with person attributes nid, label, active (True: Active user, cannot be removed,
        False: inactive user, can be removed).
        """
        person_dict = dict(
            nid=self.person_node["nid"],
            label=self.get_name(),
            active=self.active()
        )
        return person_dict

    def get_mf(self):
        """
        This method will get mf node.

        :return: mf node
        """
        return ns.get_endnode(start_node=self.person_node, rel_type=person2mf)

    def get_mf_value(self):
        """
        This method will get mf value to set race in web form.

        :return: mf value (man/vrouw)
        """
        return get_mf_value(node=self.person_node, rel=person2mf)

    def get_node(self, person_id=None):
        """
        This method returns the Person Node, or sets the person node if person_id is provided.

        :param person_id: NID of the person. Optional. If not specified, then the node will be returned. If set, then
        the person node is set.
        :return: Person node.
        """
        if person_id:
            self.person_node = ns.node(person_id)
        return self.person_node

    def active(self):
        """
        This method will check if a person is active. For now, this means that a person has 'participates' links.
        If the person is not active, then the person can be removed.

        :return: True if the person is active, False otherwise
        """
        end_node_list = ns.get_endnodes(start_node=self.person_node, rel_type=person2participant)
        if len(end_node_list) == 0:
            # Empty list, so person does not participate in any race.
            return False
        else:
            return True

    def get_races4person(self):
        """
        This method will get a list of participant information for a person, sorted on date. The information will be
        provided in a list of dictionaries. The dictionary values are the corresponding node dictionaries.

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
        """.format(pers_id=self.get_nid())
        cursor = ns.get_query(query)
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

    def remove(self):
        """
        Remove the person node if no longer active. The person object is no longer valid.

        :return:
        """
        if self.active():
            current_app.logger.warning("Cannot remove {name}, still active!".format(name=self.get_name()))
        else:
            ns.remove_node_force(self.get_nid())
        return

    def set_name(self, name):
        """
        This method will update a person name to a new name.

        :param name:
        :return:
        """
        cn = self.get_name()
        if self.find(name):
            current_app.logger.error("Change name {cn} to new name {nn}, but this exists already!"
                                     .format(cn=cn, nn=name))
            return False
        else:
            props = ns.node_props(self.person_node["nid"])
            props["name"] = name
            ns.node_update(**props)
            return True


class Organization:
    """
    This class instantiates to an organization.
    If an organization ID is provided, then the corresponding organization object is created. Otherwise an empty
    organization object is created.

    The organization object has the organization node as its property.

    :return: Object
    """
    def __init__(self, org_id=None):
        self.org_node = None
        if org_id:
            self.org_node = self.get_node(org_id)

    def add(self, **org_dict):
        """
        This method will add the organization to the calender. The organization graph object exists of organization name
        with link to date and city where it is organized.
        The organization instance attributes will be set.
        No checking is done on duplicate organization creations. These will be shown in the list and can be handled
        manually by the user.

        :param org_dict: New set of properties for the node. These properties are: name, location, datestamp and
         org_type. Datestamp needs to be of the form 'YYYY-MM-DD'. if org_type True then deelname otherwise Wedstrijd.
        :return: True if the organization has been registered, False if it existed already.
        """
        # Create the Organization node.
        self.org_node = ns.create_node("Organization", name=org_dict["name"])
        # Organization node known, now I can link it with the Location.
        self.set_location(org_dict["location"])
        # Set Date  for Organization
        self.set_date(org_dict["datestamp"])
        # Set Organization Type
        if org_dict['org_type']:
            self.set_type(def_deelname)
        else:
            self.set_type(def_wedstrijd)
        return True

    def edit(self, **properties):
        """
        This method will edit if the organization.
        Edit function needs to redirect relations, so it has begin and end nodes. This function can then remove single
        date nodes and location nodes if required. The Organization delete function will force to remove an organization
        node without a need to find the date and location first. Therefore the delete function requires a more generic
        date and location removal, where a check on all orphans is done.

        :param properties: Modified set of properties for the node. These properties are: name, location, datestamp and
         org_type. Datestamp must be of the form 'YYYY-MM-DD'
        :return: True if the organization has been updated, False if the organization (name, location, date) existed
         already. A change in Organization Type only is also a successful (True) change.
        """
        # Check Organization Type
        if properties['org_type']:
            org_type = def_deelname
        else:
            org_type = def_wedstrijd
        self.set_type(org_type=org_type)
        """
        if self.set_org_type(org_type):
            # Organization type changed, so re-calculate points for all races in the organization
            racelist = get_race_list(self.org_node["nid"])
            for rec in racelist:
                # Probably not efficient, but then you should't change organization type too often.
                points_for_race(rec["race_id"])
        """
        # Check Organization name.
        if properties['name'] != self.get_name():
            node_prop = ns.node_props(nid=self.get_org_id())
            node_prop["name"] = properties["name"]
            ns.node_update(**node_prop)
        # Check location
        curr_loc_node = self.get_location()
        if properties['location'] != curr_loc_node['city']:
            # Remember current location - before fiddling around with relations!
            # First create link to new location
            self.set_location(properties["location"])
            # Then remove link to current location
            ns.remove_relation(start_node=self.org_node, rel_type=organization2location, end_node=curr_loc_node)
            # Finally check if current location is still required. Remove if there are no more links.
            ns.remove_node(curr_loc_node)
        # Check Date
        self.set_date(ds=properties["datestamp"])
        return True

    def calculate_points(self):
        """
        Calculate points for every race in the organization.

        :return:
        """
        races = [item["race"] for item in get_race_list(self.get_org_id())]
        for race_node in races:
            race = Race(race_id=race_node["nid"])
            race.calculate_points()
        return

    def get_label(self):
        """
        This method will return the label of the Organization. (Organization name, city and date). Assumption is that
        the organization has been set already.

        :return: Label
        """
        org_name = self.org_node["name"]
        city = self.get_location()["city"]
        ds = self.get_date()
        ds_obj = my_env.datestr2date(ds["key"])
        label = "{org_name} ({city}, {date})".format(org_name=org_name, city=city, date=ds_obj.strftime("%d-%m-%Y"))
        return label

    def get_location(self):
        """
        This method will return the location for the Organization.

        :return: Location node.
        """
        loc_node = ns.get_endnode(self.org_node, organization2location)
        return loc_node

    def get_date(self):
        """
        This method will return the date node for the Organization.

        :return: Date node, or False if date not yet defined for the organization.
        """
        date_node = ns.get_endnode(start_node=self.org_node, rel_type=organization2date)
        # current_app.logger.debug("Date node: {dn}".format(dn=date_node))
        if isinstance(date_node, Node):
            return date_node
        else:
            return False

    def get_name(self):
        """
        This method will return the organization name as defined in the node.

        :return: Organization name.
        """
        return self.org_node["name"]

    def get_org_id(self):
        """
        This method will return the nid of the Organization node.

        :return: nid of the Organization node
        """
        return self.org_node["nid"]

    def get_node(self, org_id=None):
        """
        This method returns the Organization Node, or sets the organization node if org_id is provided.

        :param org_id: NID of the organization. Optional. If not specified, then the node will be returned. If set, then
        the organization node is set.
        :return: Organization node.
        """
        if org_id:
            self.org_node = ns.node(org_id)
        return self.org_node

    def get_participants(self):
        """
        This method will return all participants in this organization.

        :return: list of person nodes for persons that do participate in a race for this organization.
        """
        query = """
            MATCH (n:Organization)-[:has]->(m:Race)<-[:participates]-(d:Participant)<-[:is]-(p:Person)
            WHERE n.nid = '{org_id}'
            RETURN p
        """.format(org_id=self.get_org_id())
        return ns.get_query(query)

    def get_race_main(self):
        """
        This method will return main race node, or False if no main race defined for this organization.

        :return: Race node for 'Hoofdwedstrijd' or False if no Hoofdwedstrijd defined for Organization.
        """
        if self.get_type() == def_deelname:
            return False
        else:
            query = """
                    MATCH (org:{lbl_org})-[:{org2race}]->(race:{lbl_race})-[:{race2type}]->(rt:{lbl_rt})
                    WHERE org.nid='{nid}'
                      AND rt.name='{def_hoofd}'
                    RETURN race
                    """.format(nid=self.org_node["nid"],
                               lbl_org=lbl_organization, lbl_race=lbl_race, lbl_rt=lbl_raceType,
                               org2race=organization2race, race2type=race2type,
                               def_hoofd=def_hoofdwedstrijd)
            current_app.logger.debug(query)
            res = ns.get_query_data(query)
            if len(res) > 0:
                return res[0]["race"]
            else:
                return False

    def get_type(self):
        """
        This method will return the organization type(Wedstrijd or Deelname).

        :return: Organization Type. Wedstrijd (Default) or Deelname, or False if not set.
        """
        org_type = ns.get_endnode(self.org_node, organization2type)
        if isinstance(org_type, Node):
            return org_type["name"]
        else:
            # org_type not yet defined for organization.
            return False

    def set_date(self, ds=None):
        """
        This method will create a relation between the organization and the date. Relation type is 'On'.
        Organization Node must be available for this method.

        :param ds: Datestamp in datetime.date format
        :return:
        """
        curr_ds_node = self.get_date()
        if curr_ds_node:
            # Convert date string to datetime date object.
            # Then compare date objects to avoid formatting issues.
            curr_ds = datetime.datetime.strptime(curr_ds_node["key"], "%Y-%m-%d").date()
            if ds != curr_ds:
                current_app.logger.debug("Trying to set date from {curr_ds} to {ds}".format(curr_ds=curr_ds, ds=ds))
                # Remove current link from organization to date
                ns.remove_relation(start_node=self.org_node, end_node=curr_ds_node, rel_type=organization2date)
                # Check if date (day, month, year) can be removed.
                # Don't remove single date, clear all dates that can be removed. This avoids the handling of key
                # because date nodes don't have a nid.
                ns.remove_orphan_nodes(lbl_day)
            else:
                # Link organization to date exists and no need to change
                return True
        # Create new (or updated) link from organization to date
        date_node = ns.date_node(ds)  # Get Date (day) node
        ns.create_relation(from_node=self.org_node, rel=organization2date, to_node=date_node)
        return

    def set_location(self, loc=None):
        """
        This method will create a relation between the organization and the location. Relation type is 'In'.
        Organization Node must be available for this method.

        :param loc: city name of the location.
        :return: Nothing - relation between organization and location is established.
        """
        loc_node = Location(loc).get_node()   # Get Location Node based on city
        ns.create_relation(from_node=self.org_node, to_node=loc_node, rel=organization2location)
        return

    def set_type(self, org_type):
        """
        This method will set or update the Organization Type. In case of update Organization Type, then the current link
        needs to be removed and the new link is set.
        Method set_race_type is called after setting the org type, to guarantee that the race links are OK.

        :param org_type: 'Wedstrijd' or 'Deelname"
        :return: True if org_type is set (or changed), False if org_type is not changed.
        """
        # Todo: Add link to recalculate points in the races (this link is in org edit!)
        if self.get_type():
            if self.get_type == org_type:
                # All set, return
                return False
            else:
                # Org Type needs to change, remove here.
                org_type_node = ns.get_endnode(start_node=self.org_node, rel_type=organization2type)
                ns.remove_relation(start_node=self.org_node, rel_type=organization2type, end_node=org_type_node)
        # Set the organization type
        org_type_node = get_org_type_node(org_type)
        ns.create_relation(from_node=self.org_node, rel=organization2type, to_node=org_type_node)
        self.set_race_type()
        self.calculate_points()
        return True

    def set_race_type(self, race_nid=None, race_type=None):
        """
        This method sets the race type for a specific race or for all races in the organization.
        If Organization is Deelname, then all (race)-[:type]->(raceType) links will be removed.

        If Organization is Wedstrijd, then this method will ensure there is maximum one Hoofdwedstrijd.
        Options:
        1. Organization type changes from Deelname to Wedstrijd (race_nid is None) => set all races to 'Nevenwedstrijd'
        2. Race changes from Hoofdwedstrijd to Nevenwedstrijd => remove relation to Hoofdwedstrijd, set relation to
        Nevenwedstrijd.
        3. Race changes from Nevenwedstrijd to Hoofdwedstrijd. If there was Hoofdwedstrijd, then apply -2- first. Set
        current race to Hoofdwedstrijd.

        Recalculate points for this organization.

        :param race_nid: NID for which race type needs to be set.
        :param race_type: Type for the race.
        :return:
        """
        if self.get_type() == def_deelname:
            # Make sure there are no race->raceType links
            query = """
            MATCH (org:{lbl_org})-[:{org2race}]->(race:{lbl_race})-[:{race2type}]->(rt:{lbl_rt})
            RETURN race, rt
            """.format(lbl_org=lbl_organization, lbl_race=lbl_race, lbl_rt=lbl_raceType,
                       org2race=organization2race, race2type=race2type)
            res = ns.get_query_data(query)
            for rec in res:
                ns.remove_relation(start_node=rec["race"], end_node=rec["rt"], rel_type=race2type)
        else:
            # Organization type is Wedstrijd
            if isinstance(race_nid, str):
                # Remove current relation - then set new relation
                current_type = ns.get_endnode(start_node=ns.node(race_nid), rel_type=race2type)
                if isinstance(current_type, Node):
                    ns.remove_relation(start_node=ns.node(race_nid), rel_type=race2type, end_node=current_type)
                if race_type == def_hoofdwedstrijd:
                    # If another hoofdwedstrijd was defined, set other race to nevenwedstrijd
                    main_race = self.get_race_main()
                    if isinstance(main_race, Node):
                        self.set_race_type(race_nid=main_race["nid"], race_type=def_nevenwedstrijd)
                    # No hoofdwedstrijd OR hoofdwedstrijd already set to current race
                    props = dict(name=def_hoofdwedstrijd)
                    hoofd_node = ns.get_node(lbl_raceType, **props)
                    ns.create_relation(from_node=ns.node(race_nid), rel=race2type, to_node=hoofd_node)
                else:
                    props = dict(name=def_nevenwedstrijd)
                    neven_node = ns.get_node(lbl_raceType, **props)
                    ns.create_relation(from_node=ns.node(race_nid), rel=race2type, to_node=neven_node)
            else:
                # Set all race_types to Nevenwedstrijd - make sure there is no Hoofdwedstrijd defined
                main_race = self.get_race_main()
                if isinstance(main_race, Node):
                    self.set_race_type(race_nid=main_race["nid"], race_type=def_deelname)
                # For all races merge with Nevenwedstrijd racetype.
                races = ns.get_endnodes(start_node=self.org_node, rel_type=organization2race)
                props = dict(name=def_nevenwedstrijd)
                neven_node = ns.get_node(lbl_raceType, **props)
                for race in races:
                    ns.create_relation(from_node=race, rel=race2type, to_node=neven_node)
        return


class Race:
    """
    This class instantiates a race. This can be done as a new race that links to an organization, in which case
    org_id needs to be specified, or it can be done as a race node ID (in which case org_id should be none).

    The object has the race node and the organization object. Methods include creating and maintaining the race graph,
    consisting of links to organization and type (if organization is wedstrijd). For organization is Deelname, Race
    does not have link to type.
    """

    def __init__(self, org_id=None, race_id=None):
        """
        Define the Race object.

        :param org_id: Node ID of the Organization, used to create a new race.
        :param race_id: Node ID of the Race, to handle an existing race. Organization will be calculated from race.
        """
        self.org = None
        self.race_node = None
        if org_id:
            self.org = Organization(org_id=org_id)
        elif race_id:
            self.race_node = ns.node(nid=race_id)
            self.set_org()

    def add(self, **props):
        """
        This method will add the race to this organization. This is done by creating a race graph object, consisting of
        a race node and a link to the organization. If the organization is Wedstrijd, then race link to Hoofdwedstrijd
        or Nevenwedstrijd is also required.
        Note that check on duplicate races is not done. If a duplicate race is defined, then the user will see it in the
        list and can remove it again.

        :param props: Dictionary with race properties, including name (mandatory) and type (of Organization Wedstrijd).
        :return: racename
        """
        # Create Race Node with attribute name and label
        race_props = dict(name=props["name"])
        self.race_node = ns.create_node(lbl_race, **race_props)
        # Add Race Node to Organization
        ns.create_relation(from_node=self.org.get_node(), rel=organization2race, to_node=self.race_node)
        # If organization is Wedstrijd, then set race type
        if self.org.get_type() == def_wedstrijd:
            self.org.set_race_type(race_nid=self.get_nid(), race_type=props["type"])
            self.org.calculate_points()
        return self.race_node["name"]

    def edit(self, **props):
        """
        This method will update the race. Changes can be made to the name or (for Wedstrijd Organizations) to the race
        type.

        :param props: Dictionary with race properties name and optionally type.
        :return: racename
        """
        # Check if name needs to be updated
        if props["name"] != self.get_name():
            race_props = dict(
                nid=self.race_node["nid"],
                name=props["name"]
            )
            self.race_node = ns.node_update(**race_props)
        # Check if type needs to be updated if organization type is Wedstrijd. In case of Deelname, then racetype has
        # been removed already.
        if self.org.get_type() == def_wedstrijd:
            if props["type"] != self.get_racetype():
                # Change in race type - handled by organization object.
                self.org.set_race_type(race_nid=self.get_nid(), race_type=props["type"])
                self.org.calculate_points()
        return self.race_node["name"]

    def calculate_points(self):
        """
        This method will calculate the points for the race. Races can be of 3 different types: Wedstrijd, Nevenwedstrijd
        or deelname.

        :return: All participants in the race have the correct points and position.
        """
        race_type = self.get_racetype()
        node_list = self.get_participant_seq_list()
        main_race_node = self.org.get_race_main()
        if isinstance(main_race_node, Node):
            main_race = Race(race_id=main_race_node["nid"])
            main_race_parts = len(main_race.get_participant_seq_list())
        else:
            main_race_parts = 0
        if isinstance(node_list, list):
            cnt = 0
            for part in node_list:
                if race_type == def_hoofdwedstrijd:
                    points = points_race(cnt)
                elif race_type == def_nevenwedstrijd:
                    points = points_race(main_race_parts)
                elif race_type == def_deelname:
                    points = points_deelname
                else:
                    current_app.logger.error("Race Type {rt} not defined.".format(rt=race_type))
                    points = 20
                cnt += 1
                rel_pos = cnt
                # Set points for participant - Participant node is identified on nid.
                props = dict(nid=part["nid"], points=points, rel_pos=rel_pos)
                ns.node_set_attribs(**props)
        return

    def get_next_part(self):
        """
        This method will get the list of people that can be added as participant to the race. So these are people not
        listed as participant yet.

        :return: list of possible next participants
        """
        query = """
          MATCH (person:{lbl_person}), (org:{lbl_org} {{nid: '{org_nid}'}})
          WHERE NOT EXISTS ((person)-[:{person2part}]->(:{lbl_part})-[:{part2race}]->(:{lbl_race})<-[:{org2race}]-(org))
          RETURN person 
          ORDER BY person.name
        """.format(lbl_person=lbl_person, lbl_part=lbl_participant, lbl_race=lbl_race, lbl_org=lbl_organization,
                   person2part=person2participant, part2race=participant2race, org2race=organization2race,
                   org_nid=self.get_org_id())
        current_app.logger.debug(query)
        res = ns.get_query_data(query)
        return res

    def get_label(self):
        """
        This method will get the display name for the race and organization.

        :return: Race name and organization, for race 'stand-alone' usage.
        """
        org_name = self.org.get_name()
        return "{race_name} ({org_name})".format(race_name=self.get_racename(), org_name=org_name)

    def get_mf_value(self):
        """
        This method will get mf value to set race in web form.

        :return: mf value (man/vrouw)
        """
        return get_mf_value(node=self.race_node, rel=race2mf)

    def get_name(self):
        """
        This method will return the Name attribute from the race node.

        :return: Name attribute of race node, or None if name not available
        """
        return self.race_node["name"]

    def get_nid(self):
        """
        This method will return the NID or the race_node

        :return: NID of the race_node
        """
        return self.race_node["nid"]

    def get_node(self):
        """
        This method will return the race_node

        :return: race_node
        """
        return self.race_node

    def get_org_id(self):
        """
        This method returns the org_id for a race object.

        :return: org_id
        """
        return self.org.get_org_id()

    def get_participant_seq_list(self, excl_part_nid=None):
        """
        This method returns the participants for the race in sequence of arrival.

        :param excl_part_nid: Participant nid that needs to be excluded from query, since it is in orpan state.
        :return: List of participant nodes for the race in sequence of arrival.
        """
        # Todo: Review update in the cypher query.
        """
        MATCH race_ptn = (race)<-[:participates]-(first_part),
              participants = (first_part)<-[:after*0..]-(last_part)
        WHERE race.nid = '5ac5b0f1-8ca2-4da2-9516-0a047f00f1b7'
          AND NOT ()<-[:after]-(first_part)
          AND NOT (last_part)-[:after]->()
        RETURN nodes(participants)
        """

        if isinstance(excl_part_nid, str):
            excl_str = "AND NOT participant.nid = '{part_nid}'".format(part_nid=excl_part_nid)
        else:
            excl_str = ""
        query = """
            MATCH race_ptn = (race)<-[:participates]-(participant),
                  participants = (participant)<-[:after*0..]-()
            WHERE race.nid = '{race_id}' {excl_str}
            WITH COLLECT(participants) AS results, MAX(length(participants)) AS maxLength
            WITH FILTER(result IN results WHERE length(result) = maxLength) AS result_coll
            UNWIND result_coll as result
            RETURN nodes(result)
        """.format(race_id=self.get_nid(), excl_str=excl_str)
        current_app.logger.info(query)
        # Get the result of the query in a recordlist
        res = ns.get_query_data(query)
        if len(res) > 0:
            return res[0]["nodes(result)"]
        else:
            return []

    def get_racename(self):
        """
        This method get the display name of the race.

        :return: Display name (racename) for the race.
        """
        return self.race_node["name"]

    def get_racetype(self):
        """
        This method will return the race type (Wedstrijd, Nevenwedstrijd). If no racetype is defined, then organization
        type must be 'Deelname', for which no specific racetype is required.

        :return: Race Type: Wedstrijd, Nevenwedstrijd or False if not available.
        """
        race_type = ns.get_endnode(self.get_node(), race2type)
        if isinstance(race_type, Node):
            return race_type["name"]
        else:
            # race_type not defined for race, so it must be 'Deelname'.
            return False

    def part_person_seq_list(self, excl_part_nid=None):
        """
        This method add person information to the participant sequence list.

        :param excl_part_nid: Participant nid that needs to be excluded from query, since it is in orpan state.
        :return: List of participant items in the race. Each item is a tuple of the person dictionary (from the person
        object) and the participant dictionary (the properties of the participant node). False if there are no
        participants in the list.
        """
        node_list = self.get_participant_seq_list(excl_part_nid)
        if isinstance(node_list, list):
            finisher_list = []
            # If there are finishers, then recordlist has one element, which is a nodelist
            for part in node_list:
                part_obj = Participant(part_id=part["nid"])
                person_obj = Person(person_id=part_obj.get_person_nid())
                person_dict = person_obj.get_dict()
                pers_part_tuple = (person_dict, dict(part))
                finisher_list.append(pers_part_tuple)
            return finisher_list
        else:
            return False

    def part_person_after_list(self):
        """
        This method will return the participant sequence list as a SelectField list. It will call part_person_seq_list
        and 'prepend' a value for 'eerste aankomer' (value -1).

        :return: List of the Person objects (list of Person nid and Person name) in sequence of arrival and value for
        'eerste aankomer'.
        """
        eerste = [-1, 'Eerste aankomst']
        finisher_tuple = self.part_person_seq_list()
        if finisher_tuple:
            finisher_list = [[person['nid'], person['label']] for (person, part) in finisher_tuple]
            finisher_list.insert(0, eerste)
        else:
            finisher_list = [eerste]
        return finisher_list

    def part_person_first_id(self, excl_part_nid=None):
        """
        This method will get the ID of the first person in the race.

        :param excl_part_nid: Participant nid that needs to be excluded from query, since it is in orpan state.
        :return: Node ID of the first person so far in the race, False if no participant registered for this race.
        """
        finisher_tuple = self.part_person_seq_list(excl_part_nid)
        if finisher_tuple:
            (person, part) = finisher_tuple[0]
            person_id = person['nid']
            return person_id
        else:
            return False

    def part_person_last_id(self):
        """
        This method will return the nid of the last person in the race. It calls part_person_after_list and fetches
        the ID of the last runner. This way no special treatment is required in case there are no participants. The ID
        of the last runner will redirect to -1 then.

        :return: nid of the Person Node of the last finisher so far in the race, -1 if no finishers registered yet.
        """
        finisher_list = self.part_person_after_list()
        part_arr = finisher_list.pop()
        part_last = part_arr[0]
        return part_last

    def set_org(self):
        """
        This method will set the organization object for the race.

        :return: (nothing, organization object will be set.)
        """
        org_node = ns.get_startnode(end_node=self.race_node, rel_type=organization2race)
        self.org = Organization(org_id=org_node["nid"])
        return


class Location:

    def __init__(self, loc):
        """
        The class will initialize the location object based on city name.

        :param loc: city name for the Location.
        """
        self.loc = loc

    def find(self):
        """
        Find the location node

        :return:
        """
        props = {
            "city": self.loc
        }
        loc = ns.get_node("Location", **props)
        return loc

    def add(self):
        if not self.find():
            ns.create_node("Location", city=self.loc)
            return True
        else:
            return False

    def get_node(self):
        """
        This method will get the node that is associated with the location. If the node does not exist already, it will
        be created.

        :return:
        """
        self.add()    # Register if required, ignore else
        node = self.find()
        return node


def organization_list():
    """
    This function will return a list of organizations. Each item in the list is a dictionary with fields date,
    organization, city, id (for organization nid) and type.

    :return: List of dictionaries containing fields date, organization, city, id (organization nid) and type.
    """
    query = """
        MATCH (day:Day)<-[:On]-(org:Organization)-[:In]->(loc:Location),
              (org)-[:type]->(ot:OrgType)
        RETURN day.key as date, org.name as organization, loc.city as city, org.nid as id, ot.name as type
        ORDER BY day.key ASC
    """
    res = ns.get_query_data(query)
    # Convert date key from YYYY-MM-DD to DD-MM-YYYY
    for rec in res:
        rec["date"] = datetime.datetime.strptime(rec["date"], "%Y-%m-%d").strftime("%d-%m-%Y")
    return res


def organization_delete(org_id=None):
    """
    This method will delete an organization. This can be done only if there are no more races attached to the
    organization. If an organization is removed, then check is done for orphan date and orphan location. If available,
    these will also be removed.

    :param org_id:
    :return:
    """
    org = Organization(org_id=org_id)
    org_node = org.get_node()
    org_label = org.get_label()
    if ns.get_endnodes(start_node=org_node, rel_type="has"):
        current_app.logger.info("Organization {label} cannot be removed, races are attached.".format(label=org_label))
        return False
    else:
        # Remove Organization
        current_app.logger.debug("Trying to remove organization {lbl}".format(lbl=org_label))
        ns.remove_node_force(nid=org_id)
        # Check if this results in orphan dates, remove these dates
        current_app.logger.debug("Then remove all orphan dates")
        ns.remove_orphan_nodes(lbl_day)
        # Check if this results in orphan locations, remove these locations.
        current_app.logger.debug("Trying to delete orphan organizations.")
        ns.remove_orphan_nodes(lbl_location)
        current_app.logger.debug("All done")
        current_app.logger.info("Organization {lbl} removed.".format(lbl=org_label))
        return True


def get_org_id(race_id):
    """
    This method will return the organization ID for a Race ID: Organization has Race.

    :param race_id: Node ID of the race.
    :return: Node ID of the organization.
    """
    race_node = ns.node(race_id)
    org_id = ns.get_startnode(end_node=race_node, rel_type="has")
    return org_id


def get_org_type_node(org_type):
    """
    This method will find the Organization Type Node.

    :param org_type: "Deelname" or "Wedstrijd".
    :return: Organization Type Node, "Wedstrijd" or "Deelname".
    """
    props = {
        "name": org_type
    }
    return ns.get_node("OrgType", **props)


def get_race_list_attribs(org_id):
    """
    This method will collect the params required for the Race List macro.

    :param org_id: Node ID of the organization.
    :return: Parameters for the Race List macro: org_id, org_label, org_type, races (list of (race, type) dictionaries)
    and remove_org flag.
    """
    org = Organization(org_id=org_id)
    # org.set(org_id)
    races = get_race_list(org_id)
    if len(races) > 0:
        remove_org = "No"
    else:
        remove_org = "Yes"
    params = dict(
        org_id=org_id,
        org_label=org.get_label(),
        org_type=org.get_type(),
        races=races,
        remove_org=remove_org
    )
    return params


def init_graph():
    """
    This method will initialize the graph. It will set indices and create nodes required for the application
    (on condition that the nodes do not exist already).

    :return:
    """
    stmt = "CREATE CONSTRAINT ON (n:{0}) ASSERT n.{1} IS UNIQUE"
    ns.get_query(stmt.format(lbl_location, 'city'))
    ns.get_query(stmt.format(lbl_person, 'name'))
    ns.get_query(stmt.format(lbl_raceType, 'name'))
    ns.get_query(stmt.format(lbl_organizationType, 'name'))
    nid_labels = [lbl_day, lbl_location, lbl_mf, lbl_organization, lbl_organization, lbl_participant, lbl_person,
                  lbl_race, lbl_raceType]
    stmt = "CREATE CONSTRAINT ON (n:{nid_label}) ASSERT n.nid IS UNIQUE"
    for nid_label in nid_labels:
        ns.get_query(stmt.format(nid_label=nid_label))
    # Organization type nodes and Race type nodes are required for empty database
    # Organization
    for name in [def_wedstrijd, def_deelname]:
        props = dict(name=name)
        if not ns.get_node(lbl_organizationType, **props):
            ns.create_node(lbl_organizationType, **props)
    # Race
    for name in [def_hoofdwedstrijd, def_nevenwedstrijd]:
        props = dict(name=name)
        if not ns.get_node(lbl_raceType, **props):
            ns.create_node(lbl_raceType, **props)
    # mf
    for name in ["Dames", "Heren"]:
        props = dict(name=name)
        if not ns.get_node(lbl_mf, **props):
            ns.create_node(lbl_mf, **props)
    return


def link_mf(mf, node, rel):
    """
    This method will link the node to current mf. If Link does not exist, it will be created. If link is to other
    node, the link will be removed and attached to required mf node.

    :param mf: mf attribute from web form (man/vrouw)
    :param node: Start node for the relation (Person or Race)
    :param rel: relation
    :return:
    """
    current_app.logger.info("mf: {mf}, rel: {rel}".format(mf=mf, rel=rel))
    # Translate web property to node name
    mf_name = mf_tx[mf]
    # Review MF link - update if different from current setting
    current_mf = ns.get_endnode(start_node=node, rel_type=rel)
    if isinstance(current_mf, Node):
        if current_mf["name"] != mf_name:
            # Remove link to current node
            ns.remove_relation(start_node=node, end_node=current_mf, rel_type=rel)
        else:
            current_app.logger.info("No changes required...")
            # Link from race to mf exist, all OK!
            return
    # Create link between race node and MF.
    mf_node = get_mf_node(mf_name)
    current_app.logger.info("Creating connection to node {mf}".format(mf=mf_node))
    ns.create_relation(from_node=node, rel=rel, to_node=mf_node)
    return


def get_race_list(org_id):
    """
    This function will get an organization nid and return the Races associated with the Organization.
    The races will be returned as a list of dictionaries with fields race node and raceType node.

    :param org_id: nid of the Organization.
    :return: List of dictionaries with race node and raceType node sorted on raceType then raceName, or empty list which
    evaluates to False.
    """
    query = """
        MATCH (org:{lbl_org})-[:{org2race}]->(race:{lbl_race})
        WHERE org.nid = '{org_id}'
        OPTIONAL MATCH (race)-[:{race2type}]->(type:{lbl_rt})
        RETURN race, type
        ORDER BY type.name, race.name
    """.format(org_id=org_id,
               lbl_org=lbl_organization, lbl_race=lbl_race, lbl_rt=lbl_raceType,
               org2race=organization2race, race2type=race2type)
    current_app.logger.debug(query)
    res = ns.get_query_data(query)
    return res


def races4person(pers_id):
    """
    This method is pass-through for a method in neostore module.
    This method will get a list of race_ids per person, sorted on date. The information per race will be provided in
    a list of dictionaries. This includes date, organization, type of race, and race results.

    :param pers_id:
    :return: list of Participant (part),race, date, organization (org) and racetype Node dictionaries in date
    sequence.
    """
    person = Person(person_id=pers_id)
    recordlist = person.get_races4person()
    return recordlist


def races4person_org(pers_id):
    """
    This method gets the result of races4person method, then converts the result in a dictionary with key org_nid and
    value race dictionary.

    :param pers_id:
    :return: Dictionary with key org_nid and value dictionary of node race attributes for the person. This can be used
    for the Results Overview page.
    """
    races = races4person(pers_id=pers_id)
    race_org = {}
    for race in races:
        race_org[race["org"]["nid"]] = dict(
            race=race["race"],
            part=race["part"]
        )
    return race_org


def race_delete(race_id=None):
    """
    This method will delete a race. This can be done only if there are no more participants attached to the
    race.

    :param race_id: Node ID of the race to be removed.
    :return: True if race is removed, False otherwise.
    """
    race = Race(race_id=race_id)
    rl = race.get_label()
    if ns.get_startnodes(end_node=race.get_node(), rel_type="participates"):
        msg = "Race {rl} cannot be removed, participants are attached.".format(rl=rl)
        current_app.logger.error(msg)
        return False
    else:
        # Remove Organization
        ns.remove_node_force(race_id)
        msg = "Race {rl} removed.".format(rl=rl)
        current_app.logger.info(msg)
        return True


def person_list():
    """
    Return the list of persons as person objects.

    :return: List of persons objects. Each person is represented as a dictionary with person nid, name, category,
    category sequence (cat_seq), mf and number of races (races). The list is sorted on Category, MF and name.
    """
    res = ns.get_nodes(lbl_person)
    person_arr = []
    if isinstance(res, list):
        for node in res:
            person_obj = Person(person_id=node["nid"])
            person_dict = dict(
                nid=person_obj.get_node()["nid"],
                name=person_obj.get_name(),
                mf=person_obj.get_mf()["name"],
                races=len(person_obj.get_races4person())
            )
            person_arr.append(person_dict)
        persons_sorted = sorted(person_arr, key=lambda x: (x["mf"], x["name"]))
    else:
        persons_sorted = []
    return persons_sorted


def get_location(nid):
    """
    This method will get a location nid and return the city name. This is because the Location class requires city name
    as creator attribute.

    :param nid: nid of the location node, returned by a selection field.
    :return: city name of the location node, or False if no location found.
    """
    loc = ns.get_node(lbl_location, nid=nid)
    if loc:
        return loc["city"]
    else:
        current_app.logger.fatal("Location expected but not found for nid {nid}".format(nid=nid))
        return False


def get_location_list():
    """
    This method will return the location list in sequence. Location items are returned in list of tuples
    with nid and city name

    :return: List of tuples containing nid and city sorted by City name.
    """
    query = "MATCH (n:{lbl}) RETURN n ORDER BY n.city".format(lbl=lbl_location)
    return [(loc["n"]["nid"], loc["n"]["city"]) for loc in ns.get_query_data(query)]


def get_mf_node(prop):
    """
    This method will return the node that corresponds with the selected man/vrouw value.

    :param prop: Heren / Dames
    :return: Corresponding node
    """
    props = dict(name=prop)
    return ns.get_node(lbl_mf, **props)


def get_mf_value(node, rel):
    """
    This method will get mf value to set race in web form. The MF Node is on the end of a relation (person or race.)

    :param node: Start Node for the relation (person or race)
    :param rel: Relation type (person2mf or race2mf)
    :return: mf value (man/vrouw)
    """
    mf_node = ns.get_endnode(start_node=node, rel_type=rel)
    mf = mf_node["name"]
    return mf_tx_inv[mf]


def points_race(pos):
    """
    This method will return points for a specific position in a regular race.
    Points are in sequence of arrival: 50 - 45 - 40 - 35 - 34 - 33 - 32 - ... - 15

    :param pos: Position in the race
    :return: Points associated for this position. Minimum is 15 points.
    """
    racepoints = [50, 45, 40, 35]
    try:
        points = racepoints[pos]
    except IndexError:
        points = racepoints[-1] - ((pos+1) - len(racepoints))
    if points < 15:
        points = 15
    return points


def points_sum(point_list):
    """
    This function will calculate the total of the points for this participant. For now, the sum of all points is
    calculated.

    :param point_list: list of the points for the participant.
    :return: sum of the points
    """
    # Todo: points for 'deelname' should be calculated separately and in full
    nr_races = 6
    add_points_per_race = 5
    max_list = sorted(point_list)[-nr_races:]
    if len(point_list) > nr_races:
        add_points = (len(point_list) - nr_races) * add_points_per_race
    else:
        add_points = 0
    points = sum(max_list) + add_points
    return points


def results_for_mf(mf):
    """
    This method will calculate the points for all participants in mf. Split up in points for wedstrijd and points for
    deelname at this point.

    :param mf: Dames / Heren
    :return: Sorted list with tuples (name, points, number of races, nid for person).
    """
    # Wedstrijden
    res_wedstrijd = participation_points(mf=mf, orgtype=def_wedstrijd)
    result_list = {}
    for df_line in res_wedstrijd.iterrows():
        rec = df_line[1].to_dict()
        try:
            result_list[rec["person_nid"]].append(rec["points"])
        except KeyError:
            result_list[rec["person_nid"]] = [rec["points"]]
    # Then collect totals for every participant
    wedstrijd_total = {}
    for nid in result_list:
        params = dict(
            wedstrijd_nr=len(result_list[nid]),
            wedstrijd_points=points_sum(result_list[nid])
        )
        wedstrijd_total[nid] = params
    # Deelname
    res_deelname = participation_points(mf=mf, orgtype=def_deelname)
    result_list = {}
    for df_line in res_deelname.iterrows():
        rec = df_line[1].to_dict()
        try:
            result_list[rec["person_nid"]].append(rec["points"])
        except KeyError:
            result_list[rec["person_nid"]] = [rec["points"]]
    # Then collect totals for every participant
    deelname_total = {}
    for nid in result_list:
        params = dict(
            deelname_nr=len(result_list[nid]),
            deelname_points=len(result_list[nid] * points_per_deelname)
        )
        deelname_total[nid] = params
    # Merge wedstrijd_total and deelname_total
    for nid in wedstrijd_total:
        try:
            wedstrijd_total[nid]["deelname_nr"] = deelname_total[nid]["deelname_nr"]
            wedstrijd_total[nid]["deelname_points"] = deelname_total[nid]["deelname_points"]
        except KeyError:
            wedstrijd_total[nid]["deelname_nr"] = 0
            wedstrijd_total[nid]["deelname_points"] = 0
    # Now add participants in deelname_total and not in wedstrijd_total
    deelname_only = [nid for nid in deelname_total if nid not in wedstrijd_total]
    for nid in deelname_only:
        wedstrijd_total[nid] = {}
        wedstrijd_total[nid]["wedstrijd_nr"] = 0
        wedstrijd_total[nid]["wedstrijd_points"] = 0
        wedstrijd_total[nid]["deelname_nr"] = deelname_total[nid]["deelname_nr"]
        wedstrijd_total[nid]["deelname_points"] = deelname_total[nid]["deelname_points"]
    # Now calculate totals
    for nid in wedstrijd_total:
        wedstrijd_total[nid]["nr"] = wedstrijd_total[nid]["wedstrijd_nr"] + wedstrijd_total[nid]["deelname_nr"]
        wedstrijd_total[nid]["points"] = wedstrijd_total[nid]["wedstrijd_points"] + \
            wedstrijd_total[nid]["deelname_points"]
    # Then convert dictionary in sorted list
    result_total = []
    for nid in wedstrijd_total:
        person = Person(nid)
        result_total.append([person.get_name(), wedstrijd_total[nid]["points"], wedstrijd_total[nid]["nr"], nid])
    result_sorted = sorted(result_total, key=lambda x: (x[5], -x[1]))
    return result_sorted


def participation_points(mf, orgtype):
    """
    This method returns all participation points for every person for the specified mf and orgtype (Wedstrijd or
    Deelname).

    :param mf: Dames / Heren
    :param orgtype: Wedstrijd / Deelname
    :return: A dataframe with records having the person_nid and points for each participation for mf and orgtype and for
    every race.
    """
    query = """
        MATCH (person:Person)-[:mf]->(mf:MF  {name: {mf}}),
              (person)-[:is]->(part)-[:participates]-(race:Race),
              (race)<-[:has]-(org:Organization),
              (org)-[:type]->(orgtype:OrgType {name: {orgtype}})
        RETURN person.nid as person_nid, part.points as points
    """
    res = ns.get_query_df(query, mf=mf, orgtype=orgtype)
    return res


def remove_node_force(node_id):
    """
    This function will remove the node with node ID node_id, including relations with the node.

    :param node_id:
    :return: True if node is deleted, False otherwise
    """
    return ns.remove_node_force(node_id)
