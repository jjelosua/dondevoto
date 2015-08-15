# coding: utf-8
from __future__ import with_statement
from fabric.api import *
from contextlib import contextmanager as _contextmanager
import os

# REMOTE PATHS
SERVER_ROOT = os.environ.get('SERVER_ROOT', 'path_to_server_root')
SERVER_PROJECT_PATH = os.path.join(
    SERVER_ROOT,
    'arg/elecciones_arg_2015_paso'
)
SERVER_VIRTUALENV_PATH = os.path.join(
    SERVER_ROOT,
    'arg/elecciones_arg_2015_paso/backend/.venv'
)
SERVER_OUTPUT_PATH = os.path.join(
    SERVER_ROOT,
    'arg/paso/json_files'
)
SERVER_DICT_PATH = os.path.join(
    SERVER_ROOT,
    'arg/paso/dicts'
)
SERVER_BSAS_OUTPUT_PATH = os.path.join(
    SERVER_ROOT,
    'bsas/paso/json_files'
)
SERVER_BSAS_DICT_PATH = os.path.join(
    SERVER_ROOT,
    'bsas/paso/dicts'
)
SERVER_ZIP_PATH = os.path.join(
    SERVER_ROOT,
    'arg/paso/zip_files'
)

# LOCAL PATHS
cwd = os.path.dirname(__file__)
SIM_DATA_BSAS_PATH = os.path.join(cwd, 'data/output_sim/bsas')

# Server config
SERVER20 = os.environ.get('SERVER20', 'hostname_or_ip_1')
SERVER24 = os.environ.get('SERVER24', 'hostname_or_ip_2')
env.user = os.environ.get('SSH_USER', 'username')
SAMBA_LOCAL_USER = os.environ.get('SAMBA_LOCAL_USER', 'username')
SAMBA_MNT10 = os.environ.get('SAMBA_MNT10',
                             "smb://'DOMAIN;user':pass@SERVER/dir")
SAMBA_MNT11 = os.environ.get('SAMBA_MNT11',
                             "smb://'DOMAIN;user':pass@SERVER/dir")


# Role definitions
env.roledefs = {
    'server20': [SERVER20],
    'server24': [SERVER24],
    'servers': [SERVER20, SERVER24],
}


# CONTEXT MANAGERS
@_contextmanager
def lvirtualenv():
    LOCAL_VIRTUALENV_PATH = os.path.join(
        cwd,
        '.venv'
    )
    with lcd(LOCAL_VIRTUALENV_PATH):
        with prefix('source bin/activate'):
            yield


@_contextmanager
def rvirtualenv():
    SERVER_VIRTUALENV_PATH = os.path.join(
        SERVER_ROOT,
        'arg/elecciones_arg_2015_paso/backend/.venv'
    )
    with cd(SERVER_VIRTUALENV_PATH):
        with prefix('source bin/activate'):
            yield


# SIMULATION TASKS
@task
@runs_once
def generate_sim_data():
    with lvirtualenv():
        local('python scripts/generate_sim_data.py')


@task
@runs_once
def local_sim_run():
    with lvirtualenv():
        local('python scripts/paso_agosto.py -s')


@task(alias='run_simdata')
@runs_once
def new_simulation():
    with lvirtualenv():
        execute(generate_sim_data)
        execute(local_sim_run)


# DEPLOY TO ESPECIALES PRODUCCION
@task
@runs_once
def deploy_esp10():
    local_path = os.path.join(
        cwd,
        'mnt10'
    )
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    local('sudo -u %s mount_smbfs \
          %s/15/elecciones/test_fabric %s'
          % (SAMBA_LOCAL_USER, SAMBA_MNT10, local_path))
    with lcd(cwd):
        local('cp -v -r %s %s'
              % ('../build/*',
                 'mnt10'))


