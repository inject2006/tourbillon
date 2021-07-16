#!/bin/bash

output="$(git pull <<EOF)"
if [ "$output" != "Already up-to-date." ]
then
    docker restart nginx-devops-gui
else
    echo -e "skip"
fi
