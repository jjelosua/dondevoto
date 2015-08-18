#!/bin/bash
SCRIPTPATH=$( cd $(dirname $0) ; pwd -P )
INPUT_PATH=$SCRIPTPATH'/../../data/csvlink/input'
CONFIG_PATH=$SCRIPTPATH'/../../data/csvlink/config'
csvlink $INPUT_PATH/polling_nogeo_sch_num.csv \
        $INPUT_PATH/escuelas_2013_sch_num.csv \
        --config_file=$CONFIG_PATH/config.json