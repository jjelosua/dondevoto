# coding: utf-8
from __future__ import with_statement
from fabric.api import *
import os
# LOCAL PATHS
cwd = os.path.dirname(__file__)


@task(alias='dedupe')
@runs_once
def ml_csvlink():
    with lcd(cwd):
        local('scripts/csvlink/run_csvlink.sh')


@task(alias='regenerate')
@runs_once
def regenerate_data():
    with lcd(cwd):
        local('scripts/DB/create_db.sh')
        local('scripts/DB/create_schema.sh')
        local('scripts/DB/load_adm_boundaries.sh')
        local('scripts/DB/load_polling_stations.sh')
        local('scripts/DB/load_schools.sh')
        local('scripts/DB/update_school_sequence.sh')
        local('scripts/csvlink/clean_csvlink_dedupe.sh')
        local('scripts/DB/load_dedupe_matches.sh')
        local('scripts/csvlink/clean_csvlink_weighted.sh')
        local('scripts/DB/load_weighted_matches.sh')
        local('python scripts/join_establecimientos_escuelas.py')


# DEFAULT TASK
@task(default=True)
def list_tasks():
    local('fab --list')
