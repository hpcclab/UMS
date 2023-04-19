# https://github.com/pinkisemils/memhog

FROM frolvlad/alpine-gcc
COPY main.c /opt/memoryhog/main.c
RUN cd /opt/memoryhog/ && gcc -Wall -O3 main.c -o memoryhog
COPY entrypoint.sh /opt/memoryhog/entrypoint.sh
RUN chmod +x /opt/memoryhog/entrypoint.sh
CMD ["/opt/memoryhog/entrypoint.sh"]