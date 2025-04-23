"""
Workout module - Classes for workout management with Garmin Connect.

This module provides classes for representing workouts and their components
in a format compatible with Garmin Connect.
"""

# Common constants for Garmin Connect API
SPORT_TYPES = {
    "running": 1,
    "cycling": 2,
    "swimming": 5
}

STEP_TYPES = {
    "warmup": 1, 
    "cooldown": 2, 
    "interval": 3, 
    "recovery": 4, 
    "rest": 5, 
    "repeat": 6, 
    "other": 7
}

END_CONDITIONS = {
    "lap.button": 1,
    "time": 2,
    "distance": 3,
    "calories": 4,
    "heart.rate": 5,
    "power": 6,
    "iterations": 7,
}

TARGET_TYPES = {
    "no.target": 1,
    "power.zone": 2,
    "cadence.zone": 3,
    "heart.rate.zone": 4,
    "speed.zone": 5,
    "pace.zone": 6,  # meters per second
}

class Workout:
    """
    Represents a workout consisting of multiple steps.
    
    A workout is a collection of workout steps that can be uploaded
    to Garmin Connect.
    """
    
    def __init__(self, sport_type, name, description=None):
        """
        Initialize a new workout.
        
        Args:
            sport_type: Type of sport (e.g., 'running', 'cycling')
            name: Name of the workout
            description: Optional description of the workout
        """
        if sport_type not in SPORT_TYPES:
            raise ValueError(f"Unsupported sport type: {sport_type}. " 
                             f"Must be one of {list(SPORT_TYPES.keys())}")
            
        self.sport_type = sport_type
        self.workout_name = name
        self.description = description
        self.workout_steps = []

    def add_step(self, step):
        """
        Add a workout step to the workout.
        
        Args:
            step: WorkoutStep object to add
        """
        if step.order == 0:
            step.order = len(self.workout_steps) + 1
        self.workout_steps.append(step)

    def dist_to_time(self):
        """
        Convert distance-based steps to time-based steps.
        
        This is useful for treadmill workouts where distance
        is hard to measure.
        """
        for ws in self.workout_steps:
            ws.dist_to_time()

    def garminconnect_json(self):
        """
        Convert the workout to Garmin Connect JSON format.
        
        Returns:
            Dictionary representation of the workout for Garmin Connect API
        """
        return {
            "sportType": {
                "sportTypeId": SPORT_TYPES[self.sport_type],
                "sportTypeKey": self.sport_type,
            },
            "workoutName": self.workout_name,
            "description": self.description,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": SPORT_TYPES[self.sport_type],
                        "sportTypeKey": self.sport_type,
                    },
                    "workoutSteps": [step.garminconnect_json() for step in self.workout_steps],
                }
            ],
        }

