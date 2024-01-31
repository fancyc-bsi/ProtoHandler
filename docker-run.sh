#!/bin/bash
# xhost +
docker build -t c2:latest .
docker run --rm -it --net host --hostname c2 -v $PWD:/shared --name c2 c2:latest
# docker run --rm -it --net host -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix --hostname c2 -v $PWD:/shared --name c2 c2:latest
# xhost -