@task
@runs_once
def deploy_esp11():
    local_path = os.path.join(
        cwd,
        'mnt11'
    )
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    local('sudo -u %s mount_smbfs \
          %s/15/elecciones/test_fabric %s'
          % (SAMBA_LOCAL_USER, SAMBA_MNT11, local_path))
    with lcd(cwd):
        local('cp -v -r %s %s'
              % ('../build/*',
                 'mnt11'))


@task(alias='umount_esp')
@runs_once
def umount_especiales():
    with lcd(cwd):
        local('umount mnt10')
        local('umount mnt11')


@task(alias='deploy_especiales')
@runs_once
def deploy_especiales():
    execute(umount_especiales)
    execute(deploy_esp10)
    execute(deploy_esp11)


# PROCESS RESULTS TASK
@task(alias='run')
@runs_once
def local_run():
    with lvirtualenv():
        local('python scripts/paso_agosto.py')


@task(alias='run20')
@roles('server20')
def remote20_run():
    with rvirtualenv():
        run('python scripts/paso_agosto.py')


@task(alias='run24')
@roles('server24')
def remote24_run():
    with rvirtualenv():
        run('python scripts/paso_agosto.py')


@task(alias='run20debug')
@roles('server20')
def remote20_run_debug():
    with rvirtualenv():
        run('python scripts/paso_agosto.py -d')


@task(alias='run24debug')
@roles('server24')
def remote24_run_debug():
    with rvirtualenv():
        run('python scripts/paso_agosto.py -d')


# COPY SIMULATED DATA TO SERVERS FOR TESTING PURPOSES
@task
@roles('servers')
def cp_simdata(lrel_path='data/output_sim', rrel_path='arg/paso/json_files'):
    INPUT_PATH = os.path.join(
        cwd,
        lrel_path
    )
    OUTPUT_PATH = os.path.join(
        SERVER_ROOT,
        rrel_path
    )
    run('mkdir -p %s' % (OUTPUT_PATH))

    with lcd(INPUT_PATH):
        put('*.json', OUTPUT_PATH)


@task
@roles('servers')
def cp_simdata_bsas():
    with lcd(SIM_DATA_BSAS_PATH):
        put('*.json', JSON_BSAS_OUTPUT_PATH)


@task(alias='cp_simdata')
def cp_simdata_all():
    execute(cp_simdata)
    execute(cp_simdata_bsas)


# RETRIEVE ELECTION RESULTS FROM SERVER
@task
@roles('server20')
@parallel(pool_size=2)
def remote20_get_data():
    local_path = os.path.join(cwd, 'data/output_prod/s20/')
    local_path_bsas = os.path.join(cwd, 'data/output_prod/s20/bsas/')
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    if not os.path.exists(local_path_bsas):
        os.makedirs(local_path_bsas)
    with cd(JSON_OUTPUT_PATH):
        with lcd(local_path):
            get('*.json', '.')
    with cd(JSON_BSAS_OUTPUT_PATH):
        with lcd(local_path_bsas):
            get('*.json', '.')


@task
@roles('server24')
def remote24_get_data():
    local_path = os.path.join(cwd, 'data/output_prod/s24/')
    local_path_bsas = os.path.join(cwd, 'data/output_prod/s24/bsas/')
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    if not os.path.exists(local_path_bsas):
        os.makedirs(local_path_bsas)
    with cd(JSON_OUTPUT_PATH):
        with lcd(local_path):
            get('*.json', '.')
    with cd(JSON_BSAS_OUTPUT_PATH):
        with lcd(local_path_bsas):
            get('*.json', '.')


@task(alias='rdata')
def remote_get_data_all():
    # get('.ssh/id_lnmachine_rsa.pub', cwd)
    execute(remote20_get_data)
    execute(remote24_get_data)


# RETRIEVE DATA DICTIONARIES FROM SERVER
@task
@roles('server20')
def remote20_get_dict():
    local_path = os.path.join(cwd, 'data/output_prod/s20/dict')
    local_path_bsas = os.path.join(cwd, 'data/output_prod/s20/bsas/dict')
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    if not os.path.exists(local_path_bsas):
        os.makedirs(local_path_bsas)
    with cd(DATA_DICT_PATH):
        with lcd(local_path):
            get('*.json', '.')
    with cd(BSAS_DATA_DICT_PATH):
        with lcd(local_path_bsas):
            get('*.json', '.')


