#!/bin/sh

if [ -z "${PROCESS}" ]; then
  exec /opt/memoryhog/memoryhog
else
  i=1
  while [ "$i" -le "$PROCESS" ]; do
    /opt/memoryhog/memoryhog &
    i=$(($i+1))
  done
  wait
fi