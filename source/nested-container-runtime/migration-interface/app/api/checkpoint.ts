import {FastifyRequest} from "fastify"
import {checkpointContainer, inspectContainer, listContainer} from "../docker"
import {CheckpointRequestType} from "../schema"
import {cpSync, readFileSync} from "fs"
import {FastifyLoggerInstance} from "fastify/types/logger"
import {join} from "path"
import dotenv from "dotenv"
import {AsyncBlockingQueue} from "../queue"

async function checkpoint(request: FastifyRequest<{ Body: CheckpointRequestType }>) {
    const containerInfos: any[] = await listContainer(request.log)
    const {checkpointId, volumes} = request.body
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const exit = config[process.env.START_MODE_ANNOTATION!] !== process.env.START_MODE_ACTIVE
    const responses = await Promise.all([
        ...containerInfos.map(
            containerInfo => checkpointContainer(containerInfo.Id, checkpointId, exit, new AsyncBlockingQueue<string>(),
                request.log)
        ),
        ...containerInfos.map(
            containerInfo => checkpointContainerFS(checkpointId, containerInfo, request.log)
        ),
        ...volumes.map(
            volume => checkpointVolume(checkpointId, volume, request.log)
        )
    ])
    request.log.info(responses)
    return responses
}

async function checkpointContainerFS(checkpointId: string, containerInfo: any, log: FastifyLoggerInstance) {
    const {GraphDriver: {Name, Data: {UpperDir}}} = await inspectContainer(containerInfo.Id, log)
    if (Name === 'overlay2') {
        cpSync(UpperDir, `/checkpoints/${checkpointId}/containers/${containerInfo.Id}`, {recursive: true})
    }
}

async function checkpointVolume(checkpointId: string, volume: any, log: FastifyLoggerInstance) {
    cpSync(volume, join(`/checkpoints/${checkpointId}/volumes`, volume), {recursive: true})
}

export {checkpoint}
