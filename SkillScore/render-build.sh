#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Initialize the database if it doesn't exist
# This script is often used to run migrations too
python init_db.py
