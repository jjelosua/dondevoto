#!/bin/sh
DATABASE_NAME=geo_arg_paso_2015
TABLE_NAME=escuelasutf8
psql $DATABASE_NAME -q -c "SELECT setval('"$TABLE_NAME"_ogc_fid_seq', \
                           max(ogc_fid)) \
                           FROM $TABLE_NAME;"