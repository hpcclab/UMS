import {FastifyReply, FastifyRequest} from "fastify"
import {MigrateRequestType} from "../schema"
import {execRsync, requestAxios, waitForIt} from "../lib"
import {FastifyBaseLogger} from "fastify/types/logger"
import chokidar from "chokidar"
import {AsyncBlockingQueue, lock} from "../queue"


async function migrate(request: FastifyRequest<{ Body: MigrateRequestType }>, reply: FastifyReply) {
    const {checkpointId, interfaceHost, interfacePort, template} = request.body
    const sourceImagePath = `/var/lib/kubelet/migration`
    const destinationImagePath = `root@${interfaceHost}:/var/lib/kubelet`


    await lock.lock();
    try {
        await waitForIt(interfaceHost, interfacePort, request.log)

        // todo check volume
        // let responses = await Promise.all([
        //         ...containerInfos.map(
        //             containerInfo => migrateOneContainerPind(checkpointId, interfaceHost, interfacePort,
        //                 containerInfo, exit, request.log)
        //         ),
        //         ...volumes.map(
        //             volume => transferVolume(interfaceHost, interfacePort, volume, request.log)
        //         )
        //     ])
        // request.log.info(responses)

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

        await Promise.all([
            transferContainerImage(interfacePort, imageQueue, sourceImagePath, destinationImagePath, request.log),
            requestAxios({
                method: 'post',
                url: `/Podmigrations`,
                data: {
                    name: checkpointId,
                    action: 'checkpoint',
                    sourcePod: template.metadata.name,
                    template: {
                        metadata: template.metadata,
                        spec: template.spec
                    }
                }
            }, request.log).then(() => {
                // todo check if checkpointing is done
                imageQueue.done = true
            })
        ])

        await imageWatcher.close()

        reply.code(204)
    } finally {
        lock.unlock();
    }
}

async function transferContainerImage(interfacePort: string, queue: AsyncBlockingQueue<string>, sourcePath: string,
                                      destinationPath: string, log: FastifyBaseLogger) {
    while (true) {
        if (queue.done) break
        await queue.dequeue()
        await execRsync(interfacePort, sourcePath, destinationPath, log)
    }

    while (!queue.isEmpty()) {
        await queue.dequeue()
    }

    await execRsync(interfacePort, sourcePath, destinationPath, log)
}

async function transferVolume(interfaceHost: string, interfacePort: string, volume: any, log: FastifyBaseLogger) {
    await execRsync(interfacePort, volume, `root@${interfaceHost}:/mount`, log)
}

export {migrate}
