#! /usr/bin/env python

import json
import logging
import os
import garth
from getpass import getpass

class GarminClient():
    """Client for interacting with Garmin Connect API."""
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls, oauth_folder='oauth-folder'):
        """Get a singleton instance of GarminClient."""
        if cls._instance is None:
            cls._instance = cls(oauth_folder)
        elif cls._instance.oauth_folder != oauth_folder:
            # If a different OAuth folder is requested, create a new instance
            cls._instance = cls(oauth_folder)
        return cls._instance

    def __init__(self, oauth_folder='oauth-folder'):
        """Initialize the Garmin client with the given OAuth folder.
        
        Args:
            oauth_folder: Path to the folder containing OAuth credentials
        """
        self.oauth_folder = oauth_folder
        self.max_retries = 3  # Maximum number of retries for API calls
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize the Garth session."""
        try:
            # Ensure the OAuth folder exists
            if not os.path.exists(self.oauth_folder):
                os.makedirs(self.oauth_folder, exist_ok=True)
                logging.info(f"Created OAuth folder: {self.oauth_folder}")
            
            # Resume the Garth session using the OAuth credentials
            garth.resume(self.oauth_folder)
            logging.debug("Garmin Connect session initialized")
        except Exception as e:
            logging.error(f"Failed to initialize Garmin Connect session: {str(e)}")
            raise

    def _execute_api_call(self, method_name, *args, **kwargs):
        """Execute an API call with retry logic.
        
        Args:
            method_name: The name of the Garth method to call
            *args, **kwargs: Arguments to pass to the method
            
        Returns:
            Response from the API
            
        Raises:
            Exception: If the API call fails after all retries
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                # Get the method from the garth module
                method = getattr(garth, method_name)
                return method(*args, **kwargs)
            except Exception as e:
                last_error = e
                retries += 1
                logging.warning(f"API call failed (attempt {retries}/{self.max_retries}): {str(e)}")
                
                # Try to re-initialize the session for the next attempt
                if retries < self.max_retries:
                    try:
                        self._initialize_session()
                    except:
                        pass  # If re-initialization fails, just continue with the retry
        
        # If we get here, all retries failed
        logging.error(f"API call failed after {self.max_retries} attempts: {str(last_error)}")
        raise last_error

    def list_workouts(self):
        """List all workouts from Garmin Connect.
        
        Returns:
            List of workout data from Garmin Connect
        """
        logging.info("Fetching workout list from Garmin Connect")
        response = self._execute_api_call(
            "connectapi",
            '/workout-service/workouts',
            params={'start': 1, 'limit': 999, 'myWorkoutsOnly': True}
        )
        return response

    def add_workout(self, workout):
        """Add a new workout to Garmin Connect.
        
        Args:
            workout: Workout object to add
            
        Returns:
            Response from Garmin Connect API
        """
        logging.info(f"Adding workout: {workout.workout_name}")
        response = self._execute_api_call(
            "connectapi",
            '/workout-service/workout', 
            method="POST",
            json=workout.garminconnect_json()
        )
        return response 

    def delete_workout(self, workout_id):
        """Delete a workout from Garmin Connect.
        
        Args:
            workout_id: ID of the workout to delete
            
        Returns:
            Response from Garmin Connect API
        """
        logging.info(f'Deleting workout {workout_id}')
        response = self._execute_api_call(
            "connectapi",
            '/workout-service/workout/' + str(workout_id), 
            method="DELETE"
        )
        return response 

    def get_workout(self, workout_id):
        """Get a specific workout from Garmin Connect.
        
        Args:
            workout_id: ID of the workout to retrieve
            
        Returns:
            Workout data from Garmin Connect
        """
        logging.info(f'Getting workout {workout_id}')
        response = self._execute_api_call(
            "connectapi",
            '/workout-service/workout/' + str(workout_id), 
            method="GET"
        )
        return response 

    def update_workout(self, workout_id, workout):
        """Update an existing workout in Garmin Connect.
        
        Args:
            workout_id: ID of the workout to update
            workout: Updated Workout object
            
        Returns:
            Response from Garmin Connect API
        """
        logging.info(f'Updating workout {workout_id}')
        wo_json = workout.garminconnect_json()
        wo_json['workoutId'] = workout_id
        response = self._execute_api_call(
            "connectapi",
            '/workout-service/workout/' + str(workout_id), 
            method="PUT", 
            json=wo_json
        )
        logging.debug(f"Update response: {response}")
        return response 

    def get_calendar(self, year, month):
        """Get calendar data for a specific year and month.
        
        Args:
            year: Calendar year
            month: Calendar month (1-12)
            
        Returns:
            Calendar data from Garmin Connect
        """
        logging.info(f'Getting calendar. Year: {year}, month: {month}')
        response = self._execute_api_call(
            "connectapi",
            f'/calendar-service/year/{year}/month/{month-1}'
        )
        return response 

    def schedule_workout(self, workout_id, date):
        """Schedule a workout for a specific date.
        
        Args:
            workout_id: ID of the workout to schedule
            date: Date to schedule the workout (string 'YYYY-MM-DD' or datetime object)
            
        Returns:
            Response from Garmin Connect API
        """
        date_formatted = date
        if not isinstance(date_formatted, str):
            date_formatted = date.strftime('%Y-%m-%d')
        
        logging.info(f'Scheduling workout {workout_id} for {date_formatted}')
        response = self._execute_api_call(
            "connectapi",
            f'/workout-service/schedule/{workout_id}', 
            method="POST",
            json={'date': date_formatted}
        )
        return response 

    def unschedule_workout(self, schedule_id):
        """Remove a scheduled workout.
        
        Args:
            schedule_id: ID of the scheduled workout to remove
            
        Returns:
            Response from Garmin Connect API
        """
        logging.info(f'Unscheduling workout {schedule_id}')
        response = self._execute_api_call(
            "connectapi",
            f'/workout-service/schedule/{schedule_id}', 
            method="DELETE"
        )
        return response

def cmd_login(args):
    """Command to log in to Garmin Connect.
    
    Args:
        args: Command line arguments
    """
    try:
        email = input('Enter email address: ')
        password = getpass('Enter password: ')
        garth.login(email, password)
        
        # Ensure the OAuth folder exists
        oauth_folder = os.path.expanduser(args.oauth_folder)
        if not os.path.exists(oauth_folder):
            os.makedirs(oauth_folder, exist_ok=True)
            logging.info(f"Created OAuth folder: {oauth_folder}")
        
        garth.save(oauth_folder)
        logging.info(f"Successfully logged in and saved credentials to {oauth_folder}")
    except Exception as e:
        logging.error(f"Login failed: {str(e)}")
        raise