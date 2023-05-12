Quantos Project R to Python


Overview and steps to implemented on Docker Containers

How to Guide (installation on docker containers)



# R_to_Python
This is a new repository in which basic goal is to transform the existing R code to Python


How to install guide dask and flask in docker in 7 simple steps

1. install ubuntu 22.04 LTS on vm - physical node - or public cloud
2. install github packages using the following 2 separate commands in your terminal :

# install github

- sudo apt-get remove gitsome -y 
- type -p curl >/dev/null || (sudo apt update && sudo apt install curl -y)curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \&& sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \&& sudo apt update \&& sudo apt install gh -y


3. gh auth login # in order to login github QUANTOS-SA/R_to_Python

4. gh repo clone QUANTOS-SA/R_to_Python # to download the latest files and changes locally on your machine.

5. run the 2 following scripts in specific order using a terminal inside your linux machine as follows:

- sudo bash prepare_local_linux_system.sh
- sudo bash prepare_docker_containers_dask&flask.sh

6. Finally your environment is ready for use you can access the dashboard and the flask application as follows:

- http://your_running_external_ip_address:5000 for flask application
- http://your_running_external_ip_address:8787 for dask dashboard

7. if you need to add more workers you can run the following command:

- docker compose -f docker_compose.yml run -d worker # to add workers to the same system

and if you need to remove a worker respectively you can just run:

- docker stop and the name or id of the respective worker container.
