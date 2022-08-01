#!/usr/bin/env bash

ARG1=${1:-.env}
ARG2=${2:-memhog}

set -a
# shellcheck source=.
source "$ARG1"
envsubst < "${ARG2}.template.yml" > "${ARG2}.yml"
set +a