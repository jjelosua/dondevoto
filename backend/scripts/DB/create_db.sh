#!/bin/bash
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
DB_PATH=$SCRIPTPATH'/../../data/DB/sql'
DATABASE_NAME=dondevoto_arg_paso_2015
echo "Creating $DATABASE_NAME"
psql -q -f $DB_PATH/create_db.sql