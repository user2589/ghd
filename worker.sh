#!/bin/bash

while true; do
    ./manage.py scrape >> worker.log 2>> error.log
done
