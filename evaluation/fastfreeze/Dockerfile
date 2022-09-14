FROM debian:10
ARG S6_OVERLAY_VERSION=3.1.0.1

RUN apt-get update
RUN apt-get install -y curl xz-utils procps python3 python3-pip gcc tar

# s6-overlay installation assume using x86_64 architecture
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz

COPY wait /root/wait
COPY run /root/run
RUN chmod +x /root/run /root/wait
RUN pip3 install python-dotenv

ENTRYPOINT ["/init", "/command/with-contenv", "/root/run"]

COPY s6-rc.d /etc/s6-overlay/s6-rc.d/

ENV S3_CMD "aws --endpoint-url http://127.0.0.1:9000 s3"
ENV CRIU_OPTS "-vvvv"

RUN set -ex; \
  curl -SL https://github.com/twosigma/fastfreeze/releases/download/v1.3.0/fastfreeze-v1.3.0.tar.xz | \
    tar xJf - -C /opt; \
  ln -s /opt/fastfreeze/fastfreeze /usr/local/bin; \
  fastfreeze install

ADD https://dl.min.io/server/minio/release/linux-amd64/minio /usr/sbin
COPY credentials /root/.aws/credentials
RUN chmod +x /usr/sbin/minio \
  && mkdir -p /data/checkpoints \
  && pip3 install awscli