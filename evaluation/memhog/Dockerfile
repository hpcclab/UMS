# https://github.com/pinkisemils/memhog

FROM frolvlad/alpine-gcc
RUN mkdir -p /opt/memoryhog
COPY main.c /opt/memoryhog/main.c
RUN cd /opt/memoryhog/ && gcc -Wall -O3 main.c -o memoryhog
CMD ["/opt/memoryhog/memoryhog"]