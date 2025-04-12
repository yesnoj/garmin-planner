#!/usr/bin/env python
"""
Garmin Planner - Command Line Interface

This script provides a command-line interface for managing workouts
in Garmin Connect, including importing, exporting, scheduling, and managing
workout plans.
"""

import sys
import argparse
import logging
import os
import glob
import json

# Disable SSL verification to solve connection problems
os.environ['PYTHONHTTPSVERIFY'] = '0'

from planner.import_export import cmd_import_workouts
from planner.import_export import cmd_export_workouts
from planner.import_export import cmd_delete_workouts
from planner.schedule import cmd_schedule_workouts
from planner.schedule import cmd_unschedule_workouts
from planner.manage import cmd_list_scheduled
from planner.garmin_client import cmd_login

def parse_args(argv):
    """
    Parse command line arguments.
    
    Args:
        argv: Command line arguments
        
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Garmin Planner - Manage workout plans for Garmin Connect')

    # Common options
    parser.add_argument('--dry-run', action='store_true', default=False, 
                      help='Do not modify anything, only show what would be done.')
    parser.add_argument('--oauth-folder', default='~/.garth', 
                      help='Folder where the Garmin oauth token is stored.')
    parser.add_argument('--treadmill', action='store_true', default=False, 
                      help='Convert distance end conditions to time end conditions where possible (treadmill mode).')
    parser.add_argument('--log-level', required=False,
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='Set log level')

    # Add sub commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    subparsers.required = True  # Make subcommand required

    # Login command
    garmin_login = subparsers.add_parser('login', help='Refresh or create OAuth credentials for your Garmin account')
    garmin_login.set_defaults(func=cmd_login)
    garmin_login.add_argument('--email', required=False, help='Email address for Garmin Connect')
    garmin_login.add_argument('--password', required=False, help='Password for Garmin Connect')

    # Import command
    import_wo = subparsers.add_parser('import', help='Import workouts from a YAML file')
    import_wo.set_defaults(func=cmd_import_workouts)
    import_wo.add_argument('--workouts-file', required=True, help='YAML file containing the workouts to create')
    import_wo.add_argument('--name-filter', required=False, help='Only import workouts whose name matches the filter')
    import_wo.add_argument('--replace', action='store_true', default=False, 
                         help='Replace any existing workouts with the same name (only if workout was created)')

    # Export command
    export_wos = subparsers.add_parser('export', help='Export workouts from Garmin Connect')
    export_wos.set_defaults(func=cmd_export_workouts)
    export_wos.add_argument('--export-file', default='', help='Output file for exported workouts')
    export_wos.add_argument('--format', required=False,
                          choices=['JSON', 'YAML'],
                          default=None,
                          help='Format of the export file')
    export_wos.add_argument('--clean', required=False, action='store_true', default=False,
                          help='Remove null items and useless data')
    export_wos.add_argument('--name-filter', required=False, 
                          help='Name (or pattern) of workouts to export. Accepts regular expressions.')
    export_wos.add_argument('--workout-ids', required=False, 
                          help='Comma-separated list of workouts to export')

    # Delete command
    delete_wo = subparsers.add_parser('delete', help='Delete workouts from Garmin Connect')
    delete_wo.set_defaults(func=cmd_delete_workouts)
    delete_wo.add_argument('--workout-ids', required=False, 
                         help='Comma-separated list of workouts to delete')
    delete_wo.add_argument('--name-filter', required=False, 
                         help='Name (or pattern) of workouts to delete. Accepts regular expressions.')

    # Schedule command
    schedule = subparsers.add_parser('schedule', 
                                   help='Schedule workouts in a training plan. Workouts should have previously been added, and be named: [PLAN_ID] W01S01 [DESCRIPTION]')
    schedule.set_defaults(func=cmd_schedule_workouts)
    schedule.add_argument('--race-day', required=True, 
                       help='The date of the race. Should correspond to the last workout of the training plan.')
    schedule.add_argument('--training-plan', required=True, 
                        help='The training plan ID. Corresponds to the common prefix of all workouts in the plan.')
    schedule.add_argument('--workout-days', required=False, 
                        help='Comma-separated list of day indices (0=Monday, 6=Sunday) for each session in a week')
    schedule.add_argument('--start-day', required=False, 
                        help='The date from which to start planning the training sessions. Format: YYYY-MM-DD')

    # Unschedule command
    unschedule = subparsers.add_parser('unschedule', help='Unschedule workouts from calendar.')
    unschedule.set_defaults(func=cmd_unschedule_workouts)
    unschedule.add_argument('--start-date', required=False, 
                          help='The date from which to start looking for workouts in the calendar.')
    unschedule.add_argument('--training-plan', required=True, 
                          help='The training plan ID. Corresponds to the common prefix of all workouts in the plan.')

    # List command
    list_scheduled = subparsers.add_parser('list', help='List scheduled workouts')
    list_scheduled.set_defaults(func=cmd_list_scheduled)
    list_scheduled.add_argument('--start-date', required=False, 
                              help='The date from which to start looking for workouts in the calendar.')
    list_scheduled.add_argument('--end-date', required=False, 
                              help='The date up to which to look for workouts in the calendar.')
    list_scheduled.add_argument('--date-range', required=False, 
                              help='The date range. Can be: TODAY, TOMORROW, CURRENT-WEEK, CURRENT-MONTH.')
    list_scheduled.add_argument('--name-filter', required=False, 
                              help='Name (or pattern) of workouts to list. Accepts regular expressions.')

    # Parse the arguments
    args = parser.parse_args(argv)
    
    # Expand and normalize the oauth_folder path
    args.oauth_folder = os.path.expanduser(args.oauth_folder)
    
    return args

def validate_args(args):
    """
    Validate the command line arguments.
    
    Args:
        args: Parsed arguments
        
    Returns:
        True if arguments are valid, False otherwise
    """
    # Check if the oauth folder exists
    if not os.path.exists(args.oauth_folder) and args.command != 'login':
        logging.warning(f"OAuth folder {args.oauth_folder} does not exist.")
        logging.info("Please log in first using the 'login' command.")
        return False
    
    # Command-specific validation
    if args.command == 'import':
        if not os.path.exists(args.workouts_file):
            logging.error(f"Workouts file {args.workouts_file} does not exist.")
            return False
    
    # All validations passed
    return True

def setup_logging(log_level):
    """
    Set up logging with the specified level.
    
    Args:
        log_level: Logging level (e.g., 'INFO', 'DEBUG')
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    logging.basicConfig(
        level=numeric_level, 
        format='%(asctime)-15s %(levelname)s %(message)s'
    )

