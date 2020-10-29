#!/bin/bash

# This simple script can be used to delete temporary directories that
#   are guaranteed to be no longer needed during a run of Pyexec.
# Normally Pyexec does this cleanup by itself.
# However some directories require root privilege to be deleted.
# This script is meant to be run with root privilege in the background
#   to delete those directories. 
# It can be used, even if multiple instances of Pyexec are running concurrently.
# The script does its cleanup every time it is called so consider using a cronjob
#   to run in periodically.
# On debian-based GNU/Linux based distributions use 'sudo crontab -e'.

slash="/";
list=$(find "/tmp" -maxdepth 1 -wholename "/tmp/pyexec-cache-*");
for path in $list
do
    files=$(ls $path -tr | head  -n -1);
    for file in $files
    do
        full=$path$slash$file;
        rm -rf $full;
    done
done
