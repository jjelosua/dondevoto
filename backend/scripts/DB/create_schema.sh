#!/bin/bash
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
DB_PATH=$SCRIPTPATH'/../../data/DB/sql'
DATABASE_NAME=geo_arg_paso_2015
echo "Creating $DATABASE_NAME schema"
psql -q -d $DATABASE_NAME -f $DB_PATH/create_schema.sql