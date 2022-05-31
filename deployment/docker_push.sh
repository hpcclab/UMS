#!/usr/bin/env bash
set -a
source .env

docker tag migration-operator:latest $REGISTRY/migration-operator:latest
docker push $REGISTRY/migration-operator:latest &
docker tag migration-coordinator:latest $REGISTRY/migration-coordinator:latest
docker push $REGISTRY/migration-coordinator:latest &
docker tag migration-engine:latest $REGISTRY/migration-engine:latest
docker push $REGISTRY/migration-engine:latest &
docker tag migration-dind:latest $REGISTRY/migration-dind:latest
docker push $REGISTRY/migration-dind:latest &
docker tag migration-interface:latest $REGISTRY/migration-interface:latest
docker push $REGISTRY/migration-interface:latest &
docker tag migration-monitor:latest $REGISTRY/migration-monitor:latest
docker push $REGISTRY/migration-monitor:latest &
docker tag migration-proxy:latest $REGISTRY/migration-proxy:latest
docker push $REGISTRY/migration-proxy:latest &
docker tag migration-redirector:latest $REGISTRY/migration-redirector:latest
docker push $REGISTRY/migration-redirector:latest &
docker tag memhog:latest $REGISTRY/memhog:latest
docker push $REGISTRY/memhog:latest &

set +a