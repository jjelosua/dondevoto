#!/bin/bash
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
INPUT_PATH=$SCRIPTPATH'/../../data/csvlink/output'
INPUT_FILE='dedupe_final_matches.csv'
OUTPUT_PATH=$SCRIPTPATH'/../../data/DB/csv'
OUTPUT_FILE='dedupe_matches.csv'
COLUMNS='id,ogc_fid,wkb_geometry_4326'

csvcut -c $COLUMNS $INPUT_PATH/$INPUT_FILE | 
sed -e '1s/id/establecimiento_id/' -e '1s/ogc_fid/escuela_id/' -e '1s/wkb_geometry_4326/the_geom/' |
sed '1 s/$/,match_source,score/' |
sed '2,$s/$/,0,0.95/' > $OUTPUT_PATH/$OUTPUT_FILE