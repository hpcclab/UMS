FROM docker:latest
RUN apk add bash curl
COPY monitor.sh wait-for-it.sh /usr/local/bin/
CMD monitor.sh
