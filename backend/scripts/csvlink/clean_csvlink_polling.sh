#!/bin/bash
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
INPUT_PATH=$SCRIPTPATH'/../../data/csvlink/input'
INPUT_FILE='establecimientos_sch_num_refine.csv'
OUTPUT_PATH=$SCRIPTPATH'/../../data/DB/csv'
OUTPUT_FILE='establecimientos.csv'
COLUMNS1='id,id_distrito,id_seccion,id_dpto,desc_seccion,id_circuito'
COLUMNS2=',nombre,direccion,localidad,cod_postal,num_escuela,cod_sie'
COLUMNS3=',latitud,longitud,wkb_geometry_4326'

csvcut -c $COLUMNS1$COLUMNS2$COLUMNS3 $INPUT_PATH/$INPUT_FILE > $OUTPUT_PATH/$OUTPUT_FILE