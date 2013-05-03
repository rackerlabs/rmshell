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

# Setup the basic logging objects
log = logging.getLogger('rmshell')


def get_user(rmine, username):
    """Get the user ID from the provided user name"""

    users = rmine.users.query_to_list(name=username)
    if not users:
        raise RuntimeError('Unknown user %s' % username)
    return users[0].id


def print_issue(rmine, issue):
    """Print out a redmine issue object."""

    print('%s ( %s )' % (issue.id, '%s/issues/%s' % (rmine._url,
                                                     issue.id)))
    print('subject:     %s' % issue.subject)
    try:
        print('assigned to: %s' % issue.assigned_to.name)
    except AttributeError:
        print('assigned to: UNASSIGNED')
    print('project:     %s' % issue.project.name)
    print('status:      %s\n' % issue.status)


def issues(args, rmine):
    """Handle issues"""

    # query
    if args.query:
        qdict = {}
        if args.project:
            qdict['project_id'] = args.project
        if args.nosubs:
            qdict['subproject_id'] = '!*'
        if args.assigned_to:
            # Look up the user ID
            qdict['assigned_to_id'] = get_user(rmine, args.assigned_to)
        if args.status:
            qdict['status_id'] = args.status
        # Get the issues
        issues = rmine.issues.query_to_list(**qdict)
        # This output is kinda lame, but functional for now
        for issue in issues:
            print_issue(rmine, issue)

    # create
    if args.create:
        idict = {}
        # hardcode new issues to bug until pyredmine is patched for tracker
        # manipulation
        idict['tracker'] = 1
        # hardcode new issues to be status new
        idict['status'] = rmine.ISSUE_STATUS_ID_NEW
        # We have to have these items to continue
        if not args.project or not args.subject:
            raise RuntimeError('project and subject must be defined')
        idict['project'] = args.project
        idict['subject'] = args.subject
        if args.assigned_to and args.assigned_to != 'UNASSIGNED':
            idict['assigned_to_id'] = get_user(rmine, args.assigned_to)
        # Would be rad to do a git commit like editor pop up here
        if args.description:
            idict['description'] = args.description
        # Create the issue
        issue = rmine.issues.new(**idict)
        # Print it out
        print_issue(rmine, issue)


def cmd():
    """This is the entry point for the shell command"""

    parser = argparse.ArgumentParser(prog='rmshell')
    # config
    parser.add_argument('--config', '-C', default=None,
                        help='Specify a config file to use '
                        '(defaults to ~/.rmshell)')
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

    issues_parser = subparsers.add_parser('issues',
                                          help='Interact with issues')
    # verbs
    issues_parser.add_argument('--query', action='store_true',
                               help='Query for tickets')
    issues_parser.add_argument('--create', action='store_true',
                               help='Create a new ticket')
    issues_parser.add_argument('--update', action='store_true',
                               help='Update an existing ticket')
    # details
    issues_parser.add_argument('--project', help='Filter by or assign to '
                               'project')
    # I don't like the asterisk here, change it to something else soon
    issues_parser.add_argument('--nosubs', help='Filter out issues from sub '
                               'projects', action='store_true')
    # Need a way to filter all assigned issues, just show unassigned
    issues_parser.add_argument('--assigned_to', help='Filter by or assign to '
                               'user. Defaults to UNASSIGNED when creating.')
    # I don't like the asterisk here, change it to something else soon
    issues_parser.add_argument('--status', choices=['open', 'closed', '*'],
                               help='Only deal with issues with this status '
                               '(* for both open and closed)')
    issues_parser.add_argument('--subject', help='Set subject when creating '
                               'a new issue')
    issues_parser.add_argument('--description', help='Set description when '
                               'creating a new issue')
    # assign the function
    issues_parser.set_defaults(command=issues)

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
        args.config = '~/.rmshell'
    configfile = os.path.expanduser(args.config)
    cparser = ConfigParser.SafeConfigParser()
    cparser.readfp(open(configfile, 'r'))

    siteurl = cparser.get(args.site, 'url')
    key = cparser.get(args.site, 'key')

    rmine = redmine.Redmine(siteurl, key=key)

    # Run the required command -- pass args into it for reference
    args.command(args, rmine)
