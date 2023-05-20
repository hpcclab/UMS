sudo systemctl stop containerd kubelet

sudo rm /bin/ctr /bin/containerd*
sudo rm -rf /etc/containerd
sudo rm /usr/local/bin/runc
sudo rm /etc/systemd/system/containerd.service

sudo systemctl daemon-reload

sudo sed -i '$ d' /etc/sysctl.conf
sudo sysctl --system

sudo apt-get purge -y kubelet kubeadm kubectl
sudo apt-get autoremove -y

rm -rf containerd-1.3.6-linux-amd64.tar.gz custom-binaries podmigration-operator containerd runc

