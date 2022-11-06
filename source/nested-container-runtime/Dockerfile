FROM docker:dind as build
ARG CRIU_VERSION=3.17.1

RUN apk update && apk add \
    asciidoc \
    build-base \
#    coreutils \
    curl \
#    e2fsprogs \
    gcc \
#    git \
    gnutls-dev \
    iproute2 \
#    iptables \
#    ip6tables \
    libaio-dev \
    libcap-dev \
    libnet-dev \
    libnl3-dev \
    nftables-dev \
    pkgconfig \
    protobuf-c-dev \
    protobuf-dev \
#    py-yaml \
#    py3-pip \
    py3-protobuf \
#    tar \
    xmlto  \
  && curl -SL https://github.com/checkpoint-restore/criu/archive/refs/tags/v${CRIU_VERSION}.tar.gz \
    | tar xzf - -C / \
  && cd criu-${CRIU_VERSION} \
  && make -j4 \
  && make install

FROM docker:dind
ARG S6_OVERLAY_VERSION=3.1.0.1

ENV DOCKER_HOST=127.0.0.1:2375 \
    TINI_SUBREAPER=""

# s6-overlay installation assume using x86_64 architecture
ENTRYPOINT ["/init"]
RUN apk update && apk add  \
    bash \
    curl \
    gnutls \
    libnet \
    libnl3 \
    nftables \
    npm \
    openssh \
    openssh-client-default \
    protobuf-c \
    rsync \
    tar \
  && curl -SL https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz \
    | tar xJf - -C / \
  && curl -SL https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz \
    | tar xJf - -C / \
  && apk add --repository https://dl-3.alpinelinux.org/alpine/edge/community/ containerd \
  && mv /usr/bin/runc /usr/local/bin/ \
  && mv /usr/bin/containerd* /usr/local/bin/ \
  && mv /usr/bin/ctr /usr/local/bin/ \
  && ssh-keygen -A \
  && echo -e "PasswordAuthentication no" >> /etc/ssh/sshd_config \
  && sed -i '/LogLevel/c\LogLevel QUIET' /etc/ssh/sshd_config

COPY s6-rc.d /etc/s6-overlay/s6-rc.d/
COPY --from=build /usr/local/sbin/criu /usr/local/sbin/
COPY daemon.json /etc/docker/
COPY runc.conf /etc/criu/
COPY id_rsa.pub /root/.ssh/authorized_keys
COPY ca.crt /usr/local/share/ca-certificates/harbor-ca.crt
RUN update-ca-certificates

WORKDIR /app

COPY migration-interface/package.json .

RUN npm install

COPY migration-interface .

RUN npm run build \
    && chmod 400 /app/id_rsa \
    && chmod +x /app/wait-for-it.sh
