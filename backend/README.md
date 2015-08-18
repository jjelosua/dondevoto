Backend usage
=============

## Requirements
* Have postgreSQL 9.x with postgis extension installed locally
* Python 2.7.\* && virtualenv && pip installed 

## Process
1. Create a virtualenv

        $ virtualenv .venv

2. Activate the created virtualenv

        $ source .venv/bin/activate

3. Install dependencies

        $ pip install -r requirements.txt

4. Generate input datasets for the dedupe process and then run

        $ fab dedupe

5. Create DATABASE_URL environment variable to connect to the DB created in the previous step 

6. Once we have trained and launched the ML algorithm create the DB and load the data

        $ fab regenerate

## Implementation notes

* Some parameters inside the csvlink process can be tweaked to balance precission or recall take a look at their [documentation](http://dedupe.readthedocs.org/en/latest/)