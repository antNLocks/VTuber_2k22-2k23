#!/bin/bash
nb_previous_exec=$(ls logs/ | grep -c logV)

log=logs/logV$nb_previous_exec.txt
errors=logs/errorsV$nb_previous_exec.txt

nohup python -u twitch_video_bot.py > $log 2> $errors &