FROM golang:1.15.5

CMD ["go", "run", "/go/podmigration-operator/main.go"]

RUN apt-get update && apt-get install -y sudo
RUN git clone https://github.com/SSU-DCN/podmigration-operator.git --branch multi-cluster
RUN git clone https://github.com/vutuong/kubernetes.git
RUN curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"  | bash \
  && mv ./kustomize /usr/local/bin/kustomize
RUN os="linux/amd64"  \
  && version=$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)  \
  && curl -LO "https://storage.googleapis.com/kubernetes-release/release/$version/bin/$os/kubectl" \
  && chmod +x ./kubectl \
  && mv ./kubectl /usr/local/bin/kubectl

WORKDIR /go/podmigration-operator

RUN make manifests
RUN make generate
RUN make fmt
RUN make vet
