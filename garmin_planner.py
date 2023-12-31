#! /usr/bin/env python
import sys
import argparse
import logging

from planner.fartlek import cmd_farlek
from planner.import_export import cmd_import_workouts
from planner.import_export import cmd_export_workouts
from planner.import_export import cmd_delete_workouts
from planner.schedule import cmd_schedule_workouts
from planner.schedule import cmd_unschedule_workouts

def parse_args(argv):
    parser = argparse.ArgumentParser()

    # common options
    parser.add_argument('--dry-run', action='store_true', default=False, help='Do not modify anything, only show what would be done.')
    parser.add_argument('--garmin-id', required=True, help='Garmin account ID')
    parser.add_argument('--garmin-password', required=True, help='Garmin account password')
    #parser.add_argument('--cookie-jar', help='Use cookies from this file')

    parser.add_argument('--log-level', required=False,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO',
                        help='set log level')

    # add sub commands
    subparsers = parser.add_subparsers(help='available commands')

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

    delete_wo = subparsers.add_parser('delete', help='delete workouts')
    delete_wo.set_defaults(func=cmd_delete_workouts)
    delete_wo.add_argument('--workout-ids', required=False, help='comma separated list of workouts to delete')
    delete_wo.add_argument('--name-filter', required=False, help='name (or part of the name) of workshop to delete. Accepts regular expressions.')

    schedule = subparsers.add_parser('schedule', help='schedule workouts in a training plan. Workouts should have previously been added, and be named: [PLAN_ID] W01S01 [DESCRIPTION]')
    schedule.set_defaults(func=cmd_schedule_workouts)
    schedule.add_argument('--race-day', required=True, help='the date of the race. Should correspond to the last workout of the training plan.')
    schedule.add_argument('--training-plan', required=True, help='the training plan ID. Corresponds to the common prefix of all workouts in the plan.')

    unschedule = subparsers.add_parser('unschedule', help='unschedule workouts from calendar.')
    unschedule.set_defaults(func=cmd_unschedule_workouts)
    unschedule.add_argument('--start-date', required=False, help='the date from which to start looking for workouts in the calendar.')
    unschedule.add_argument('--training-plan', required=True, help='the training plan ID. Corresponds to the common prefix of all workouts in the plan.')

    farlek = subparsers.add_parser('farlek', help='create a random farlek workout')
    farlek.set_defaults(func=cmd_farlek)
    farlek.add_argument('--duration', help='workout duration in mm:ss')
    farlek.add_argument('--target-pace', help='target pace in mm:ss')

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
