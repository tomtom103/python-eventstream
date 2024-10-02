#!/usr/bin/env bash

set -e

ENV_FILE=.env
if [[ ! -f ${ENV_FILE} ]]; then
    echo "Error: ${ENV_FILE} does not exist"
    exit 1
fi

source ${ENV_FILE}

docker run \
    --detach \
    --rm \
    --name ${REDIS_CONTAINER} \
    --publish ${REDIS_PORT}:6379 \
    docker.io/library/redis:latest
