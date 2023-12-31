#! /usr/bin/env python

import json
import logging

import garminexport.garminclient

class GarminClient(garminexport.garminclient.GarminClient):

  def list_workouts(self):
    response = self.session.get(
        'https://connect.garmin.com/workout-service/workouts',
        params={'start': 1, 'limit': 999, 'myWorkoutsOnly': True})
    if response.status_code != 200:
      raise Exception(
        u'failed to fetch workouts: {}\n{}'.format(
          response.status_code, response.text))
    json_resp = json.loads(response.text)
    return (response.status_code, json_resp) 

  def add_workout(self, workout):
    response = self.session.post(
      'https://connect.garmin.com/workout-service/workout',
      json=workout.garminconnect_json())

    if response.status_code > 299:
      print('Add workout response status:' + str(response.status_code))
      print('Add workout response json:' + str(response.text))
    json_resp = json.loads(response.text)
    return (response.status_code, json_resp) 

  def delete_workout(self, workout_id):
    logging.info(f'deleting workout {workout_id}')
    response = self.session.delete(
      'https://connect.garmin.com/workout-service/workout/' + workout_id)

    if response.status_code > 299:
      logging.warn(f'could not delete workout {workout_id}. Resp code: {response.status_code}. Error: {response.text}')
    return response.status_code

  def get_calendar(self, year, month):
    logging.info(f'getting calendar. Year: {year}, month: {month}')
    response = self.session.get(
        f'https://connect.garmin.com/calendar-service/year/{year}/month/{month-1}')
    if response.status_code != 200:
      raise Exception(
        u'failed to fetch calendar: {}\n{}'.format(
          response.status_code, response.text))
    json_resp = json.loads(response.text)
    return json_resp

  def schedule_workout(self, workout_id, date):
    date_formatted = date
    if type(date_formatted) is not str:
      date_formatted = date.strftime('%Y-%m-%d')
    response = self.session.post(
      f'https://connect.garmin.com/workout-service/schedule/{workout_id}',
      json={'date' :date_formatted})

    if response.status_code > 299:
      print('Add workout response status:' + str(response.status_code))
      print('Add workout response json:' + str(response.text))
    return response.status_code

  def unschedule_workout(self, schedule_id):
    response = self.session.delete(
      f'https://connect.garmin.com/workout-service/schedule/{schedule_id}')

    if response.status_code > 299:
      print('Unschedule workout response status:' + str(response.status_code))
      print('Unschedule workout response json:' + str(response.text))
    return response.status_code
