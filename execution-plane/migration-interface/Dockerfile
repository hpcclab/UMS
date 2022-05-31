FROM linuxserver/openssh-server
HEALTHCHECK CMD netstat -an | grep 2222 > /dev/null; if [ 0 != $? ]; then exit 1; fi;
RUN apk add rsync
COPY id_rsa.pub /config/.ssh/authorized_keys
