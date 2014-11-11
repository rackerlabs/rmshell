# Copyright (c) 2013 Jesse Keating <jesse.keating@rackspace.com>
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import ConfigParser
import logging
import sys
import os

import redmine
import tempfile
from redmine import exceptions as rm_exc
from subprocess import call


# Setup the basic logging objects
LOG = logging.getLogger('rore')


def get_user(rmine, userdata):
    """Get the user ID from the provided data"""

    # first see if we got an int
    try:
        userdata = int(userdata)
        return userdata
    except ValueError:
        pass
    users = rmine.user.filter(name=userdata)
    if not users:
        raise RuntimeError('Unknown user %s' % userdata)
    if len(users) > 1:
        raise RuntimeError('Multiple users for %s found' % userdata)
    return users[0].id


def print_issue(rmine, issue, verbose=False, oneline=False):
    """Print out a redmine issue object."""

    # handle unauth issues -- github #20
    if issue.id == 0:
        print('Unauthorized to view this issue')
        return
    # handle oneline printing
    if oneline:
        print('%s %s %s %s %s %s' % (issue.id, issue.project.name,
                                     issue.tracker.name, issue.priority.name,
                                     issue.status.name, issue.subject))
        return
    print('%s ( %s )' % (issue.id, issue.url))
    print('subject:     %s' % issue.subject)
    print('type:        %s' % issue.tracker.name)
    try:
        print('assigned to: %s' % issue.assigned_to.name)
    except rm_exc.ResourceAttrError:
        print('assigned to: UNASSIGNED')
    print('project:     %s' % issue.project.name)
    print('status:      %s' % issue.status.name)
    print('priority:    %s' % issue.priority.name)
    print('completion:  %s' % issue.done_ratio)
    if verbose:
        # Here is where we should enumerate all the possible fields
        print('priority:    %s' % issue.priority.name)
        print('start date:  %s' % issue.start_date)
        try:
            print('due date:    %s' % issue.due_date)
        except rm_exc.ResourceAttrError:
            pass
        try:
            print('parent:      %s' % issue.parent['id'])
        except rm_exc.ResourceAttrError:
            pass
        print('updated_on:  %s' % issue.updated_on)
        if hasattr(issue, 'description'):
            print('description:\n')
            print(issue.description)
        print('----')
        for relation in issue.relations:
            # Get the verb right for blocking relationship
            reltype = relation.relation_type
            if relation.issue_id != issue.id:
                if relation.relation_type == 'blocks':
                    reltype = 'blocked by'
                if relation.relation_type == 'blocked':
                    reltype = 'blocks'
                relish = rmine.issue.get(relation.issue_id)
            else:
                relish = rmine.issue.get(relation.issue_to_id)
            # Check for unauth -- wtf? See github #20
            if relish.id == 0:
                continue
            # Get the verb right for blocking relationship
            reltype = relation.relation_type
            if relation.issue_id != issue.id:
                if relation.relation_type == 'blocks':
                    reltype = 'blocked by'
                if relation.relation_type == 'blocked':
                    reltype = 'blocks'
                if relation.relation_type == 'duplicates':
                    reltype = 'duplicated by'
                if relation.relation_type == 'precedes':
                    reltype = 'preceded by'
                if relation.relation_type == 'follows':
                    reltype = 'followed by'
            print('%s %s - %s #%s: %s (%s)') % (reltype,
                                                relish.project.name,
                                                relish.tracker.name,
                                                relish.id,
                                                relish.subject,
                                                relation.id)
        for journ in issue.journals:
            print('\n####')
            print('Updated by %s on %s:' % (journ.user.name,
                                            journ.created_on))
            if hasattr(journ, 'notes'):
                print(journ.notes)
    print('\n')


def print_project(rmine, proj, verbose=False):
    """Print out a redmine project object."""

    print('%s ( %s )' % (proj.name, '%s/projects/%s' % (rmine.url,
                                                        proj.identifier)))
    if verbose:
        # Here is where we should enumerate all the possible fields
        print('description: %s' % proj.description)
        print('identifier: %s' % proj.identifier)
        try:
            print('parent: %s' % proj.parent['name'])
        except rm_exc.ResourceAttrError:
            pass
    print('\n')


