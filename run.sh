#!/bin/bash

docker build -t rtest:latest .
docker run -e SSH_KEY="$(cat ~/.ssh/git_provisioning_key)" --name rtest --rm -it -p 3000:3000 -v /home/archusr/.ssh:/root/.ssh rtest:latest
