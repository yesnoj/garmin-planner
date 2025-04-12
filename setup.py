#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for Garmin Planner.
"""

from setuptools import setup, find_packages
import os
import re

# Get the version from planner/constants.py
with open('planner/constants.py', 'r') as f:
    version_file = f.read()
    version_match = re.search(r"VERSION = ['\"]([^'\"]*)['\"]", version_file)
    if version_match:
        version = version_match.group(1)
    else:
        version = '0.0.0'

# Get the long description from README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Dependencies
REQUIRED = [
    'garth',
    'pyyaml',
    'pandas',
    'openpyxl',
    'tkcalendar',
]

# Optional dependencies
EXTRAS = {
    'dev': [
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'flake8',
    ],
    'gui': [
        'tkcalendar',
    ],
}

setup(
    name='garmin-planner',
    version=version,
    description='A tool for planning and scheduling workouts in Garmin Connect',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Garmin Planner Contributors',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/garmin-planner',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    entry_points={
        'console_scripts': [
            'garmin-planner=garmin_planner:main',
            'garmin-planner-gui=garmin_planner_gui:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires='>=3.6',
    keywords='garmin, workout, planning, scheduling',
    project_urls={
        'Documentation': 'https://github.com/yourusername/garmin-planner',
        'Source': 'https://github.com/yourusername/garmin-planner',
        'Tracker': 'https://github.com/yourusername/garmin-planner/issues',
    },
)