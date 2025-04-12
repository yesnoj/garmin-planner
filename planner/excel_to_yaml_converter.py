#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel to YAML Converter for Garmin Planner with Scheduling Support

This module converts a structured Excel file into a YAML file compatible with garmin-planner.
It includes support for a Date column with workout scheduling.
"""

import pandas as pd
import yaml
import re
import os
import sys
import copy
from datetime import datetime
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Customize YAML dumper to avoid references/aliases
class NoAliasDumper(yaml.SafeDumper):
    """Custom YAML dumper that ignores aliases"""
    def ignore_aliases(self, data):
        return True

# Valid step types supported by garmin-planner
VALID_STEP_TYPES = {"warmup", "cooldown", "interval", "recovery", "rest", "repeat", "other"}

def excel_to_yaml(excel_file, output_file=None):
    """
    Convert a structured Excel file to a YAML file compatible with garmin-planner.
    
    Args:
        excel_file: Path to the input Excel file
        output_file: Path to the output YAML file (optional)
        
    Returns:
        Dictionary containing the parsed workout plan
        
    Raises:
        ValueError: If the Excel file has invalid structure
    """
    # Create output file name if not specified
    if output_file is None:
        output_file = os.path.splitext(excel_file)[0] + '.yaml'
    
    logging.info(f"Converting {excel_file} to {output_file}...")
    
    # Load the Excel file
    try:
        # Try to read with headers in the second row
        df = pd.read_excel(excel_file, sheet_name='Workouts', header=1)
        
        # Verify required columns exist
        required_cols = ['Week', 'Session', 'Description', 'Steps']
        if are_required_columns_present(df, required_cols):
            logging.info("'Workouts' sheet found with headers in the second row.")
        else:
            # Try alternative header positions or handle missing columns
            df = handle_missing_columns(excel_file, required_cols)
        
        # Get the ExcelFile object for reading other sheets
        xls = pd.ExcelFile(excel_file)
        
    except Exception as e:
        raise ValueError(f"Error loading 'Workouts' sheet: {str(e)}")
    
    # Dictionary to hold the complete plan
    plan = {
        'config': {
            'heart_rates': {},
            'paces': {},
            'margins': {
                'faster': '0:03',
                'slower': '0:03',
                'hr_up': 5,
                'hr_down': 5
            },
            'name_prefix': ''
        }
    }
    
    # Extract configuration information
    plan = extract_config(xls, plan)
    
    # Extract paces
    plan = extract_paces(xls, plan)
    
    # Extract heart rates
    plan = extract_heart_rates(xls, plan)
    
    # Dictionary to store workout descriptions for comments
    workout_descriptions = {}
    
    # Process workouts from the DataFrame
    for _, row in df.iterrows():
        # Skip rows with missing required data
        if pd.isna(row['Week']) or pd.isna(row['Session']) or pd.isna(row['Description']) or pd.isna(row['Steps']):
            continue
        
        # Extract data
        week = str(int(row['Week'])).zfill(2)  # Format as 01, 02, etc.
        session = str(int(row['Session'])).zfill(2)
        description = str(row['Description']).strip()
        
        # Create the full workout name (without date information)
        full_name = f"W{week}S{session} {description}"
        
        # Store the description for comments
        workout_descriptions[full_name] = description
        
        # Extract workout steps
        steps_str = str(row['Steps']).strip()
        
        # Parse workout steps
        workout_steps = parse_workout_steps(steps_str, full_name)
        
        # Add the workout to the plan (without date in the name)
        plan[full_name] = workout_steps
    
    # Save the plan as YAML
    with open(output_file, 'w', encoding='utf-8') as f:
        # Use NoAliasDumper to avoid YAML references
        yaml.dump(plan, f, default_flow_style=False, sort_keys=False, Dumper=NoAliasDumper)
    
    logging.info(f"Conversion completed! YAML file saved to: {output_file}")
    
    # Add comments to the YAML file for workout descriptions
    add_comments_to_yaml(output_file, workout_descriptions)
    
    return plan

def are_required_columns_present(df, required_cols):
    """
    Check if all required columns are present in the DataFrame.
    
    Args:
        df: DataFrame to check
        required_cols: List of required column names
        
    Returns:
        True if all required columns are present, False otherwise
    """
    return all(col in df.columns for col in required_cols)

def handle_missing_columns(excel_file, required_cols):
    """
    Handle missing columns by trying different header positions or case-insensitive matching.
    
    Args:
        excel_file: Path to the Excel file
        required_cols: List of required column names
        
    Returns:
        DataFrame with corrected columns
        
    Raises:
        ValueError: If required columns cannot be found
    """
    try:
        # Try reading with header in the first row
        df = pd.read_excel(excel_file, sheet_name='Workouts', header=0)
        
        if are_required_columns_present(df, required_cols):
            logging.info("'Workouts' sheet found with headers in the first row.")
            return df
            
        # Try case-insensitive matching
        df_cols_lower = [col.lower() for col in df.columns]
        missing = []
        
        for req_col in required_cols:
            if req_col.lower() not in df_cols_lower:
                missing.append(req_col)
        
        if missing:
            raise ValueError(f"Missing columns in 'Workouts' sheet: {', '.join(missing)}")
        
        # Rename columns for consistency
        rename_map = {}
        for col in df.columns:
            for req_col in required_cols:
                if col.lower() == req_col.lower():
                    rename_map[col] = req_col
        
        df = df.rename(columns=rename_map)
        logging.info("Columns renamed for consistency.")
        return df
        
    except Exception as e:
        raise ValueError(f"Error finding required columns: {str(e)}")

def extract_config(xls, plan):
    """
    Extract configuration information from the Config sheet.
    
    Args:
        xls: ExcelFile object
        plan: Plan dictionary to update
        
    Returns:
        Updated plan dictionary
    """
    if 'Config' in xls.sheet_names:
        try:
            config_df = pd.read_excel(xls, 'Config', header=0)
            
            # Extract name prefix (if present)
            name_prefix_rows = config_df[config_df.iloc[:, 0] == 'name_prefix']
            if not name_prefix_rows.empty:
                # Ensure the prefix ends with a space
                prefix = str(name_prefix_rows.iloc[0, 1]).strip()
                # Add a space at the end if not already there
                if prefix and not prefix.endswith(' '):
                    prefix = prefix + ' '
                plan['config']['name_prefix'] = prefix
            
            # Extract margins (if present)
            margins_rows = config_df[config_df.iloc[:, 0] == 'margins']
            if not margins_rows.empty:
                # Check if there are values for the margins
                if pd.notna(margins_rows.iloc[0, 1]):
                    plan['config']['margins']['faster'] = str(margins_rows.iloc[0, 1]).strip()
                if pd.notna(margins_rows.iloc[0, 2]):
                    plan['config']['margins']['slower'] = str(margins_rows.iloc[0, 2]).strip()
                if pd.notna(margins_rows.iloc[0, 3]):
                    plan['config']['margins']['hr_up'] = int(margins_rows.iloc[0, 3])
                if pd.notna(margins_rows.iloc[0, 4]):
                    plan['config']['margins']['hr_down'] = int(margins_rows.iloc[0, 4])
        except Exception as e:
            logging.warning(f"Error extracting configuration: {str(e)}")
    
    return plan

def extract_paces(xls, plan):
    """
    Extract pace information from the Paces sheet.
    
    Args:
        xls: ExcelFile object
        plan: Plan dictionary to update
        
    Returns:
        Updated plan dictionary
    """
    if 'Paces' in xls.sheet_names:
        try:
            paces_df = pd.read_excel(xls, 'Paces', header=0)
            
            for _, row in paces_df.iterrows():
                # Ensure both name and value are present
                if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    name = str(row.iloc[0]).strip()
                    value = str(row.iloc[1]).strip()
                    plan['config']['paces'][name] = value
        except Exception as e:
            logging.warning(f"Error extracting paces: {str(e)}")
    
    return plan

def extract_heart_rates(xls, plan):
    """
    Extract heart rate information from the HeartRates sheet.
    
    Args:
        xls: ExcelFile object
        plan: Plan dictionary to update
        
    Returns:
        Updated plan dictionary
    """
    if 'HeartRates' in xls.sheet_names:
        try:
            hr_df = pd.read_excel(xls, 'HeartRates', header=0)
            
            for _, row in hr_df.iterrows():
                # Ensure both name and value are present
                if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    name = str(row.iloc[0]).strip()
                    value = row.iloc[1]
                    
                    # Convert numeric values to integers
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        value = int(value)
                    elif isinstance(value, str) and value.strip().isdigit():
                        value = int(value.strip())
                    else:
                        value = str(value).strip()
                        
                    plan['config']['heart_rates'][name] = value
        except Exception as e:
            logging.warning(f"Error extracting heart rates: {str(e)}")
    
    return plan

def add_comments_to_yaml(yaml_file, descriptions):
    """
    Add comments to the YAML file for workout descriptions.
    
    Args:
        yaml_file: Path to the YAML file
        descriptions: Dictionary with workout names and their descriptions
    """
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add comments for each workout
        for workout_name, description in descriptions.items():
            # Find the line with the workout name
            pattern = f"^{re.escape(workout_name)}:"
            content = re.sub(pattern, f"{workout_name}: # {description}", content, flags=re.MULTILINE)
        
        # Write the updated content
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logging.info("Comments added to YAML file")
    except Exception as e:
        logging.warning(f"Error adding comments to YAML: {str(e)}")

def parse_workout_steps(steps_str, workout_name):
    """
    Parse a string of steps into a structured list.
    
    Args:
        steps_str: String containing the workout steps
        workout_name: Name of the workout (for error messages)
        
    Returns:
        List of structured workout steps
    """
    # Prepare the list of steps
    workout_steps = []
    
    # Replace semicolons with newlines for uniform processing
    steps_str = steps_str.replace(';', '\n')
    
    # Split steps by lines
    step_lines = steps_str.split('\n')
    i = 0
    
    # Process each line
    while i < len(step_lines):
        step_str = step_lines[i].strip()
        if not step_str:
            i += 1
            continue
        
        # Identify step type and details
        step_parts = step_str.split(':')
        if len(step_parts) < 2:
            logging.warning(f"Invalid step format in {workout_name}: {step_str}")
            i += 1
            continue
        
        step_type = step_parts[0].strip().lower()
        step_details = ':'.join(step_parts[1:]).strip()
        
        # Verify step type is valid for garmin-planner
        if step_type not in VALID_STEP_TYPES:
            if step_type == "steady":
                logging.warning(f"'steady' is not supported in garmin-planner. Converted to 'interval' in {workout_name}")
                step_type = "interval"
            else:
                logging.warning(f"Step type '{step_type}' not recognized in {workout_name}, converted to 'other'")
                step_type = "other"
        
        # Check if this is a repeat step
        repeat_match = re.match(r'^repeat\s+(\d+)$', step_type)
        if repeat_match:
            iterations = int(repeat_match.group(1))
            
            # Extract steps within the repeat
            substeps = []
            i += 1  # Move to the next line
            
            # Collect all indented steps after the repeat
            while i < len(step_lines):
                substep_str = step_lines[i].strip()
                if not substep_str:
                    i += 1
                    continue
                
                # If the line doesn't start with spaces or tabs, it's not part of the repeat
                if not step_lines[i].startswith((' ', '\t')):
                    break
                
                # Identify the substep type and details
                substep_parts = substep_str.split(':')
                if len(substep_parts) < 2:
                    logging.warning(f"Invalid substep format in {workout_name}: {substep_str}")
                    i += 1
                    continue
                
                substep_type = substep_parts[0].strip().lower()
                substep_details = ':'.join(substep_parts[1:]).strip()
                
                # Verify substep type is valid
                if substep_type not in VALID_STEP_TYPES:
                    if substep_type == "steady":
                        logging.warning(f"'steady' not supported in garmin-planner. Converted to 'interval' in {workout_name}")
                        substep_type = "interval"
                    else:
                        logging.warning(f"Substep type '{substep_type}' not recognized in {workout_name}, converted to 'other'")
                        substep_type = "other"
                
                # Handle cooldown inside repeat (likely an error)
                if substep_type == "cooldown":
                    logging.warning(f"'cooldown' found inside a repeat in {workout_name}. Moved outside.")
                    # Save the cooldown for later
                    cooldown_details = substep_details
                    i += 1
                    # Add the repeat step with its substeps
                    # Correct format for garmin-planner: 'repeat' key and iterations value
                    repeat_step = {"repeat": iterations, "steps": copy.deepcopy(substeps)}
                    workout_steps.append(repeat_step)
                    # Add the cooldown as a separate step
                    workout_steps.append({"cooldown": cooldown_details})
                    break  # Exit the substep loop
                
                substeps.append({substep_type: substep_details})
                i += 1
            
            # If the loop ended normally, add the repeat step
            if i >= len(step_lines) or not step_lines[i].startswith((' ', '\t')):
                # Correct format for garmin-planner: 'repeat' key and iterations value
                repeat_step = {"repeat": iterations, "steps": copy.deepcopy(substeps)}
                workout_steps.append(repeat_step)
        else:
            # Add a normal step
            workout_steps.append({step_type: step_details})
            i += 1
    
    return workout_steps

def auto_adjust_column_widths(worksheet):
    """
    Automatically adjust column widths based on content.
    
    Args:
        worksheet: openpyxl worksheet object
    """
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        
        for cell in column:
            if cell.value:
                cell_length = len(str(cell.value))
                max_length = max(max_length, cell_length)
        
        adjusted_width = max(max_length + 2, 8)  # Add some extra space
        worksheet.column_dimensions[column_letter].width = min(adjusted_width, 60)  # Limit to 60 to avoid too wide columns

def create_sample_excel(output_file='sample_training_plan.xlsx'):
    """
    Create a sample Excel file with the expected structure for the training plan.
    Includes support for a Date column.
    
    Args:
        output_file: Path for the output Excel file
        
    Returns:
        Path to the created Excel file, or None if there was an error
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        logging.error("ERROR: openpyxl library is not installed.")
        logging.error("Install openpyxl with: pip install openpyxl")
        return None
    
    logging.info(f"Creating sample Excel file: {output_file}")
    
    wb = openpyxl.Workbook()
    
    # Define a thin border style
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Config sheet
    config_sheet = wb.active
    config_sheet.title = 'Config'
    
    # Config sheet headers
    config_sheet['A1'] = 'Parameter'
    config_sheet['B1'] = 'Value'
    config_sheet['C1'] = 'Slower'
    config_sheet['D1'] = 'HR Up'
    config_sheet['E1'] = 'HR Down'
    
    # Config sheet values
    config_sheet['A2'] = 'name_prefix'
    config_sheet['B2'] = 'MYRUN_'
    
    config_sheet['A3'] = 'margins'
    config_sheet['B3'] = '0:03'  # faster
    config_sheet['C3'] = '0:03'  # slower
    config_sheet['D3'] = 5       # hr_up
    config_sheet['E3'] = 5       # hr_down
    
    # Format header
    header_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
    for col in ['A', 'B', 'C', 'D', 'E']:
        config_sheet[f'{col}1'].font = Font(bold=True)
        config_sheet[f'{col}1'].fill = header_fill
    
    # Paces sheet (Z1-Z5 zones)
    paces_sheet = wb.create_sheet(title='Paces')
    
    paces_sheet['A1'] = 'Name'
    paces_sheet['B1'] = 'Value'
    
    paces_sheet['A2'] = 'Z1'
    paces_sheet['B2'] = '6:30'
    
    paces_sheet['A3'] = 'Z2'
    paces_sheet['B3'] = '6:20'
    
    paces_sheet['A4'] = 'Z3'
    paces_sheet['B4'] = '6:00'
    
    paces_sheet['A5'] = 'Z4'
    paces_sheet['B5'] = '5:20'
    
    paces_sheet['A6'] = 'Z5'
    paces_sheet['B6'] = '4:50'
    
    # Format header
    for col in ['A', 'B']:
        paces_sheet[f'{col}1'].font = Font(bold=True)
        paces_sheet[f'{col}1'].fill = header_fill
    
    # HeartRates sheet (Z1-Z5 zones)
    hr_sheet = wb.create_sheet(title='HeartRates')
    
    hr_sheet['A1'] = 'Name'
    hr_sheet['B1'] = 'Value'
    
    # Example of using max_hr with percentages
    hr_sheet['A2'] = 'max_hr'
    hr_sheet['B2'] = 198  # Use an integer instead of a string
    
    hr_sheet['A3'] = 'Z1'
    hr_sheet['B3'] = '62-76% max_hr'
    
    hr_sheet['A4'] = 'Z2'
    hr_sheet['B4'] = '76-85% max_hr'
    
    hr_sheet['A5'] = 'Z3'
    hr_sheet['B5'] = '85-91% max_hr'
    
    hr_sheet['A6'] = 'Z4'
    hr_sheet['B6'] = '91-95% max_hr'
    
    hr_sheet['A7'] = 'Z5'
    hr_sheet['B7'] = '95-100% max_hr'
    
    # Format header
    for col in ['A', 'B']:
        hr_sheet[f'{col}1'].font = Font(bold=True)
        hr_sheet[f'{col}1'].fill = header_fill
    
    # Single Workouts sheet for all workouts
    workouts_sheet = wb.create_sheet(title='Workouts')
    
    # Add a row for the athlete's name
    # Create a merged cell for the athlete's name
    workouts_sheet.merge_cells('A1:E1')
    athlete_cell = workouts_sheet['A1']
    athlete_cell.value = "Athlete: "  # Prepared to be filled in
    athlete_cell.alignment = Alignment(horizontal='center', vertical='center')
    athlete_cell.font = Font(size=12, bold=True)
    # Add border to the athlete cell
    athlete_cell.border = thin_border

    # Headers in row 2
    workouts_sheet['A2'] = 'Week'
    workouts_sheet['B2'] = 'Date'
    workouts_sheet['C2'] = 'Session'
    workouts_sheet['D2'] = 'Description'
    workouts_sheet['E2'] = 'Steps'

    # Format header
    for col in ['A', 'B', 'C', 'D', 'E']:
        cell = workouts_sheet[f'{col}2']
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.border = thin_border  # Add border to all header cells
    
    # Add some example workouts (using ONLY supported step types)
    workouts = [
        # Week, Session, Description, Steps
        (1, 1, 'Easy run', 'warmup: 10min @ Z1; interval: 30min @ Z2; cooldown: 5min @ Z1'),
        (1, 2, 'Short intervals', 'warmup: 15min @ Z1; repeat 5:\n  interval: 400m @ Z5\n  recovery: 2min @ Z1; cooldown: 10min @ Z1'),
        (1, 3, 'Long slow run', 'warmup: 10min @ Z1; interval: 45min @ Z2; cooldown: 5min @ Z1'),
        (2, 1, 'Recovery run', 'interval: 30min @ Z1'),
        (2, 2, 'Threshold run', 'warmup: 15min @ Z1; interval: 20min @ Z4; cooldown: 10min @ Z1'),
        (2, 3, 'Progressive long run', 'warmup: 10min @ Z1; interval: 30min @ Z2; interval: 20min @ Z3; cooldown: 10min @ Z1')
    ]
    
    # Define alternating colors for weeks
    week_colors = [
        "FFF2CC",  # Light yellow
        "DAEEF3",  # Light blue
        "E2EFDA",  # Light green
        "FCE4D6",  # Light orange
        "EAD1DC",  # Light pink
        "D9D9D9",  # Light gray
    ]
    
    # Add workouts to the sheet
    current_week = None
    current_color_index = 0
    
    for i, (week, session, description, steps) in enumerate(workouts, start=3):  # Start from row 3 (after header and athlete row)
        # If the week changes, change the color
        if week != current_week:
            current_week = week
            current_color_index = (current_color_index + 1) % len(week_colors)
            
        # Background color for the current row
        row_fill = PatternFill(start_color=week_colors[current_color_index], 
                              end_color=week_colors[current_color_index], 
                              fill_type="solid")
        
        # Assign values to cells
        workouts_sheet[f'A{i}'] = week
        workouts_sheet[f'B{i}'] = None  # Empty Date column to be filled by Plan function
        workouts_sheet[f'C{i}'] = session
        workouts_sheet[f'D{i}'] = description
        workouts_sheet[f'E{i}'] = steps
        
        # Apply background color and border to all cells in the row
        for col in ['A', 'B', 'C', 'D', 'E']:
            cell = workouts_sheet[f'{col}{i}']
            cell.fill = row_fill
            cell.border = thin_border
            
            # Set text wrapping and alignment
            cell.alignment = Alignment(wrapText=True, vertical='top')
        
        # Calculate appropriate row height based on content
        # Count lines of text in steps (both \n and ;)
        num_lines = 1 + steps.count('\n') + steps.count(';')
        
        # Consider indentation for repeats
        if 'repeat' in steps and '\n' in steps:
            # Count indented lines after repeat
            lines_after_repeat = steps.split('repeat')[1].count('\n')
            if lines_after_repeat > 0:
                num_lines += lines_after_repeat - 1  # -1 because the line with 'repeat' is already counted
        
        # Minimum height plus height for each line of text (about 15 points per line)
        row_height = max(15, 12 * num_lines)
        workouts_sheet.row_dimensions[i].height = row_height
    
    # Set column widths
    workouts_sheet.column_dimensions['A'].width = 10  # Week
    workouts_sheet.column_dimensions['B'].width = 15  # Date
    workouts_sheet.column_dimensions['C'].width = 10  # Session
    workouts_sheet.column_dimensions['D'].width = 25  # Description
    workouts_sheet.column_dimensions['E'].width = 60  # Steps
    
    # Automatically adjust column widths in Config, Paces, and HR sheets
    auto_adjust_column_widths(config_sheet)
    auto_adjust_column_widths(paces_sheet)
    auto_adjust_column_widths(hr_sheet)
    
    # Save the file
    wb.save(output_file)
    logging.info(f"Sample Excel file created: {output_file}")
    return output_file

