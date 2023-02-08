FROM docker:latest
RUN apk add bash curl
COPY ambassador.sh wait-for-it.sh /usr/local/bin/
CMD ambassador.sh
RUN chmod +x /usr/local/bin/ambassador.sh /usr/local/bin/wait-for-it.sh
