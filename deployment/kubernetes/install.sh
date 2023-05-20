wget https://github.com/containerd/containerd/releases/download/v1.3.6/containerd-1.3.6-linux-amd64.tar.gz
mkdir containerd
tar -xvf containerd-1.3.6-linux-amd64.tar.gz -C containerd
sudo cp containerd/bin/* /bin/

git clone https://github.com/SSU-DCN/podmigration-operator.git
tar -vxf podmigration-operator/binaries.tar.bz2
chmod +x custom-binaries/containerd
sudo cp custom-binaries/containerd /bin/

sudo mkdir /etc/containerd
sudo cp config.toml /etc/containerd/

wget https://github.com/opencontainers/runc/releases/download/v1.0.0-rc92/runc.amd64
sudo mv runc.amd64 runc
chmod +x runc
sudo cp runc /usr/local/bin/

sudo cp containerd.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl restart containerd

sudo echo 'net.bridge.bridge-nf-call-iptables = 1' >> /etc/sysctl.conf
sudo echo '1' > /proc/sys/net/ipv4/ip_forward
sudo sysctl --system
sudo modprobe overlay
sudo modprobe br_netfilter

curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add
sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"
sudo apt-get install cri-tools=1.25.0-00 kubeadm=1.19.0-00 kubelet=1.19.0-00 kubectl=1.19.0-00 -y

chmod +x custom-binaries/kubeadm custom-binaries/kubelet
sudo cp custom-binaries/kubeadm custom-binaries/kubelet /usr/bin/
sudo systemctl daemon-reload
sudo systemctl restart kubelet

sudo kubeadm init --pod-network-cidr=10.244.0.0/16