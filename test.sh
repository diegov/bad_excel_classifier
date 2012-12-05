#!/usr/bin/env bash

rm random_generated/*xls 2>/dev/null
rm random_generated/training/*xls 2>/dev/null
rm random_generated/verification/*xls 2>/dev/null

./generate_samples.py 

python classifier.py --init test.set --rs 0 --re 3 --cs 0 --ce 8 --sheet=0

train()
{
    case "$1" in
	"bad") bad="--bad" ;;
	*) bad="" ;;
    esac
	    
    while read l
    do
	echo "Training using $l"
	python classifier.py --train test.set $bad "$l"
    done
}

find good/training -type f -name "*.xls" | train good

find random_generated -type f -name "training*.xls" | train good

find bad/training -type f -name "*.xls" | train bad

find misc_samples/training -type f -name "*.xls" | train bad

find -maxdepth 3 -type f -name "*.xls" | grep -v "training" | while read l; 
do
    python classifier.py --verify test.set "$l" --show-grid
done
