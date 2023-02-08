FROM ghcr.io/hpcclab/live_service_migration/migration-interface:development as interface

FROM node:18-alpine
ARG S6_OVERLAY_VERSION=3.1.0.1

# s6-overlay installation assume using x86_64 architecture
ENTRYPOINT ["/init"]
RUN apk update && apk add  \
    bash \
    curl \
    openssh \
    openssh-client-default \
    rsync \
  && curl -SL https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz \
    | tar xJf - -C / \
  && curl -SL https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz \
    | tar xJf - -C / \
  && ssh-keygen -A \
  && echo -e "PasswordAuthentication no" >> /etc/ssh/sshd_config \
  && sed -i '/LogLevel/c\LogLevel QUIET' /etc/ssh/sshd_config

COPY s6-rc.d /etc/s6-overlay/s6-rc.d/
COPY id_rsa.pub /root/.ssh/authorized_keys

WORKDIR /app

COPY --from=interface /app/package*.json ./

RUN npm ci --omit=dev

COPY --from=interface /app .

RUN chmod 400 /app/id_rsa \
    && chmod +x /app/wait-for-it.sh

VOLUME /var/lib/kubelet/migration
