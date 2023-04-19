#!/bin/bash

status_code=$(wait-for-it.sh "$API_SERVER" -- curl --write-out "%{http_code}" --silent --output /dev/null "$API_SERVER/create/$CONTAINER_NAME")

if [[ "$status_code" -ne 200 ]] && [[ "$status_code" -ne 204 ]] ; then
  exit 1
fi

until docker container attach --no-stdin "$CONTAINER_NAME"
do
  status=$(wait-for-it.sh "$API_SERVER" -- curl -i -o - --silent "$API_SERVER/probe/$CONTAINER_NAME")
  status_code=$(echo "$status" | grep HTTP |  awk '{print $2}')
  if [[ "$status_code" -eq 200 ]]; then
    continue
  elif [[ "$status_code" -eq 204 ]]; then
    sleep 1
  else
    exit 1
  fi
done