def get_or_throw(d, key, error):
    """
    Get a value from a dictionary or throw an exception.
    
    Args:
        d: Dictionary
        key: Key to look up
        error: Error message if the key is not found
        
    Returns:
        Value from the dictionary
        
    Raises:
        Exception: If the key is not found
    """
    try:
        return d[key]
    except KeyError:
        raise Exception(error)

def create_oauth_folder_if_not_exists(oauth_folder):
    """
    Create the OAuth folder if it doesn't exist.
    
    Args:
        oauth_folder: Path to the OAuth folder
    """
    if not os.path.exists(oauth_folder):
        try:
            os.makedirs(oauth_folder, exist_ok=True)
            logging.info(f"Created OAuth folder: {oauth_folder}")
        except Exception as e:
            logging.error(f"Failed to create OAuth folder: {str(e)}")

def main():
    """Main entry point for the script."""
    args = parse_args(sys.argv[1:])
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Create OAuth folder if needed
    create_oauth_folder_if_not_exists(args.oauth_folder)
    
    # Validate arguments
    if not validate_args(args):
        return 1
    
    try:
        # Execute the selected command
        result = args.func(args)
        
        # If the command function returns None or 0, it was successful
        return 0 if result is None or result == 0 else 1
        
    except KeyboardInterrupt:
        logging.info("Operation canceled by user.")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        logging.error(f"Error executing command: {str(e)}")
        import traceback
        logging.debug(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main())