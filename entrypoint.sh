#!/bin/bash

eval "$(ssh-agent -s)" >/dev/null 2>&1

if [[ -f /run/secrets/git_provisioning_key ]]; then
    SSH_KEY=$(cat /run/secrets/git_provisioning_key)
fi

mkdir -p /root/.ssh

echo "$SSH_KEY" > /root/.ssh/git_provisioning_key

cat /root/.ssh/git_provisioning_key

chmod 600 /root/.ssh/git_provisioning_key

ls -al /root/.ssh

ssh-add /root/.ssh/git_provisioning_key
python /app/main.py
