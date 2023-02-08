import {FastifyReply, FastifyRequest} from "fastify"
import {MigrateRequestType} from "../schema"
import {ContainerInfo, execRsync} from "../lib"
import {FastifyBaseLogger} from "fastify/types/logger"
import {AsyncBlockingQueue} from "../queue"
import {migrationInterface} from "../interface";


async function migrate(request: FastifyRequest<{ Body: MigrateRequestType }>, reply: FastifyReply) {
    const start = Date.now()
    const responses = await migrationInterface.migrate(start, request.body)
    request.log.info(responses)
    return responses
}

async function transferContainerImage(waitDestination: Promise<void>, start: number, interfacePort: string,
                                      queue: AsyncBlockingQueue<string>, sourcePath: string, destinationPath: string,
                                      log: FastifyBaseLogger) {
    let exist = false
    let delay = 0
    await waitDestination
    while (true) {
        if (queue.done) break
        await queue.dequeue()
        if (!exist) {
            exist = true
            delay = (Date.now() - start) / 1000
        }
        await execRsync(interfacePort, sourcePath, destinationPath, log)
    }

    while (!queue.isEmpty()) {
        await queue.dequeue()
    }

    await execRsync(interfacePort, sourcePath, destinationPath, log)
    return {checkpoint_files_transfer: (Date.now() - start) / 1000, checkpoint_files_delay: delay}
}

async function transferContainerFS(waitDestination: Promise<void>, start: number, interfaceHost: string,
                                   interfacePort: string, containerInfo: ContainerInfo, destinationFs: string,
                                   log: FastifyBaseLogger) {
    await waitDestination
    const delay = (Date.now() - start) / 1000
    const {GraphDriver: {Name, Data: {MergedDir}}} = await migrationInterface.inspectContainer(containerInfo.Id)
    if (Name === 'overlay2' && destinationFs !== null) {
        await execRsync(interfacePort, `${MergedDir}/*`, `root@${interfaceHost}:${destinationFs}`, log)
    }
    return {file_system_transfer: (Date.now() - start) / 1000, file_system_delay: delay}
}

async function transferVolume(waitDestination: Promise<void>, start: number, interfaceHost: string, interfacePort: string,
                              volume: any, log: FastifyBaseLogger) {
    await waitDestination
    const delay = (Date.now() - start) / 1000
    await execRsync(interfacePort, volume, `root@${interfaceHost}:/mount`, log)
    return {volume_transfer: (Date.now() - start) / 1000, volume_delay: delay}
}

export {
    migrate,
    transferContainerImage,
    transferContainerFS,
    transferVolume
}
