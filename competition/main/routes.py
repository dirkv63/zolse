# import competition.models_graph as mg
# import logging
# import datetime
from competition.lib import my_env
from competition import models_graph as mg
# from lib import neostore
from flask import render_template, flash, current_app, redirect, url_for, request
from flask_login import login_required, login_user, logout_user
from .forms import *
from . import main
# from ..models_sql import User

# The participant properties that can be set (not calculated)
"""
**Time** is currently not part of the participant properties. It is not part of wtforms 2, wtforms 3 is not yet
released for pip and it may not be required at all: the data may not always be available, and a hassle to add the data.
"""
# part_config_props = ["pos", "remark"]
part_config_props = ["pos"]


@main.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        # Create an empty user object
        user = mg.User()
        if not user.validate_password(name=form.username.data, pwd=form.password.data):
            flash('Login not successful', "error")
            return redirect(url_for('main.login', **request.args))
        login_user(user, remember=form.remember_me.data)
        return redirect(request.args.get('next') or url_for('main.index'))
    return render_template('login.html', form=form)


@main.route('/')
def index():
    # return render_template('index.html')
    return redirect(url_for('main.organization_list'))


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main.route('/location/add', methods=['GET', 'POST'])
@login_required
def location_add():
    ref = False
    form = LocationAdd()
    if request.method == "GET":
        form.ref.data = request.referrer
        return render_template('login.html', form=form)
    else:
        if form.validate_on_submit():
            loc = form.location.data
            ref = form.ref.data
            if mg.Location(loc).add():
                flash("{l} toegevoegd als locatie".format(l=loc), "success")
            else:
                flash("{l} bestaaat reeds".format(l=loc), "warning")
        else:
            flash("Form did not validate on submit, how did this happen?", "error")
        return redirect(ref or url_for('main.index'))


@main.route('/person/add', methods=['GET', 'POST'])
@login_required
def person_add(person_id=None):
    if request.method == "GET":
        if person_id:
            person = mg.Person(person_id=person_id)
            mf = person.get_mf_value()
            if person.get_category():
                cat_nid = person.get_category()["nid"]
                form = PersonAdd(mf=mf, category=cat_nid)
            else:
                form = PersonAdd(mf=mf)
            form.name.data = person.get_name()
        else:
            form = PersonAdd()
        form.category.choices = mg.get_category_list()
        persons = mg.person_list()
        return render_template('person_add.html', form=form, persons=persons)
    else:
        # request.method == "POST":
        form = PersonAdd()
        # if form.validate_on_submit(): Doesn't work with SelectField
        person_dict = dict(
            name=form.name.data,
            mf=form.mf.data,
            category=form.category.data
        )
        if person_id:
            # This is from person edit function
            # current_app.logger.debug("Person Dictionary: {person_dict}".format(person_dict=person_dict))
            person = mg.Person(person_id=person_id)
            person.edit(**person_dict)
        else:
            person = mg.Person()
            person.add(**person_dict)
        return redirect(url_for('main.person_add'))


@main.route('/person/edit/<pers_id>', methods=['GET', 'POST'])
@login_required
def person_edit(pers_id):
    """
    This method will edit the person's information.
    :param pers_id:
    :return:
    """
    # Flask insists on getting a response back. Omitting 'return' in line below is an implicit 'Return None' and Flask
    # doesn't like this.
    return person_add(person_id=pers_id)


@main.route('/person/list')
def person_list():
    persons = mg.person_list()
    for person in persons:
        current_app.logger.info(person)
    return render_template('person_list.html', persons=persons)


@main.route('/person/<pers_id>')
def person_summary(pers_id):
    """
    This method provides all information about a single person. In case this is an 'isolated' person
    (this means without link to races), then a 'Verwijder' (delete) button will be shown.
    :param pers_id: ID of the Participant for which overview info is required.
    :return:
    """
    part = mg.Person(pers_id)
    person_dict = part.get_dict()
    races = mg.races4person(pers_id)
    # Don't count on len(races), since this is competition races. Remove person only if not used across all
    # competitions.
    persons = mg.person_list()
    return render_template('person_races_list.html', person=person_dict, races=races, persons=persons)


@main.route('/person/<pers_id>/delete')
@login_required
def person_delete(pers_id):
    """
    This method will get an id for a participant that can be removed. Checks have been done to make sure that there
    are no more connections (relations) with this participant.

    :param pers_id: NID of the person to be removed

    :return: person_list
    """
    person = mg.Person(pers_id)
    if person.active():
        current_app.logger.warning("Request to delete id {pers_id} but person participates in races"
                                   .format(pers_id=pers_id))
    else:
        mg.remove_node_force(pers_id)
    return redirect(url_for('main.person_list'))


