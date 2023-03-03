FROM debian:10
WORKDIR /root
RUN apt update \
    && apt install -y git wget make gcc g++ \
    && wget https://pjreddie.com/media/files/yolov3.weights \
    && git clone https://github.com/pjreddie/darknet \
    && cd darknet \
    && make
COPY entrypoint.sh /root
COPY main.c /opt/memoryhog/main.c
RUN cd /opt/memoryhog/ && gcc -Wall -O3 main.c -o memoryhog \
    && chmod +x /root/entrypoint.sh
CMD ["/root/entrypoint.sh"]
WORKDIR /root/darknet
#docker stats yolo --no-stream --format "{{.MemUsage}}" | cut -f1 -d " "