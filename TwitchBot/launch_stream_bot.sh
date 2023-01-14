#!/bin/bash
nb_previous_exec=$(ls logs/ | grep -c logS)

log=logs/logS$nb_previous_exec.txt
errors=logs/errorsS$nb_previous_exec.txt

nohup python -u twitch_stream_bot.py > $log 2> $errors &