#!/bin/bash

eval "$(ssh-agent -s)" >/dev/null 2>&1

if [[ -f /run/secrets/git_provisioning_key ]]; then
    SSH_KEY=$(cat /run/secrets/git_provisioning_key)
fi

echo "$SSH_KEY" > /root/.ssh/git_prov_key
chmod 600 /root/.ssh/git_prov_key
chmod 600 /root/.ssh/config
chown root:root /root/.ssh/config
ssh-add /root/.ssh/git_prov_key
python /app/main.py