def main():
    """Main function for command line use"""
    # Define command line arguments
    parser = argparse.ArgumentParser(description='Convert an Excel file to a YAML file for garmin-planner')
    parser.add_argument('--excel', '-e', help='Path to the input Excel file', default='')
    parser.add_argument('--output', '-o', help='Path to the output YAML file (optional)')
    parser.add_argument('--create-sample', '-s', action='store_true', help='Create a sample Excel file')
    parser.add_argument('--sample-name', help='Name for the sample Excel file', default='sample_training_plan.xlsx')
    
    args = parser.parse_args()
    
    # Create a sample file if requested
    if args.create_sample:
        sample_file = create_sample_excel(args.sample_name)
        if sample_file:
            # If specified --excel, immediately convert the sample file
            if args.excel == '':
                args.excel = sample_file
    
    # Verify that an input file is specified
    if not args.excel:
        logging.error("ERROR: You must specify an input Excel file (--excel)")
        logging.info("Use --create-sample to create a sample file")
        parser.print_help()
        return
    
    # Verify that the Excel file exists
    if not os.path.exists(args.excel):
        logging.error(f"ERROR: File {args.excel} does not exist")
        return
    
    # Convert the Excel file to YAML
    try:
        excel_to_yaml(args.excel, args.output)
        logging.info("Operation completed successfully!")
    except Exception as e:
        logging.error(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()