#!/bin/sh
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
CSV_PATH=$SCRIPTPATH'/../../data/DB/csv'
CSV_FILE='divisiones_administrativas.csv'
DATABASE_NAME=geo_arg_paso_2015
TABLE_NAME=divisiones_administrativas
echo "loading data into $TABLE_NAME in $DATABASE_NAME DB"
psql $DATABASE_NAME -q -c "\copy $TABLE_NAME FROM '$CSV_PATH/$CSV_FILE' \
                           with delimiter as ',' CSV HEADER"