def editor_text(initial_description=""):
    EDITOR = os.environ.get('EDITOR')
    text = initial_description
    if EDITOR:
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False,
                                         dir='/tmp/') as tmp:
            tmp.write(initial_description)
            tmp.flush()
            call([EDITOR, tmp.name])
        with open(tmp.name, 'r') as fh:
            text = fh.read()
        os.remove(tmp.name)
    return text


def create_relation(rmine, issue, relissue, reltype):
    """Creates a new issue relationship between two issues."""

    rmine.issue_relation.create(issue_id=issue,
                                issue_to_id=relissue,
                                relation_type=reltype)


def get_priority(rmine, priority):
    """Gets the id for the priority passed in."""

    priorities = rmine.enumeration.filter(resource='issue_priorities')
    p = [p for p in priorities if p.name.lower() == priority.lower()]
    if len(p) == 0:
        raise RuntimeError("Priority '%s' is not a priority.")
    return p[0]


def issues(args, rmine):
    """Handle issues"""

    # Just print issue details
    if args.ID and not (args.update or args.close):
        ishs = [rmine.issue.get(ID) for ID in args.ID]
        for ish in ishs:
            print_issue(rmine, ish, args.verbose, args.oneline)
        return

    # query
    if args.query:
        qdict = {}
        if args.project:
            qdict['project_id'] = args.project
        if args.nosubs:
            qdict['subproject_id'] = '!*'
        if args.assigned_to:
            qdict['assigned_to_id'] = get_user(rmine, args.assigned_to)
        if args.mine:
            my_id = rmine.user.get('current').id
            qdict['assigned_to_id'] = my_id
        if args.status:
            qdict['status_id'] = args.status
        if args.query_id:
            if not args.project:
                raise RuntimeError("query_id argument requires '--project "
                                   "[projectid]' argument also")
            qdict['query_id'] = args.query_id
        # Get the issues
        ishes = rmine.issue.filter(**qdict)
        if args.priority:
            priority = get_priority(rmine, args.priority)
            ishes = [i for i in ishes
                     if i.priority.name.lower() == priority.name.lower()]
        # This output is kinda lame, but functional for now
        for issue in ishes:
            print_issue(rmine, issue, args.verbose, args.oneline)
            if not args.oneline:
                print('##############')
        return

    # create
    if args.create:
        idict = {}
        # We have to have these items to continue
        if not args.project or not args.subject:
            raise RuntimeError('project and subject must be defined')
        idict['project_id'] = args.project
        idict['subject'] = args.subject
        # Get tracker by type
        itype = [
            tracker.id for tracker in rmine.tracker.all() if
            tracker.name == args.type]
        try:
            idict['tracker_id'] = itype[0]
        except IndexError:
            raise RuntimeError('Unknown issue type %s' % args.type)
        if args.assigned_to and args.assigned_to != 'UNASSIGNED':
            idict['assigned_to_id'] = get_user(rmine, args.assigned_to)
        # Would be rad to do a git commit like editor pop up here
        if args.description:
            idict['description'] = args.description
        else:
            idict['description'] = editor_text()
        # figure out the status
        if args.status:
            stat = [status for status in rmine.issue_status.all() if
                    status.name == args.status]
            try:
                idict['status_id'] = stat[0].id
            except IndexError:
                raise RuntimeError('Unknown issue type %s' % args.type)
        # set priority
        if args.priority:
            p = get_priority(rmine, args.priority)
            idict['priority_id'] = p.id
        # Create the issue
        issue = rmine.issue.create(**idict)
        # Create a relationship if one was asked for
        if args.relate_to:
            create_relation(rmine, issue.id, args.relate_to,
                            args.relation_type)
            issue = issue.refresh()
        # Print it out
        print_issue(rmine, issue, args.verbose, args.oneline)
        return

    # update the ticket(s)
    if args.update:
        ishs = [rmine.issue.get(ID) for ID in args.ID]
        udict = {}
        # Discover status ID
        if args.status:
            stat = [status for status in rmine.issue_status.all() if
                    status.name == args.status]
            try:
                udict['status_id'] = stat[0].id
            except IndexError:
                raise RuntimeError('Unknown issue status %s' % args.status)

        if args.type:
            itype = [
                tracker for tracker in rmine.tracker.all()
                if tracker.name == args.type]
            try:
                udict['tracker_id'] = itype[0].id
            except IndexError:
                raise RuntimeError('Unknown issue type %s' % args.type)

        if args.assigned_to:
            udict['assigned_to_id'] = get_user(rmine, args.assigned_to)
        if args.project:
            udict['project_id'] = args.project
        if args.subject:
            udict['subject'] = args.subject
        if args.description:
            udict['description'] = args.description
        if args.priority:
            udict['priority_id'] = get_priority(rmine, args.priority).id
        if args.notes:
            udict['notes'] = args.notes

        for ish in ishs:
            if udict:
                rmine.issue.update(ish.id, **udict)
            else:
                rmine.issue.get(ish.id)
            if args.relate_to:
                create_relation(rmine, ish.id, args.relate_to,
                                args.relation_type)
            ish = ish.refresh()
            print_issue(rmine, ish, args.verbose, args.oneline)
        return

    # close the ticket(s)
    if args.close:
        ishs = [rmine.issue.get(ID) for ID in args.ID]
        closestatus = [status for status in rmine.issue_status.all() if
                       status.name == 'Closed']
        for ish in ishs:
            rmine.issue.update(ish.id, status_id=closestatus[0].id,
                               notes=args.notes)
            ish = ish.refresh()
            print_issue(rmine, ish, args.verbose, args.oneline)
        return

    # issue types
    if args.list_types:
        if args.project:
            # Get trackers via the project entry point
            proj = rmine.project.get(args.project, include='trackers')
            print('Available issue types for %s :' % proj.url)
            print('\n'.join(itype.name for itype in proj.trackers))
        else:
            print('Available issue types for %s :' % rmine.url)
            print('\n'.join(itype.name for itype in rmine.tracker.all()))
        return

    # issue types
    if args.list_statuses:
        print('Available issue statuses for %s :' % rmine.url)
        print('\n'.join(status.name for status in rmine.issue_status.all()))
        return

    # issue queries
    if args.list_queries:
        print('Available issue queries for %s :' % rmine.url)
        print('\n'.join("%s %s" % (q.id, q.name) for q in
                        sorted(rmine.query.all(), key=lambda k: k['id'])))
        return

    # delete a relation
    if args.delete_relation:
        relation = rmine.issue_relation.get(args.delete_relation)
        rmine.issue_relation.delete(args.delete_relation)
        print('Deleted relation %s: %s %s %s' % (relation.id,
                                                 relation.issue_id,
                                                 relation.relation_type,
                                                 relation.issue_to_id))


