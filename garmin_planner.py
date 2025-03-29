#! /usr/bin/env python
import sys
import argparse
import logging

from planner.fartlek import cmd_fartlek
from planner.import_export import cmd_import_workouts
from planner.import_export import cmd_export_workouts
from planner.import_export import cmd_delete_workouts
from planner.schedule import cmd_schedule_workouts
from planner.schedule import cmd_unschedule_workouts
from planner.manage import cmd_list_scheduled
from planner.garmin_client import cmd_login

def parse_args(argv):
    parser = argparse.ArgumentParser()

    # common options
    parser.add_argument('--dry-run', action='store_true', default=False, help='Do not modify anything, only show what would be done.')
    parser.add_argument('--oauth-folder', default='~/.garth', help='Folder where the Garmin oauth token is stored.')
    parser.add_argument('--treadmill', action='store_true', default=False, help='Convert distance end conditions to time end conditions where possible (treadmill mode).')

    parser.add_argument('--log-level', required=False,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO',
                        help='set log level')

    # add sub commands
    subparsers = parser.add_subparsers(help='available commands')

    garmin_login = subparsers.add_parser('login', help='refresh or create Oauth credentials for your Garmin account')
    garmin_login.set_defaults(func=cmd_login)


    import_wo = subparsers.add_parser('import', help='import workouts')
    import_wo.set_defaults(func=cmd_import_workouts)
    import_wo.add_argument('--workouts-file', required=True, help='yaml file containing the workouts to create')
    import_wo.add_argument('--name-filter', required=False, help='only import the workouts whose name matches the filter.')
    import_wo.add_argument('--replace', action='store_true', default=False, help='replace any existing workouts with the same name (only if workout was created)')

    export_wos = subparsers.add_parser('export', help='export current workouts')
    export_wos.set_defaults(func=cmd_export_workouts)
    export_wos.add_argument('--export-file', default='', help='yaml file containing the workouts to create')
    export_wos.add_argument('--format', required=False,
                        choices=['JSON', 'YAML'],
                        default=None,
                        help='format of the export file')
    export_wos.add_argument('--clean', required=False, action='store_true', default=False,
                        help='remove null items and useless data')
    export_wos.add_argument('--name-filter', required=False, help='name (or part of the name) of workout to export. Accepts regular expressions.')

    delete_wo = subparsers.add_parser('delete', help='delete workouts')
    delete_wo.set_defaults(func=cmd_delete_workouts)
    delete_wo.add_argument('--workout-ids', required=False, help='comma separated list of workouts to delete')
    delete_wo.add_argument('--name-filter', required=False, help='name (or part of the name) of workout to delete. Accepts regular expressions.')

    schedule = subparsers.add_parser('schedule', help='schedule workouts in a training plan. Workouts should have previously been added, and be named: [PLAN_ID] W01S01 [DESCRIPTION]')
    schedule.set_defaults(func=cmd_schedule_workouts)
    schedule.add_argument('--race-day', required=True, help='the date of the race. Should correspond to the last workout of the training plan.')
    schedule.add_argument('--training-plan', required=True, help='the training plan ID. Corresponds to the common prefix of all workouts in the plan.')
    schedule.add_argument('--reverse-order', action='store_true', default=False, help='Week numbers are in reverse order (17, 16, 15,..) instead of (1, 2, 3,...')

    unschedule = subparsers.add_parser('unschedule', help='unschedule workouts from calendar.')
    unschedule.set_defaults(func=cmd_unschedule_workouts)
    unschedule.add_argument('--start-date', required=False, help='the date from which to start looking for workouts in the calendar.')
    unschedule.add_argument('--training-plan', required=True, help='the training plan ID. Corresponds to the common prefix of all workouts in the plan.')

    list_scheduled = subparsers.add_parser('list', help='list scheduled workouts')
    list_scheduled.set_defaults(func=cmd_list_scheduled)
    list_scheduled.add_argument('--start-date', required=False, help='the date from which to start looking for workouts in the calendar.')
    list_scheduled.add_argument('--end-date', required=False, help='the date frup to which to look for workouts in the calendar.')
    list_scheduled.add_argument('--date-range', required=False, help='the date range. Can be: today, tomorrow, current_week, current_month.')
    list_scheduled.add_argument('--name-filter', required=False, help='name (or part of the name) of workout to export. Accepts regular expressions.')

    fartlek = subparsers.add_parser('fartlek', help='create a random fartlek workout')
    fartlek.set_defaults(func=cmd_fartlek)
    fartlek.add_argument('--duration', required=True, help='workout duration in mm:ss')
    fartlek.add_argument('--target-pace', required=True, help='target pace in mm:ss')
    fartlek.add_argument('--schedule', required=False, help='schedule this workout (today, tomorrow, YYY-MM-DD)')

    return parser.parse_args(argv)

def get_or_throw(d, key, error):
    try:
        return d[key]
    except:  # noqa: E722
        raise Exception(error)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
    logging.basicConfig(format=FORMAT)
    args.func(args)
