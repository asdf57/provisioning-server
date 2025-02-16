#!/bin/bash

eval "$(ssh-agent -s)" >/dev/null 2>&1

if [[ -f /run/secrets/git_provisioning_key ]]; then
    SSH_KEY=$(cat /run/secrets/git_provisioning_key)
fi

mkdir -p /root/.ssh

echo "$SSH_KEY" > /root/.ssh/git_provisioning_key
chmod 600 /root/.ssh/git_provisioning_key
ssh-add /root/.ssh/git_provisioning_key
ssh-keyscan -t rsa github.com >> /root/.ssh/known_hosts
python /app/main.py
