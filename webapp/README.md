Frontend usage
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

5. Create DATABASE_URL environment variable to connect to the DB created in the backend

        ```
        export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'
        ```

4. Run gunicorn locally

        $ gunicorn dondevoto:app

5. Patience and happy geocoding!!

## Implementation notes

* It's always a good practice to create a DB backup periodically so that you have something to hold on to if someone messes things up badly. For example with cron

        ```
        0 8 * * 1 pg_dump -O dbname | bzip2 > /home/user/db_backup/dbname.$(/bin/date +\%Y\%m\%d).sql.bz2
        ```