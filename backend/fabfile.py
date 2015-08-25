# coding: utf-8
from __future__ import with_statement
from fabric.api import *
from contextlib import contextmanager as _contextmanager
import os
# LOCAL PATHS
cwd = os.path.dirname(__file__)
SERVER_ROOT = os.environ.get('SERVER_ROOT', 'path_to_server_root')

# Server config
SERVER = os.environ.get('SERVER', 'hostname_or_ip')
DB = os.environ.get('DB', 'dbname')
env.user = os.environ.get('SSH_USER', 'username')

# Role definitions
env.roledefs = {
    'server': [SERVER]
}


@_contextmanager
def rvirtualenv():
    SERVER_VIRTUALENV_PATH = os.path.join(
        SERVER_ROOT,
        'arg/elecciones_arg_2015_paso/backend/.venv'
    )
    with cd(SERVER_VIRTUALENV_PATH):
        with prefix('source bin/activate'):
            yield


@task(alias='dedupe')
@runs_once
def ml_csvlink():
    with lcd(cwd):
        local('scripts/csvlink/run_csvlink.sh')


@task(alias='clean_dedupe')
@runs_once
def clean_csvlink():
    with lcd(cwd):
        local('scripts/csvlink/clean_csvlink_polling.sh')
        local('scripts/csvlink/clean_csvlink_schools.sh')
        local('scripts/csvlink/clean_csvlink_dedupe.sh')
        local('scripts/csvlink/clean_csvlink_weighted.sh')


@task(alias='reset_db')
@runs_once
def reset_database():
    with lcd(cwd):
        local('scripts/DB/create_db.sh')
        local('scripts/DB/create_schema.sh')


@task(alias='reload_data')
@runs_once
def reload_database_data():
    with lcd(cwd):
        local('scripts/DB/load_adm_boundaries.sh')
        local('scripts/DB/load_polling_stations.sh')
        local('scripts/DB/load_schools.sh')
        local('scripts/DB/update_school_sequence.sh')
        local('scripts/DB/load_dedupe_matches.sh')
        local('scripts/DB/load_weighted_matches.sh')


@task(alias='add_sim_results')
@runs_once
def add_similarity_results():
    with lcd(cwd):
        local('python scripts/join_establecimientos_escuelas.py')


@task(alias='getgeodata')
@roles('server')
def get_geo_data():
    local_path = os.path.join(
        cwd,
        'data/geo'
    )
    db_backup_path = os.path.join(
        SERVER_ROOT,
        'db_backup'
    )
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    with lcd(local_path):
        with cd(db_backup_path):
            run('pg_dump -O %s | bzip2 > %s.sql.bz2' %
                (DB, DB))
            get('%s.sql.bz2' % (DB), '.')


# DEFAULT TASK
@task(default=True)
def list_tasks():
    local('fab --list')
