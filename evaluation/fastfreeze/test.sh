#!/bin/bash
fastfreeze run --image-url file:/tmp/ff-test -- python3 /root/test.py &
sleep 1000