@main.route('/organization/list')
def organization_list():
    organizations = mg.organization_list()
    return render_template('organization_list.html', organizations=organizations)


@main.route('/organization/add', methods=['GET', 'POST'])
@login_required
def organization_add(org_id=None):
    if request.method == "POST":
        form = OrganizationAdd()
        # if form.validate_on_submit(): Form Validate doesn't work on SelectField with choices not defined.
        city = mg.get_location(form.location.data)
        org_dict = dict(name=form.name.data,
                        location=city,
                        datestamp=form.datestamp.data,
                        org_type=form.org_type.data)
        if org_id:
            current_app.logger.debug("Modify organisation with ID {id}".format(id=org_id))
            org = mg.Organization(org_id=org_id)
            if org.edit(**org_dict):
                flash(org_dict["name"] + ' aangepast.', "success")
            else:
                flash(org_dict["name"] + ' bestaat reeds.', "warning")
        else:
            current_app.logger.debug("Ready to add organization with values {v}".format(v=org_dict))
            if mg.Organization().add(**org_dict):
                flash(org_dict["name"] + ' toegevoegd als organizatie', "success")
            else:
                flash(org_dict["name"] + ' bestaat reeds, niet toegevoegd.', "warning")
        # Form validated successfully, clear fields!
        return redirect(url_for('main.organization_list'))
    # Request Method is GET or Form did not validate
    # Note that in case Form did not validate, the fields will be reset.
    # But how can we fail on form_validate?
    organizations = mg.organization_list()
    if org_id:
        current_app.logger.debug("Get Form to edit organization with ID: {id}".format(id=org_id))
        org = mg.Organization(org_id=org_id)
        name = org.get_name()
        location = org.get_location()["nid"]
        datestamp = org.get_date()["key"]
        org_type = org.get_org_type()
        if org_type == "Deelname":
            org_type_flag = True
        else:
            org_type_flag = False
        form = OrganizationAdd(org_type=org_type_flag)
        form.name.data = name
        form.location.data = location
        form.datestamp.data = my_env.datestr2date(datestamp)
    else:
        current_app.logger.debug("Get Form to add organization")
        name = None
        location = None
        datestamp = None
        form = OrganizationAdd()
    # Form did not validate successfully, keep fields.
    form.location.choices = mg.get_location_list()
    return render_template('organization_add.html', form=form, name=name, location=location,
                           datestamp=datestamp, organizations=organizations)


@main.route('/organization/edit/<org_id>', methods=['GET', 'POST'])
@login_required
def organization_edit(org_id):
    """
    This method will edit an existing organization.

    :param org_id: The Node ID of the organization.

    :return:
    """
    # current_app.logger.debug("Evaluate Organization/edit")
    return organization_add(org_id=org_id)


@main.route('/organization/delete/<org_id>', methods=['GET', 'POST'])
@login_required
def organization_delete(org_id):
    """
    This method will delete an existing organization. This can be done only if there are no races attached to the
    organization.
    :param org_id: The Node ID of the organization.
    :return: True if the organization is removed, False otherwise.
    """
    # Todo: Check on Organization Date, does this needs to be removed?
    # Todo: Check on Organization Location, does this needs to be removed?
    current_app.logger.error("Delete organization {org_id}".format(org_id=org_id))
    if mg.organization_delete(org_id=org_id):
        flash("Organizatie verwijderd.", "success")
        return redirect(url_for('main.organization_list'))
    else:
        flash("Organizatie niet verwijderd, er zijn nog wedstrijden mee verbonden.", "warning")
        return redirect(url_for('main.race_add', org_id=org_id))


@main.route('/race/<org_id>/list')
def race_list(org_id):
    """
    This method will manage races with an organization. It will get the organization object based on ID. Then it will
    show the list of existing races for the organization. Races need to be added, removed or modified.

    :param org_id: Organization ID

    :return:
    """
    race_list_attribs = mg.get_race_list_attribs(org_id)
    return render_template('organization_races.html', **race_list_attribs)


