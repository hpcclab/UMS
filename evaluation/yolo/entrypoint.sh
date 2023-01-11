#!/bin/bash
/opt/memoryhog/memoryhog &
while true
do
  /root/darknet/darknet detect /root/darknet/cfg/yolov3.cfg /root/yolov3.weights /root/darknet/data/dog.jpg >/dev/null 2>&1
done