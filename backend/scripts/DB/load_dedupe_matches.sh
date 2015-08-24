#!/bin/sh
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
CSV_PATH=$SCRIPTPATH'/../../data/DB/csv'
CSV_FILE='dedupe_matches.csv'
DATABASE_NAME=dondevoto_arg_paso_2015
TABLE_NAME=dedupe_matches
COLUMNS=establecimiento_id,escuela_id,the_geom,match_source,score
echo "loading data into $TABLE_NAME in $DATABASE_NAME DB"
psql $DATABASE_NAME -q -c "\copy $TABLE_NAME($COLUMNS) FROM \
                           '$CSV_PATH/$CSV_FILE' \
                           with delimiter as ',' CSV HEADER"