FROM golang:1.15.5

CMD ["go", "run", "/go/podmigration-operator/api-server/cmd/main.go"]

RUN git clone https://github.com/SSU-DCN/podmigration-operator.git --branch multi-cluster
RUN git clone https://github.com/vutuong/kubernetes.git

WORKDIR /go/podmigration-operator

RUN go fmt /go/podmigration-operator/api-server/cmd/main.go
RUN go vet /go/podmigration-operator/api-server/cmd/main.go