@main.route('/race/<org_id>/add', methods=['GET', 'POST'])
@login_required
def race_add(org_id, race_id=None):
    """
    This method allows to add or edit a race. Race name is optional. Category/MF makes label.

    :param org_id: nid of the organization to which the race is added.

    :param race_id:  nid of the race if edit is required.

    :return:
    """
    form = RaceAdd()
    if request.method == "POST":
        # if form.validate_on_submit(): - validate_on_submit doesn't work with Select List.
        params = dict(
            name=form.name.data,
            categories=form.category.data,
            mf=form.mf.data,
            short=form.cross.data
        )
        if race_id:
            racename = mg.Race(race_id=race_id).edit(**params)
            flash("Race {rl} modified in Organization".format(rl=racename), "success")
        else:
            racename = mg.Race(org_id).add(**params)
            flash("Race {rl} created in Organization".format(rl=racename), "success")
        # Form validated successfully, clear fields!
        return redirect(url_for('main.race_list', org_id=org_id))
    else:
        # Get Form.
        race_add_attribs = mg.get_race_list_attribs(org_id)
        form.category.choices = mg.get_category_list()
        if race_id:
            race = mg.Race(race_id=race_id)
            form.name.data = race.get_name()
            form.cross.data = race.is_short()
            form.category.data = race.get_cat_nids()
            form.mf.data = race.get_mf_value()
            race_add_attribs["racename"] = race.get_racename()
        race_add_attribs['form'] = form
        return render_template('organization_races.html', **race_add_attribs)


@main.route('/races_default/<org_id>')
@login_required
def races_default(org_id):
    """
    This method will add a list of default races for an organization. No check is done if races exist already.
    The races need to be modified for combination or short race.

    :param org_id: Organization nid.

    :return: Redirect to the races_list for the organization
    """
    nr_races = len(mg.get_race_list(org_id=org_id))
    if nr_races == 0:
        mg.races_generate(org_id)
    else:
        msg = "Cannot generate races, there are {n} races defined already.".format(n=nr_races)
        flash(msg, "error")
    return redirect(url_for('main.race_list', org_id=org_id))


@main.route('/race/delete/<race_id>', methods=['GET', 'POST'])
@login_required
def race_delete(race_id):
    """
    This method will delete an existing race. This can be done only if there are no participants attached to the
    race.

    :param race_id: The Node ID of the race.

    :return: True if the race is removed, False otherwise.
    """
    current_app.logger.debug("Delete race {race_id}".format(race_id=race_id))
    race = mg.Race(race_id=race_id)
    org_id = race.get_org_id()
    if mg.race_delete(race_id=race_id):
        flash("Wedstrijd verwijderd.", "info")
        return redirect(url_for('main.race_list', org_id=org_id))
    else:
        flash("Wedstrijd niet verwijderd, er zijn nog deelnemers mee verbonden.", "warning")
        return redirect(url_for('main.participant_add', race_id=race_id))


@main.route('/race/edit/<org_id>/<race_id>', methods=['GET', 'POST'])
@login_required
def race_edit(org_id, race_id):
    """
    This method will edit an existing race.

    :param org_id: The Node ID of the organization.

    :param race_id: The Node ID of the race.

    :return:
    """
    return race_add(org_id=org_id, race_id=race_id)


@main.route('/participant/<race_id>/list', methods=['GET'])
def participant_list(race_id):
    """
    This method will show the participants in sequence of arrival for a race.
    :param race_id:
    :return:
    """
    race = mg.Race(race_id=race_id)
    param_dict = dict(
        race_label=race.get_label(),
        org_id=race.get_org_id(),
        race_id=race_id
    )
    finishers = mg.participant_seq_list(race_id)
    if finishers:
        param_dict['finishers'] = finishers
    return render_template('participant_list.html', **param_dict)


@main.route('/participant/<race_id>/add', methods=['GET', 'POST'])
@login_required
def participant_add(race_id):
    """
    This method will add a person to a race. The previous runner (earlier arrival) is selected from drop-down list.
    By default the person is appended as the last position in the race, so the previous person was the last one in the
    race. First position is specified as previous runner equals -1.

    :param race_id: ID of the race.

    :return: The person is added or modified as a participant to the race.
    """
    race = mg.Race(race_id=race_id)
    race_label = race.get_label()
    if request.method == "POST":
        # Call form to get input values
        form = ParticipantAdd()
        # Add collected info as participant to race.
        runner_id = form.name.data
        prev_runner_id = form.prev_runner.data
        # Create the participant node, connect to person and to race.
        part = mg.Participant(race_id=race_id, person_id=runner_id, prev_person_id=prev_runner_id)
        # Collect properties for this participant so that they can be added to the participant node.
        props = {}
        for prop in part_config_props:
            if form.data[prop]:
                props[prop] = form.data[prop]
        part.set_props(**props)
        return redirect(url_for('main.participant_add', race_id=race_id))
    else:
        # Get method, initialize page.
        org_id = race.get_org_id()
        part_last = mg.participant_last_id(race_id)
        # Initialize Form
        form = ParticipantAdd(prev_runner=part_last)
        next_part_nodes = race.get_next_part()
        form.name.choices = [(x["nid"], x["name"]) for x in next_part_nodes]
        form.prev_runner.choices = mg.participant_after_list(race_id)
        param_dict = dict(
            form=form,
            race_id=race_id,
            race_label=race_label,
            org_id=org_id
        )
        finishers = mg.participant_seq_list(race_id)
        if finishers:
            param_dict['finishers'] = finishers
        return render_template('participant_add.html', **param_dict)


