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
import logging
import sys
import os
import ConfigParser
import redmine
from redmine.exceptions import *

# Setup the basic logging objects
log = logging.getLogger('rore')


def get_user(rmine, username):
    """Get the user ID from the provided user name"""

    users = rmine.user.filter(name=username)
    if not users:
        raise RuntimeError('Unknown user %s' % username)
    return users[0].id


def print_issue(rmine, issue, verbose=False):
    """Print out a redmine issue object."""

    print('%s ( %s )' % (issue.id, issue.url))
    print('subject:     %s' % issue.subject)
    print('type:        %s' % issue.tracker.name)
    try:
        print('assigned to: %s' % issue.assigned_to.name)
    except ResourceAttrError:
        print('assigned to: UNASSIGNED')
    print('project:     %s' % issue.project.name)
    print('status:      %s' % issue.status.name)
    print('completion:  %s' % issue.done_ratio)
    if verbose:
        # Here is where we should enumerate all the possible fields
        print('priority:    %s' % issue.priority.name)
        print('start date:  %s' % issue.start_date)
        try:
            print('due date:    %s' % issue.due_date)
        except ResourceAttrError:
            pass
        try:
            print('parent:      %s' % issue.parent['id'])
        except ResourceAttrError:
            pass
        print('updated_on:  %s' % issue.updated_on)
        print('description:\n')
        print(issue.description)
        print('----')
        for relation in issue.relations:
            relish = rmine.issue.get(relation.issue_to_id)
            print('%s %s - %s #%s: %s') % (relation.relation_type,
                                           relish.project.name,
                                           relish.tracker.name,
                                           relish.id,
                                           relish.subject)
        for journ in issue.journals:
            print('\n####')
            print('Updated by %s on %s:' % (journ.user.name,
                                            journ.created_on))
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
        except ResourceAttrError:
            pass
    print('\n')

def issues(args, rmine):
    """Handle issues"""

    # Just print issue details
    if args.ID and not (args.update or args.close):
        ishs = [rmine.issue.get(ID) for ID in args.ID]
        for ish in ishs:
            print_issue(rmine, ish, args.verbose)
        return

    # query
    if args.query:
        qdict = {}
        if args.project:
            qdict['project_id'] = args.project
        if args.nosubs:
            qdict['subproject_id'] = '!*'
        if args.assigned_to:
            qdict['assigned_to_id'] = args.assigned_to
        if args.status:
            qdict['status_id'] = args.status
        # Get the issues
        issues = rmine.issue.filter(**qdict)
        # This output is kinda lame, but functional for now
        for issue in issues:
            print_issue(rmine, issue, args.verbose)
            print('##############')
        return

    # create
    if args.create:
        idict = {}
        if not args.type:
            args.type='Bug'
        # Get tracker by type
        itype = [tracker.id for tracker in rmine.tracker.all() if
                tracker.name == args.type]
        try:
            idict['tracker_id'] = itype[0]
        except IndexError:
            raise RuntimeError('Unknown issue type %s' % args.type)
        # We have to have these items to continue
        if not args.project or not args.subject:
            raise RuntimeError('project and subject must be defined')
        idict['project_id'] = args.project
        idict['subject'] = args.subject
        # Figure out a way to discover if assigned_to is a int ID or if it needs
        # to be discovered from a name
        if args.assigned_to and args.assigned_to != 'UNASSIGNED':
            idict['assigned_to_id'] = args.assigned_to
        # Would be rad to do a git commit like editor pop up here
        if args.description:
            idict['description'] = args.description
        # Create the issue
        issue = rmine.issue.create(**idict)
        # Print it out
        print_issue(rmine, issue, args.verbose)
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
            itype = [tracker for tracker in rmine.tracker.all() if
                    tracker.name == args.type]
            try:
                udict['tracker_id'] = itype[0].id
            except IndexError:
                raise RuntimeError('Unknown issue type %s' % args.type)

        if args.assigned_to:
            udict['assigned_to_id'] = args.assigned_to
        if args.project:
            udict['project_id'] = args.project
        if args.subject:
            udict['subject'] = args.subject
        if args.description:
            udict['description'] = args.description
        if args.notes:
            udict['notes'] = args.notes

        for ish in ishs:
            rmine.issue.update(ish.id, **udict)
            ish = ish.refresh()
            print_issue(rmine, ish, args.verbose)
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
            print_issue(rmine, ish, args.verbose)
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
                               help='List available issue types. Specify a'
                               'project ID to get specific types for that'
                               'project')
    issues_parser.add_argument('--list-statuses', action='store_true',
                               help='List available statuses.')
    # details
    issues_parser.add_argument('--project', help='Filter by or assign to '
                               'project')
    issues_parser.add_argument('--type', help='Filter by or create issue '
                               'type.  Defaults to Bug.')
    # I don't like the asterisk here, change it to something else soon
    issues_parser.add_argument('--nosubs', help='Filter out issues from sub '
                               'projects', action='store_true')
    # Need a way to filter all assigned issues, just show unassigned
    issues_parser.add_argument('--assigned_to', help='Filter by or assign to '
                               'user. Defaults to UNASSIGNED when creating.')
    issues_parser.add_argument('--status',
                               help='Only deal with issues with this status '
                               'or set an issue to this status.')
    issues_parser.add_argument('--subject', help='Set subject when creating '
                               'a new issue')
    issues_parser.add_argument('--description', help='Set description when '
                               'creating a new issue')
    issues_parser.add_argument('--notes', help='Notes to use when resolving '
                               'or closing an issue')

    # More options when showing issues
    issues_parser.add_argument('--verbose', action='store_true',
                               help='Show more of the ticket details',
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
    log.addHandler(stdouthandler)
    log.addHandler(stderrhandler)

    if args.v:
        log.setLevel(logging.DEBUG)
    elif args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    # load the credentials
    if not args.config:
        args.config = '~/.rore'
    configfile = os.path.expanduser(args.config)
    cparser = ConfigParser.SafeConfigParser()
    cparser.readfp(open(configfile, 'r'))

    siteurl = cparser.get(args.site, 'url')
    key = cparser.get(args.site, 'key')

    # Figure out a way to make this a config option in .rore
    rmine = redmine.Redmine(siteurl, key=key, requests={'verify': False})

    # Run the required command -- pass args into it for reference
    args.command(args, rmine)
