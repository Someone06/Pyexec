#!/bin/bash
v2 run --projectdir "$1" --environment "PYTHONPATH=$(find $1 -not -path '*/\.*' -not -path '*__pycache__*' -type d -printf ":%p" | sed "s|$1|/mnt/projectdir/|g")" --exclude $2 $3
