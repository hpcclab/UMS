FROM debian:10
ARG S6_OVERLAY_VERSION=3.1.0.1

ENV AWS_EC2_METADATA_DISABLED="true" \
    S3_CMD="/root/s3 local" \
    CRIU_OPTS="-v0"

VOLUME /data

ENTRYPOINT ["/init", "/command/with-contenv", "/root/run"]

# s6-overlay installation assume using x86_64 architecture
RUN apt-get update && apt-get install -y  \
    bash \
    curl \
    gcc \
    procps \
    python3 \
    python3-pip \
    tar \
    xz-utils \
  && pip3 install python-dotenv \
  && curl -SL https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz \
    | tar xJf - -C / \
  && curl -SL https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz \
    | tar xJf - -C / \
  && set -ex \
  && curl -SL https://github.com/twosigma/fastfreeze/releases/download/v1.3.0/fastfreeze-v1.3.0.tar.xz \
    | tar xJf - -C /opt \
  && ln -s /opt/fastfreeze/fastfreeze /usr/local/bin \
  && fastfreeze install \
  && curl https://dl.min.io/server/minio/release/linux-amd64/minio -o /usr/sbin/minio \
  && curl https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/sbin/mc

COPY s6-rc.d /etc/s6-overlay/s6-rc.d/
COPY config.json /root/.mc/
COPY wait run s3 /root/
COPY wait-for-it.sh /root/
RUN chmod +x /root/run /root/wait /root/s3 /root/wait-for-it.sh /usr/sbin/minio /usr/sbin/mc