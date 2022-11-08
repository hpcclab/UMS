import {FastifyLoggerInstance} from "fastify/types/logger"
import {FastifyRequest} from "fastify"
import {inspectContainer, listContainer} from "../docker"
import {MigrateRequestType} from "../schema"
import {execRsync, findDestinationFileSystemId, waitForIt} from "../lib"
import {join} from "path"
import dotenv from "dotenv"
import {readFileSync} from "fs"


async function transfer(request: FastifyRequest<{ Body: MigrateRequestType }>) {
    const containerInfos: any[] = await listContainer(request.log)

    const {checkpointId, interfaceHost, interfacePort, containers, volumes} = request.body

    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const pind = config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_PIND

    await waitForIt(interfaceHost, interfacePort, request.log)

    let responses
    if (pind) {
        responses = await Promise.all([
            ...containerInfos.map(
                containerInfo => transferContainerImagePind(checkpointId, interfaceHost, interfacePort, containers,
                    containerInfo, pind, request.log)
            ),
            ...volumes.map(
                volume => transferVolume(checkpointId, interfaceHost, interfacePort, volume, request.log)
            )
        ])
    } else {
        responses = await Promise.all([
            ...containerInfos.map(
                containerInfo => transferContainerImageDind(checkpointId, interfaceHost, interfacePort, containers,
                    containerInfo, pind, request.log)
            ),
            ...containerInfos.map(
                containerInfo => transferContainerFileSystem(checkpointId, interfaceHost, interfacePort, containers,
                    containerInfo, pind, request.log)
            ),
            ...volumes.map(
                volume => transferVolume(checkpointId, interfaceHost, interfacePort, volume, request.log)
            )
        ])
    }
    request.log.info(responses)
    return responses
}

async function transferContainerImageDind(checkpointId: string, interfaceHost: string, interfacePort: string,
                                      containers: any, containerInfo: any, pind: boolean, log: FastifyLoggerInstance) {
    const {destinationId} = findDestinationFileSystemId(containers, containerInfo)

    await execRsync(interfacePort, `/var/lib/docker/containers/${containerInfo.Id}/checkpoints/${checkpointId}`,
        `root@${interfaceHost}:/var/lib/docker/containers/${destinationId}/checkpoints`, log)
}

async function transferContainerImagePind(checkpointId: string, interfaceHost: string, interfacePort: string,
                                      containers: any, containerInfo: any, pind: boolean, log: FastifyLoggerInstance) {
    await execRsync(interfacePort, `/var/lib/containers/storage/${checkpointId}-${containerInfo.Id}.tar.gz`,
        `root@${interfaceHost}:/var/lib/containers/storage/${checkpointId}-${containerInfo.Id}.tar.gz`, log)
}

async function transferContainerFileSystem(checkpointId: string, interfaceHost: string, interfacePort: string,
                                           containers: any, containerInfo: any, pind: boolean, log: FastifyLoggerInstance) {
    if (pind) return
    const {destinationFs} = findDestinationFileSystemId(containers, containerInfo)

    const {GraphDriver: {Name}} = await inspectContainer(containerInfo.Id, log)
    if (Name === 'overlay2' && destinationFs !== null) {
        await execRsync(interfacePort, `/checkpoints/${checkpointId}/containers/${containerInfo.Id}`, `root@${interfaceHost}:${destinationFs}`.slice(0, -5), log)
    }
}

async function transferVolume(checkpointId: string, interfaceHost: string, interfacePort: string, volume: any, log: FastifyLoggerInstance) {
    await execRsync(interfacePort, join(`/checkpoints/${checkpointId}/volumes`, volume), `root@${interfaceHost}:/mount`, log)
}


export {transfer}
