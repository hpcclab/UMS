FROM docker:dind
ARG S6_OVERLAY_VERSION=3.1.0.1
ARG CRIU_VERSION=3.17.1

ENV DOCKER_HOST 127.0.0.1:2375

# s6-overlay installation assume using x86_64 architecture
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz
ENTRYPOINT ["/init"]

COPY s6-rc.d /etc/s6-overlay/s6-rc.d/

COPY daemon.json /etc/docker/

RUN apk update && apk add \
    gcc \
    bash \
    build-base \
    coreutils \
    git \
    gnutls-dev \
    libaio-dev \
    libcap-dev \
    libnet-dev \
    libnl3-dev \
    nftables \
    nftables-dev \
    pkgconfig \
    protobuf-c-dev \
    protobuf-dev \
    py3-pip \
    py3-protobuf \
    python3 \
    ip6tables \
    iptables \
    nftables \
    iproute2 \
    bash \
    e2fsprogs \
    py-yaml \
    tar \
    asciidoc \
    xmlto  \
  && git clone https://github.com/checkpoint-restore/criu \
  && cd criu \
  && git checkout v${CRIU_VERSION} \
  && make -j4 \
  && make install \
  && apk add --repository https://dl-3.alpinelinux.org/alpine/edge/community/ containerd \
  && mv /usr/bin/runc /usr/local/bin/ \
  && mv /usr/bin/containerd* /usr/local/bin/ \
  && mv /usr/bin/ctr /usr/local/bin/

COPY runc.conf /etc/criu/

COPY ca.crt /usr/local/share/ca-certificates/harbor-ca.crt
RUN update-ca-certificates

RUN apk add openssh-client-default=9.0_p1-r2 openssh rsync \
  && ssh-keygen -A \
  && echo -e "PasswordAuthentication no" >> /etc/ssh/sshd_config

COPY id_rsa.pub /root/.ssh/authorized_keys

RUN apk add npm

WORKDIR /app

COPY migration-engine/package.json .

RUN npm install

COPY migration-engine .

RUN npm run build \
    && chmod 400 /app/id_rsa \
    && chmod +x /app/wait-for-it.sh
