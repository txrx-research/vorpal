#!/bin/bash
for (( counter=0; counter<10; counter++ ))
do
python script.py -t 10000 -d 500 -cs $(echo $counter*0.1 | bc)
done
python script.py -t 10000 -d 500 -cs 0.99
printf "\n"