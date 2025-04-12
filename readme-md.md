# Garmin Planner

A comprehensive tool for planning, creating, and scheduling workouts for Garmin Connect. This application helps you manage your training plans, import and export workouts, and schedule them in your Garmin Connect calendar.

## Features

- **Workout Management**: Create, import, export, and delete workouts
- **Schedule Management**: Schedule workouts in your Garmin Connect calendar
- **Excel Integration**: Import workouts from Excel files
- **Workout Editor**: Visual editor for creating and modifying workouts
- **Command-line Interface**: Automate workout management with a powerful CLI
- **Graphical User Interface**: User-friendly GUI for all functionality

## Installation

### Prerequisites

- Python 3.6 or higher
- Garmin Connect account

### Option 1: Install from source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/garmin-planner.git
   cd garmin-planner
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

### Option 2: Install via pip

```bash
pip install garmin-planner
```

## Quick Start

### Initial Setup

1. Log in to your Garmin Connect account:
   ```bash
   garmin-planner login
   ```

2. Create a sample workout file:
   ```bash
   garmin-planner-gui
   ```
   Then use the Excel Tools tab to create a sample Excel file.

### Command-line Interface

```bash
# Import workouts from a YAML file
garmin-planner import --workouts-file my_workouts.yaml

# Export workouts
garmin-planner export --export-file my_workouts.yaml

# Schedule workouts
garmin-planner schedule --training-plan MY_PLAN --race-day 2023-12-31 --workout-days 1,3,5

# List scheduled workouts
garmin-planner list --date-range CURRENT-MONTH

# Unschedule workouts
garmin-planner unschedule --training-plan MY_PLAN
```

### Graphical User Interface

1. Start the GUI:
   ```bash
   garmin-planner-gui
   ```

2. Use the tabs to:
   - Log in to Garmin Connect
   - Import workouts from YAML files
   - Export workouts
   - Schedule workouts
   - Manage workout plans
   - Create and edit workouts visually

## Workout Format

Workouts can be defined in YAML format:

```yaml
config:
  name_prefix: "MY_PLAN_"
  paces:
    Z1: "6:30"
    Z2: "6:00"
    Z3: "5:30"
    Z4: "5:00"
    Z5: "4:30"
  heart_rates:
    max_hr: 180
    Z1: "60-70% max_hr"
    Z2: "70-80% max_hr"
    Z3: "80-90% max_hr"
    Z4: "90-95% max_hr"
    Z5: "95-100% max_hr"
  margins:
    faster: "0:05"
    slower: "0:05"
    hr_up: 5
    hr_down: 5

W01S01 Easy Run: # Easy run to start
  - warmup: 10min @ Z1
  - interval: 20min @ Z2
  - cooldown: 5min @ Z1

W01S02 Intervals:
  - warmup: 15min @ Z1
  - repeat: 5
    steps:
      - interval: 400m @ Z5
      - recovery: 2min @ Z1
  - cooldown: 10min @ Z1
```

## Excel Format

You can also define workouts in Excel format and convert them to YAML. Use the Excel Tools tab in the GUI to create a sample Excel file that demonstrates the expected format.

## Step Types

The following step types are supported:

- `warmup`: Warm-up period before the main workout
- `cooldown`: Cool-down period after the main workout
- `interval`: Main workout interval
- `recovery`: Recovery period between intervals
- `rest`: Rest period (no activity)
- `repeat`: Group of steps to repeat multiple times

## Target Types

The following target types are supported:

- Pace zones: `@ Z1`, `@ Z2`, etc. (configured in the `paces` section)
- Heart rate zones: `@hr Z1`, `@hr Z2`, etc. (configured in the `heart_rates` section)
- Distance-based: `3km in 15:00` (sets a pace based on the distance and time)
- Exact values: `@ 5:00` (5 minutes per kilometer pace)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Garth](https://github.com/matin/garth) for the Garmin Connect API wrapper
