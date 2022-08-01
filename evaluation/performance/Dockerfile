FROM debian:10

RUN echo "deb http://deb.debian.org/debian buster-backports main" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get -t buster-backports install -y iperf3 sysbench

CMD iperf3
