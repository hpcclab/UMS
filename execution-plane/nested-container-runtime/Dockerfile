FROM docker:dind

ENV DOCKER_HOST 127.0.0.1:2375

HEALTHCHECK CMD wget -q localhost:2375/_ping || exit 1

CMD ["dockerd", "--tls=false", "--host=tcp://0.0.0.0:2375"]

COPY daemon.json /etc/docker/

RUN apk add tar \
  && apk add --repository https://dl-3.alpinelinux.org/alpine/edge/testing/ criu \
  && apk add --repository https://dl-3.alpinelinux.org/alpine/edge/community/ containerd \
  && mv /usr/bin/runc /usr/local/bin/ \
  && mv /usr/bin/containerd* /usr/local/bin/ \
  && mv /usr/bin/ctr /usr/local/bin/

COPY runc.conf /etc/criu/

COPY ca.crt /usr/local/share/ca-certificates/harbor-ca.crt
RUN update-ca-certificates