@main.route('/participant/edit/<part_id>', methods=['GET', 'POST'])
@login_required
def participant_edit(part_id):
    """
    This method allows to edit a participant in the race. It is similar to the participant_add, but with sufficient
    differences to justify a separate method.
    :param part_id: NID of the participant. This is sufficient to find Person and Race objects.
    :return:
    """
    part = mg.Participant(part_id=part_id)
    person_nid = part.get_person_nid()
    person = mg.Person(person_id=person_nid)
    person_dict = person.get_dict()
    race_id = part.get_race_nid()
    race = mg.Race(race_id=race_id)
    race_label = race.get_label()
    if request.method == "POST":
        # Call form to get input values
        form = ParticipantEdit()
        # Collect properties for this participant
        props = {}
        for prop in part_config_props:
            try:
                props[prop] = form.data[prop]
            except KeyError:
                pass
        part.set_props(**props)
        return redirect(url_for('main.participant_add', race_id=race_id))
    else:
        # Get method, initialize page.
        org_id = mg.get_org_id(race_id)
        # Initialize Form, populate with keyword arguments
        # (http://wtforms.readthedocs.io/en/latest/crash_course.html#how-forms-get-data)
        part_props = part.get_props()
        form = ParticipantEdit(**part_props)
        finishers = mg.participant_seq_list(race_id)
        # There must be finishers, since I can update one of them
        return render_template('participant_edit.html', form=form, race_id=race_id, finishers=finishers,
                               race_label=race_label, org_id=org_id, person=person_dict)


@main.route('/participant/remove/<race_id>/<pers_id>', methods=['GET', 'POST'])
@login_required
def participant_remove(race_id, pers_id):
    """
    This method will remove the participant from the race and return to the race.

    :param race_id: ID of the race. This can be calculated, but it is always available.

    :param pers_id: Node ID of the participant in the race.

    :return:
    """
    """
    person = mg.Person(person_id=pers_id)
    person_name = person.get()
    form = ParticipantRemove()
    race_label = mg.race_label(race_id)
    finishers = mg.participant_seq_list(race_id, add_points=True)
    if request.method == "GET":
        return render_template('participant_remove.html', form=form, race_id=race_id, finishers=finishers,
                               race_label=race_label, pers_label=person_name)
    elif request.method == "POST":
        if form.submit_ok.data:
    """
    part = mg.Participant(race_id=race_id, person_id=pers_id)
    part.remove()
    return redirect(url_for('main.participant_add', race_id=race_id))


@main.route('/result_select_cat/<mf>', methods=['GET'])
def result_select_cat(mf):
    params = dict(
        categories=mg.get_category_list(),
        mf=mf
    )
    return render_template("result_select_cat.html", **params)


@main.route('/result/<mf>/<cat>/', methods=['GET'])
@main.route('/result/<mf>/<cat>/<person_id>')
def results(mf, cat, person_id=None):
    result_set = mg.results_for_category(mf=mf, cat=cat)
    cat_name = mg.get_category_name(cat)
    param_dict = dict(
        result_set=result_set,
        cat_nid=cat,
        cat=cat_name,
        mf=mf
    )
    if person_id:
        races = mg.races4person(person_id)
        person = mg.Person(person_id)
        person_dict = person.get_dict()
        param_dict["races"] = races
        param_dict["person"] = person_dict
    return render_template("result_list.html", **param_dict)

@main.route('/overview/<mf>', methods=['GET'])
def overview(mf):
    """
    This method shows the results in detail. For every person the result in every race will be shown. Note that

    :param mf: Dames OR Heren

    :return: The Overview list receives the list of races, the result_set with participants in arrival sequence and a
    dictionary with person nid as key. Value is a dictionary the race results per person.
    """
    org_list = mg.organization_list()
    result_seq = mg.results_for_mf(mf)
    param_dict = dict(
        org_list=org_list,
        result_set=result_seq,
        mf=mf
    )
    result4person = {}
    # Person nid is 4th element in the tuple
    for person_res in result_seq:
        person_nid = person_res[3]
        races = mg.races4person_org(person_nid)
        result4person[person_nid] = races
    param_dict['result4person'] = result4person
    return render_template("overview_list.html", **param_dict)


@main.errorhandler(404)
def not_found(e):
    return render_template("404.html", err=e)