class WorkoutStep:
    """
    Represents a step within a workout.
    
    A step is a single component of a workout, such as warmup, cooldown,
    interval, recovery, or rest. It can also be a repeat group that contains
    other steps.
    """
    
    def __init__(
        self,
        order,
        step_type,
        description = '',
        end_condition="lap.button",
        end_condition_value=None,
        target=None,
    ):
        """
        Initialize a new workout step.
        
        Args:
            order: Order of the step within the workout
            step_type: Type of step (e.g., 'warmup', 'interval', 'repeat')
            description: Optional description of the step
            end_condition: Condition to end the step (e.g., 'time', 'distance')
            end_condition_value: Value for the end condition
            target: Optional Target object
            
        Valid end condition values:
        - distance: '2.0km', '1.125km', '1.6km'
        - time: '0:40', '4:20'
        - lap.button
        - iterations: for repeat steps
        """
        if step_type not in STEP_TYPES:
            raise ValueError(f"Unsupported step type: {step_type}. "
                             f"Must be one of {list(STEP_TYPES.keys())}")
            
        if end_condition not in END_CONDITIONS:
            raise ValueError(f"Unsupported end condition: {end_condition}. "
                             f"Must be one of {list(END_CONDITIONS.keys())}")
        
        self.order = order
        self.step_type = step_type
        self.description = description
        self.end_condition = end_condition
        self.end_condition_value = end_condition_value
        self.target = target or Target()
        self.child_step_id = 1 if self.step_type == 'repeat' else None
        self.workout_steps = []

    def add_step(self, step):
        """
        Add a sub-step to this step.
        
        This is primarily used for repeat steps, which can contain other steps.
        
        Args:
            step: WorkoutStep object to add as a sub-step
        """
        step.child_step_id = self.child_step_id
        if step.order == 0:
            step.order = len(self.workout_steps) + 1
        self.workout_steps.append(step)

    def end_condition_unit(self):
        """
        Get the unit for the end condition.
        
        Returns:
            Dictionary containing the unit information or None
        """
        if self.end_condition == "distance" and self.end_condition_value and isinstance(self.end_condition_value, str) and self.end_condition_value.endswith("km"):
            return {"unitKey": "kilometer"}
        else:
            return None

    def parsed_end_condition_value(self):
        """
        Parse the end condition value into the format required by Garmin Connect.
        
        Returns:
            Parsed value suitable for Garmin Connect API
        """
        # distance
        if self.end_condition == 'distance' and self.end_condition_value:
            if isinstance(self.end_condition_value, str) and self.end_condition_value.endswith("km"):
                return int(float(self.end_condition_value.replace("km", "")) * 1000)
            return self.end_condition_value

        # time
        elif self.end_condition == 'time' and self.end_condition_value:
            if isinstance(self.end_condition_value, str) and ":" in self.end_condition_value:
                m, s = [int(x) for x in self.end_condition_value.split(":")]
                return m * 60 + s
            return self.end_condition_value

        # iterations or other
        else:
            return self.end_condition_value

    def dist_to_time(self):
        """
        Convert distance-based end condition to time-based end condition.
        
        This is useful for treadmill runs where pace is hard to estimate.
        """
        if self.end_condition == 'distance' and self.target.target == 'pace.zone':
            # Calculate average pace
            target_pace_ms = (self.target.from_value + self.target.to_value) / 2
            # Calculate time needed to cover the distance at the target pace
            end_condition_sec = int(self.parsed_end_condition_value()) / target_pace_ms
            # Round to nearest 10 seconds for better readability
            end_condition_sec = int(round(end_condition_sec/10, 0) * 10)
            # Update end condition
            self.end_condition = 'time'
            self.end_condition_value = f'{end_condition_sec:.0f}'
        elif self.end_condition == 'iterations' and len(self.workout_steps) > 0:
            # Recursively convert sub-steps
            for ws in self.workout_steps:
                ws.dist_to_time()

    def garminconnect_json(self):
        """
        Convert the workout step to Garmin Connect JSON format.
        
        Returns:
            Dictionary representation of the workout step for Garmin Connect API
        """
        base_json = {
            "type": 'RepeatGroupDTO' if self.step_type == 'repeat' else 'ExecutableStepDTO',
            "stepId": None,
            "stepOrder": self.order,
            "childStepId": self.child_step_id,
            "stepType": {
                "stepTypeId": STEP_TYPES[self.step_type],
                "stepTypeKey": self.step_type,
            },
            "endCondition": {
                "conditionTypeKey": self.end_condition,
                "conditionTypeId": END_CONDITIONS[self.end_condition],
            },
            "endConditionValue": self.parsed_end_condition_value(),
        }

        if len(self.workout_steps) > 0:
            base_json["workoutSteps"] = [step.garminconnect_json() for step in self.workout_steps]

        if self.step_type == 'repeat':
            base_json['smartRepeat'] = True
            base_json['numberOfIterations'] = self.end_condition_value
        else:
            base_json.update({
                "description": self.description,
                "preferredEndConditionUnit": self.end_condition_unit(),
                "endConditionCompare": None,
                "endConditionZone": None,
                **self.target.garminconnect_json(),
            })
        return base_json

class Target:
    """
    Represents a target for a workout step.
    
    A target can be pace, speed, heart rate, power, or cadence.
    """
    
    def __init__(self, target="no.target", to_value=None, from_value=None, zone=None):
        """
        Initialize a new target.
        
        Args:
            target: Type of target (e.g., 'pace.zone', 'speed.zone', 'heart.rate.zone')
            to_value: Upper bound of the target range
            from_value: Lower bound of the target range
            zone: Optional zone number (for predefined zones)
        """
        if target not in TARGET_TYPES:
            raise ValueError(f"Unsupported target type: {target}. "
                           f"Must be one of {list(TARGET_TYPES.keys())}")
        
        self.target = target
        self.to_value = to_value
        self.from_value = from_value
        self.zone = zone

    def garminconnect_json(self):
        """
        Convert the target to Garmin Connect JSON format.
        
        Returns:
            Dictionary representation of the target for Garmin Connect API
        """
        return {
            "targetType": {
                "workoutTargetTypeId": TARGET_TYPES[self.target],
                "workoutTargetTypeKey": self.target,
            },
            "targetValueOne": self.to_value,
            "targetValueTwo": self.from_value,
            "zoneNumber": self.zone,
        }