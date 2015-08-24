#!/bin/bash
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
INPUT_PATH=$SCRIPTPATH'/../../data/csvlink/input'
INPUT_FILE='escuelas_dondevoto_2013_refine.csv'
OUTPUT_PATH=$SCRIPTPATH'/../../data/DB/csv'
OUTPUT_FILE='escuelas.csv'
COLUMNS1='ogc_fid,id_distrito,id_seccion'
COLUMNS2=',nombre,direccion,localidad,cod_postal,num_escuela,cueanexo'
COLUMNS3=',wkb_geometry_4326'

csvcut -c $COLUMNS1$COLUMNS2$COLUMNS3 $INPUT_PATH/$INPUT_FILE > $OUTPUT_PATH/$OUTPUT_FILE