def projects(args, rmine):
    """Handle projects"""

    if args.list:
        for proj in rmine.project.all():
            print_project(rmine, proj, args.verbose)
        return


def cmd():
    """This is the entry point for the shell command"""

    parser = argparse.ArgumentParser(prog='rore')
    # config
    parser.add_argument('--config', '-C', default=None,
                        help='Specify a config file to use '
                        '(defaults to ~/.rore)')
    parser.add_argument('--site', '-S', default='default',
                        help='Specify which site to use '
                        '(defaults to default)')
    # verbosity
    parser.add_argument('-v', action='store_true',
                        help='Run with verbose debug output')
    parser.add_argument('-q', action='store_true',
                        help='Run quietly only displaying errors')

    # subparsers
    subparsers = parser.add_subparsers(
        title='Subcommands',
        description='Valid Redmine interaction targets',
        help='Each target has its own --help.')

    # Issues
    issues_parser = subparsers.add_parser('issues',
                                          help='Interact with issues')
    # verbs
    issues_parser.add_argument('--query', action='store_true',
                               help='Query for tickets')
    issues_parser.add_argument('--create', action='store_true',
                               help='Create a new ticket')
    issues_parser.add_argument('--close', action='store_true',
                               help='Close a ticket')
    issues_parser.add_argument('--update', action='store_true',
                               help='Update an existing ticket')
    issues_parser.add_argument('--list-types', action='store_true',
                               help='List available issue types. Specify a '
                               'project ID to get specific types for that '
                               'project')
    issues_parser.add_argument('--list-queries', action='store_true',
                               help='List available issue queries')
    issues_parser.add_argument('--list-statuses', action='store_true',
                               help='List available statuses.')
    issues_parser.add_argument('--delete_relation',
                               help='Delete a relationship',
                               type=int, metavar='RELATION_ID')
    # details
    issues_parser.add_argument('--project', help='Filter by or assign to '
                               'project')
    issues_parser.add_argument('--type', help='Filter by or create issue '
                               'type.  Defaults to Bug.')
    # I don't like the asterisk here, change it to something else soon
    issues_parser.add_argument('--nosubs', help='Filter out issues from sub '
                               'projects', action='store_true')
    group = issues_parser.add_mutually_exclusive_group()
    # Need a way to filter all assigned issues, just show unassigned
    group.add_argument('--assigned_to', help='Filter by or assign to '
                       'user. Defaults to UNASSIGNED when creating.')
    group.add_argument('--mine', action='store_true', help='Only your issues')
    issues_parser.add_argument('--priority', help='Filter by or create '
                               'priority. Defaults to Normal')
    issues_parser.add_argument('--status',
                               help='Only deal with issues with this status '
                               'or set an issue to this status.')
    issues_parser.add_argument('--subject', help='Set subject when creating '
                               'a new issue')
    issues_parser.add_argument('--description', help='Set description when '
                               'creating a new issue')
    issues_parser.add_argument('--notes', help='Notes to use when resolving '
                               'or closing an issue')
    issues_parser.add_argument('--query_id', help='Filter by query ID. '
                               ' Requires --project [project] and '
                               '--query arguments.')
    issues_parser.add_argument('--relate_to', help='Create a relationship',
                               type=int)
    issues_parser.add_argument('--relation_type', help='Type of relationship '
                               'to create',
                               choices=['relates', 'duplicates',
                                        'blocks', 'blocked',
                                        'precedes', 'follows'])
    # More options when showing issues
    issues_parser.add_argument('--verbose', action='store_true',
                               help='Show more of the ticket details',
                               default=False)
    issues_parser.add_argument('--oneline', action='store_true',
                               help='Show each ticket on one line',
                               default=False)

    # Lastly just feed specific issue numbers in
    issues_parser.add_argument('ID', help='Issue IDs to find', nargs='*')

    # assign the function
    issues_parser.set_defaults(command=issues)

    # Projects
    project_parser = subparsers.add_parser('projects',
                                           help='Interact with projects')
    # verbs
    project_parser.add_argument('--list', action='store_true',
                                help='List out all the projects')

    # details
    project_parser.add_argument('--verbose', action='store_true',
                                help='Show more of the project details',
                                default=False)
    # assign the function
    project_parser.set_defaults(command=projects)

    args = parser.parse_args()
    # Setup logging

    class StdoutFilter(logging.Filter):
        def filter(self, record):
            # If the record is 20 (INFO) or lower, let it through
            return record.levelno <= logging.INFO

    myfilter = StdoutFilter()
    formatter = logging.Formatter('%(message)s')
    stdouthandler = logging.StreamHandler(sys.stdout)
    stdouthandler.addFilter(myfilter)
    stdouthandler.setFormatter(formatter)
    stderrhandler = logging.StreamHandler()  # Defaults to stderr
    stderrhandler.setLevel(logging.WARNING)
    stderrhandler.setFormatter(formatter)
    LOG.addHandler(stdouthandler)
    LOG.addHandler(stderrhandler)

    if args.v:
        LOG.setLevel(logging.DEBUG)
    elif args.q:
        LOG.setLevel(logging.WARNING)
    else:
        LOG.setLevel(logging.INFO)

    # load the credentials
    if not args.config:
        args.config = '~/.rore'
    configfile = os.path.expanduser(args.config)
    cparser = ConfigParser.SafeConfigParser()
    try:
        cparser.readfp(open(configfile, 'r'))
    except IOError:
        LOG.error("Couldn't find config file: %s" % configfile)
        exit(1)

    siteurl = cparser.get(args.site, 'url')
    key = cparser.get(args.site, 'key')
    try:
        verify = cparser.getboolean(args.site, 'verify')
    except ConfigParser.NoOptionError:
        verify = False

    if not args.type:
        try:
            args.type = cparser.get(args.site, 'default issue tracker')
        except ConfigParser.NoOptionError:
            args.type = 'Bug'

    if not args.project:
        try:
            args.type = cparser.get(args.site, 'default issue project')
        except ConfigParser.NoOptionError:
            pass

    # Figure out a way to make this a config option in .rore
    rmine = redmine.Redmine(siteurl, key=key, requests={'verify': verify})

    # Run the required command -- pass args into it for reference
    args.command(args, rmine)
