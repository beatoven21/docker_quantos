#!/bin/bash

# Update system packages
sudo apt update -y
sudo apt upgrade -y

# Install dependencies
sudo apt install build-essential libssl-dev libffi-dev zlib1g-dev -y

# Download Python 3.9 source code
wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz

# Extract the source code
tar -xzf Python-3.9.7.tgz

# Build and install Python 3.9
cd Python-3.9.7
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall

# Update alternatives for Python
sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.9 1

# Install pip 3.9
wget https://bootstrap.pypa.io/get-pip.py
sudo python3.9 get-pip.py

# Update alternatives for pip
sudo update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip3.9 1

# Set Python 3.9 as the default version
sudo update-alternatives --set python /usr/local/bin/python3.9

--------------------------------------------------------------------------

# install docker packages

sudo apt-get remove docker docker-engine docker.io containerd runc -y
sudo apt-get update -y
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg -y

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

--------------------------------------------------------------------------------
# Run docker without sudo

sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker 

---------------------------------------------------------------------------------
