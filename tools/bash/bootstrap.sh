#!/bin/bash
#Get ansible and install

PLAYBOOK='install-iris.yml'
S3FILES_TO_CURL=(iris.yml vault.yml iris.init iris.systemd)
ANSIBLE_COMMAND="ansible-playbook --vault-id vault@"

[[ $UID != 0 ]] && echo "You need to be root to execute this script. Please run as root or with sudo." && exit 1

#Get the package manager this host uses
if [[ $(which yum) ]]; then
		echo "RedHat Based"
		PACKAGE_MANAGER='yum '
else
		echo "Debian Based"
		PACKAGE_MANAGER='apt '
fi

#Install pip if its not installed because that is how we will install ansible.
if [[ $(which pip) != 0 ]]; then 
	$PACKAGE_MANAGER install python-pip -y
	[[ $? != 0 ]] && echo "The package manager command to install pip failed: '$PACKAGE_MANAGER'" && exit 2
fi

#pip install ansible
pip install ansible
[[ $? != 0 ]] && echo "the pip command to install ansible failed!" && exit 3

mkdir -p /opt/iris/ansible
cd /opt/iris/ansible
#Curl down the ansible-playbook for iris and execute it.
for S3FILE in $S3FILES_TO_CURL; do
	curl https://s3.amazonaws.com/ihr-iris/ansible/$S3FILE
	[[ $? != 0 ]] && echo "The curl call to download the iris ansible file: '$S3FILE' did not execute successfully, unable to continue." && exit 4
done

$ANSIBLE_COMMAND $PLAYBOOK
[[ $? != 0 ]] && echo "The ansible-playbook for iris: '$PLAYBOOK' did not execute successfully" && exit 5
