import {FastifyReply, FastifyRequest} from "fastify"
import {MigrateRequestType} from "../schema"
import {ContainerInfo, execRsync, findDestinationFileSystemId, waitForIt} from "../lib"
import {FastifyBaseLogger} from "fastify/types/logger"
import dotenv from "dotenv"
import {readFileSync} from "fs"
import chokidar from "chokidar"
import {AsyncBlockingQueue} from "../queue"
import {migrationInterface} from "../interface";


async function migrate(request: FastifyRequest<{ Body: MigrateRequestType }>, reply: FastifyReply) {
    const start = Date.now()
    const {checkpointId, interfaceHost, interfacePort, containers, volumes} = request.body

    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await migrationInterface.listContainer(config[process.env.SPEC_CONTAINER_ANNOTATION!], request.log)
    const exit = config[process.env.START_MODE_ANNOTATION!] !== process.env.START_MODE_ACTIVE
    const pind = config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_PIND

    const waitDestination = waitForIt(interfaceHost, interfacePort, request.log)

    let responses
    if (pind) {
        responses = await Promise.all([
            ...containerInfos.map(
                containerInfo => migrateOneContainerPind(waitDestination, start, checkpointId, interfaceHost,
                    interfacePort, containerInfo, exit, request.log)
            ),
            ...volumes.map(
                volume => transferVolume(waitDestination, start, interfaceHost, interfacePort, volume, request.log)
            )
        ])
    } else {
        responses = await Promise.all([
            ...containerInfos.map(
                containerInfo => migrateOneContainerDind(waitDestination, start, checkpointId, interfaceHost,
                    interfacePort, containers, containerInfo, exit, request.log)
            ),
            ...volumes.map(
                volume => transferVolume(waitDestination, start, interfaceHost, interfacePort, volume, request.log)
            )
        ])
    }
    request.log.info(responses)
    return responses
}

async function migrateOneContainerDind(waitDestination: Promise<void>, start: number, checkpointId: string,
                                       interfaceHost: string, interfacePort: string, containers: any,
                                       containerInfo: ContainerInfo, exit: boolean, log: FastifyBaseLogger) {
    const {destinationId, destinationFs} = findDestinationFileSystemId(containers, containerInfo)

    const sourceImagePath = `/var/lib/docker/containers/${containerInfo.Id}/checkpoints/${checkpointId}`
    const destinationImagePath = `root@${interfaceHost}:/var/lib/docker/containers/${destinationId}/checkpoints`
    const imageQueue = new AsyncBlockingQueue<string>()
    let imageQueueInit: (value: unknown) => void
    const imageQueueInitPromise = new Promise(resolve => {
        imageQueueInit = resolve
    })
    const imageWatcher = chokidar.watch(sourceImagePath)
    imageWatcher
        .on('all', (event, path) => {
            if ((event === 'add' || event == 'change') && imageQueue.isEmpty()) {
                imageQueue.enqueue(path)
            }
        })
        .on('ready', () => {
            imageQueueInit(null)
        })

    await imageQueueInitPromise

    const responses = await Promise.all([
        transferContainerImage(waitDestination, start, interfacePort, imageQueue, sourceImagePath, destinationImagePath, log),
        transferContainerFS(waitDestination, start, interfaceHost, interfacePort, containerInfo, destinationFs, log),
        migrationInterface.checkpointContainer(start, containerInfo.Id, checkpointId, exit, imageQueue, log)
    ])

    await imageWatcher.close()

    return responses.reduce((prev: { [key: string]: number }, curr: any) => ({...prev, ...curr}), {})
}

async function migrateOneContainerPind(waitDestination: Promise<void>, start: number, checkpointId: string,
                                       interfaceHost: string, interfacePort: string, containerInfo: ContainerInfo,
                                       exit: boolean, log: FastifyBaseLogger) {
    const sourceImagePath = `/var/lib/containers/storage/${checkpointId}-${containerInfo.Id}.tar.gz`
    const destinationImagePath = `root@${interfaceHost}:/var/lib/containers/storage/${checkpointId}-${containerInfo.Id}.tar.gz`
    const imageQueue = new AsyncBlockingQueue<string>()
    let imageQueueInit: (value: unknown) => void
    const imageQueueInitPromise = new Promise(resolve => {
        imageQueueInit = resolve
    })
    const imageWatcher = chokidar.watch(sourceImagePath)
    imageWatcher
        .on('all', (event, path) => {
            if ((event === 'add' || event == 'change') && imageQueue.isEmpty()) {
                imageQueue.enqueue(path)
            }
        })
        .on('ready', () => {
            imageQueueInit(null)
        })

    await imageQueueInitPromise

    const responses = await Promise.all([
        transferContainerImage(waitDestination, start, interfacePort, imageQueue, sourceImagePath, destinationImagePath, log),
        migrationInterface.checkpointContainer(start, containerInfo.Id, checkpointId, exit, imageQueue, log)
    ])

    await imageWatcher.close()

    return responses.reduce((prev: { [key: string]: number }, curr: any) => ({...prev, ...curr}), {})
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
    const {GraphDriver: {Name, Data: {MergedDir}}} = await migrationInterface.inspectContainer(containerInfo.Id, log)
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

export {migrate}
