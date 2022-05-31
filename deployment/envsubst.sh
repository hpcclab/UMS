#!/usr/bin/env bash

ARG1=${1:-.env}
ARG2=${2:-deployment}
ARG3=${3:-local}

set -a
# shellcheck source=.
source "$ARG1"
envsubst < "${ARG2}.template.yml" > "${ARG2}.${ARG3}.yml"
set +a