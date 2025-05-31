#!/usr/bin/env bash
# public_resources_map/run.sh
set -e

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# python create_user.py admin admin
# python import_csv.py

export FLASK_APP=app.py
flask run