@task
@roles('server24')
def remote24_get_dict():
    local_path = os.path.join(cwd, 'data/output_prod/s24/dict')
    local_path_bsas = os.path.join(cwd, 'data/output_prod/s24/bsas/dict')
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    if not os.path.exists(local_path_bsas):
        os.makedirs(local_path_bsas)
    with cd(DATA_DICT_PATH):
        with lcd(local_path):
            get('*.json', '.')
    with cd(BSAS_DATA_DICT_PATH):
        with lcd(local_path_bsas):
            get('*.json', '.')


@task(alias='r_get_dict')
def remote_get_dict_all():
    # get('.ssh/id_lnmachine_rsa.pub', cwd)
    execute(remote20_get_dict)
    execute(remote24_get_dict)


# DEPLOY DATA DICTIONARIES TO SERVERS
@task
@roles('server20')
def remote20_put_dict():
    local_path = os.path.join(cwd, 'data/output_prod/s20/dict')
    local_path_bsas = os.path.join(cwd, 'data/output_prod/s20/bsas/dict')
    with cd(DATA_DICT_PATH):
        with lcd(local_path):
            put('*.json', '.')
    with cd(BSAS_DATA_DICT_PATH):
        with lcd(local_path_bsas):
            put('*.json', '.')


@task
@roles('server24')
def remote24_put_dict():
    local_path = os.path.join(cwd, 'data/output_prod/s24/dict')
    local_path_bsas = os.path.join(cwd, 'data/output_prod/s24/bsas/dict')
    with cd(DATA_DICT_PATH):
        with lcd(local_path):
            put('*.json', '.')
    with cd(BSAS_DATA_DICT_PATH):
        with lcd(local_path_bsas):
            put('*.json', '.')


@task(alias='r_put_dict')
def remote_put_dict_all():
    # get('.ssh/id_lnmachine_rsa.pub', cwd)
    execute(remote20_put_dict)
    execute(remote24_put_dict)


# Retrieve zip files
@task
@roles('server20')
def remote20_get_zip():
    local_path = os.path.join(cwd, 'data/output_prod/zipfiles/')
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    with cd(PROD_ZIP_PATH):
        with lcd(local_path):
            get('DATOS_*_2015*.tar.gz', '.')


# Retrieve file from server
@task
@roles('server20')
def remote20_get_file(criteria=None, rrel_path=None, lrel_path=None):
    '''Fabric task to retrieve files from a server'''
    if not criteria:
        puts('File criteria not specified...Aborting!')
        return
    cwd = os.path.dirname(__file__)
    if rrel_path:
        rpath = os.path.join(SERVER_ROOT, rrel_path)
    else:
        rpath = SERVER_ROOT
    if lrel_path:
        lpath = os.path.join(cwd, lrel_path)
        if not os.path.exists(lpath):
            os.makedirs(lpath)
    else:
        lpath = cwd

    with cd(rpath):
        with lcd(lpath):
            get(criteria, '.')


# DEPLOY TO SERVER
@task
@roles('server')
def deploy():
    with cd(REMOTE_PROJECT_PATH):
        run("git pull origin master")


@task
@runs_once
def rerun():
    with lcd(cwd):
        local('scripts/DB/create_db.sh')
        local('scripts/DB/create_schema.sh')
        local('scripts/DB/load_adm_boundaries.sh')
        local('scripts/DB/load_polling_stations.sh')
        local('scripts/DB/load_schools.sh')
        local('scripts/DB/update_school_sequence.sh')
        local('scripts/DB/load_dedupe_matches.sh')
        local('scripts/DB/load_weighted_matches.sh')
        local('python scripts/join_establecimientos_escuelas.py')


# DEFAULT TASK
@task(default=True)
def list_tasks():
    local('fab --list')
