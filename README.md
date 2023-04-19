# UMS: Ubiquitous Migration Solution

## Introduction
The aim of this project is to enable containerized service migration across computing systems employing container orchestrators such as Kubernetes. UMS acts as an umbrella solution encompassing various state-of-the-art migration approaches:
- **Orchestrator-level migration approach** that relies on the orchestrator native features to perform the migration
- **Service-level migration approach** that the migration mechanism is completely developed in the service container image
- **Container-level migration approach** that leverages the advantage of container nesting to enable the migration without the demand to change the service image or underlying orchestrator.

## Installation
### Prerequisites
- A Kubernetes cluster with following features. 
  - The `MutatingAdmissionWebhook` and `ValidatingAdmissionWebhook` must be enabled via `--enable-admission-plugins` flag (see [Kubernetes documentation](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#how-do-i-turn-on-an-admission-controller)).
  - The RBAC (`ClusterRole`) must be enabled via `--authorization-mode` flag (see [Kubernetes documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)). See [Kopf configuration](deployment/kopf.kubernetes.yml) to see detailed permission required to create the `ClusterRole`.
  - UMS must be deployed on both the source and destination cluster.
- To enable an orchestrator-level migration approach, the following setups are required.
  - A custom Kubernetes cluster. See [podmigration-operator documentation](https://github.com/SSU-DCN/podmigration-operator/blob/main/init-cluster-containerd-CRIU.md).
  - An empty host directory `/var/lib/kubelet/migration` must exist.
- To use a service-level migration approach, a `SYS_PTRACE` CPU capability is required in pod security context (see [Enabling ptrace for CRIU](https://github.com/twosigma/fastfreeze#enabling-ptrace-for-criu)). In some Kubernetes distributions, a `privileged: true` is required.
- To enable a container-level migration approach, the following setups are required.
  - A pod security context `privileged: true` is required due to the [Docker-in-Docker limitation](https://github.com/docker-library/docker/issues/151#issuecomment-483185972) and the [Podman-in-Docker limitation](https://hub.docker.com/r/mgoltzsche/podman).
  - Empty host directories `/dev/shm/dind` and `/dev/shm/pind` must exist for caching nested container image.

### Configurations
UMS components can be configured via environment variables. Below is the list of supported variables for each component.

#### Coordinator
The coordinator is the main actor who coordinate the service migration. To enable an orchestrator-level migration approach, the following variables need to be set
- `SSU_INTERFACE_ENABLE` set to any value to enable the interface
- `SSU_INTERFACE_SERVICE` (default: `ssu-interface`) specify the name of the interface service. It needs to be consistent with [ssu.yml](deployment/ssu.yml).
- `SSU_INTERFACE_HOST` specify the hostname for replying the destination endpoint to the source cluster. If not set, the host name in the request URL is return.
- `SSU_INTERFACE_NODEPORT` (default: `30002`) specify the NodePort of the interface service. It needs to be consistent with [ssu.yml](deployment/ssu.yml).

#### Operator
- `SYNC_HOST` specify the hostname for replying the destination endpoint to the source cluster. If not set, the host name in the request URL is return.

#### Interceptor
- `HOST_NAME` specify the hostname for Kubernetes API server to connect. If not set, it will use the default value provided by Kopf library.


#### SSU Interface
- `LOG_LEVEL` specify the detail level of logging. It must have the following methods: info, error, debug, fatal, warn, trace, silent, child


### Deployment
To deploy UMS, run the following commands:
```
kubectl apply kopf.kubernetes.yml
kubectl apply deployment.yml
```

To use an orchestrator-level migration approach, run the following commands additionally:
```
kubectl apply ssu-crd.yml
kubectl apply ssu.yml
```

## Usage
### Creating containerized service
Firstly, the service developers need to decide the appropriate migration approach for their service.

#### Orchestrator-level migration approach

In this approach, the service can be deployed without any further changes in the configuration.

#### Service-level migration approach

In this approach, the service needs to be built from provided `fastfreeze-base` image (available [here](https://github.com/users/hpcclab/packages/container/package/live_service_migration%2Ffastfreeze-base)). Then, the `migration-interface: 'ff'` needs to be set in the annotations of the pod. Below is an example of deploying example service `memhogff` for using service-level migration approach.

```
apiVersion: v1
kind: Pod
metadata:
  name: memhog
  annotations:
    migration-interface: 'ff'
spec:
  serviceAccountName: migration-coordinator
  containers:
    - name: memhog
      image: ghcr.io/hpcclab/live_service_migration/memhogff:main
```

The following environment variables can be configured in `fastfreeze-base` image:

- `CRIU_OPTS` (default: `-v0`) specify additional options for CRIU checkpoint/restore commands.

#### Container-level migration approach

In this approach, the `migration-interface: 'dind'` or `migration-interface: 'pind'` needs to be set in the annotations of the pod. Below is an example of deploying example service `memhog` for using container-level migration approach with Docker-in-Docker runtime.

```
apiVersion: v1
kind: Pod
metadata:
  name: memhog
  annotations:
    migration-interface: 'dind'
spec:
  serviceAccountName: migration-coordinator
  containers:
    - name: memhog
      image: ghcr.io/hpcclab/live_service_migration/memhog:main
```

### Migration

POST /migrate at the source cluster with following request body

```
{
    "name": "CONTAINER_NAME",
    "namespace": "CONTAINER_NAMESPACE",
    "destinationUrl": "DESTINATION_URL",
    "keep": "true",
    "redirect": "REDIRECT_URL_AFTER_MIGRATION"
}
```
