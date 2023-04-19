#!/bin/bash
/opt/memoryhog/memoryhog &
while true
do
  /root/darknet/darknet detect /root/darknet/cfg/yolov3-tiny.cfg /root/yolov3-tiny.weights /root/darknet/data/dog.jpg >/dev/null 2>&1
done