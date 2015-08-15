#!/bin/sh
DATABASE_NAME=geo_arg_paso_2015
TABLE_NAME=weighted_matches
psql $DATABASE_NAME -q -c "SELECT setval('"$TABLE_NAME"_id_seq', \
                           max(id)) \
                           FROM $TABLE_NAME;"