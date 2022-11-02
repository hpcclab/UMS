import {FastifyLoggerInstance} from "fastify/types/logger"
import {FastifyRequest} from "fastify"
import {inspectContainer, listContainer} from "../docker"
import {MigrateRequestType} from "../schema"
import {execRsync, findDestinationFileSystemId, waitForIt} from "../lib"
import {join} from "path"


async function transfer(request: FastifyRequest<{ Body: MigrateRequestType }>) {
    const containerInfos: any[] = await listContainer(request.log)

    const {checkpointId, interfaceHost, interfacePort, containers, volumes} = request.body

    await waitForIt(interfaceHost, interfacePort, request.log)

    let responses
    responses = await Promise.all([
        ...containerInfos.map(
            containerInfo => transferContainerImage(checkpointId, interfaceHost, interfacePort, containers,
                containerInfo, request.log)
        ),
        ...containerInfos.map(
            containerInfo => transferContainerFileSystem(checkpointId, interfaceHost, interfacePort, containers,
                containerInfo, request.log)
        ),
        ...volumes.map(
            volume => transferVolume(checkpointId, interfaceHost, interfacePort, volume, request.log)
        )
    ])
    request.log.info(responses)
    return responses
}

async function transferContainerImage(checkpointId: string, interfaceHost: string, interfacePort: string, containers: any, containerInfo: any, log: FastifyLoggerInstance) {
    const {destinationId} = findDestinationFileSystemId(containers, containerInfo)

    await execRsync(interfacePort, `/var/lib/docker/containers/${containerInfo.Id}/checkpoints/${checkpointId}`,
        `root@${interfaceHost}:/var/lib/docker/containers/${destinationId}/checkpoints`, log)
}

async function transferContainerFileSystem(checkpointId: string, interfaceHost: string, interfacePort: string, containers: any, containerInfo: any, log: FastifyLoggerInstance) {
    const {destinationFs} = findDestinationFileSystemId(containers, containerInfo)

    const {GraphDriver: {Name}} = await inspectContainer(containerInfo.Id, log)
    if (Name === 'overlay2' && destinationFs !== null) {
        await execRsync(interfacePort, `/checkpoints/${checkpointId}/containers/${containerInfo.Id}`, `root@${interfaceHost}:${destinationFs}`.slice(0, -5), log)
    }
}

async function transferVolume(checkpointId: string, interfaceHost: string, interfacePort: string, volume: any, log: FastifyLoggerInstance) {
    await execRsync(interfacePort, join(`/checkpoints/${checkpointId}/volumes`, volume), `root@${interfaceHost}:/mount`, log)
}


export {transfer, transferContainerImage, transferContainerFileSystem, transferVolume}
