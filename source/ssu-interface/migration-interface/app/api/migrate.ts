import {FastifyReply, FastifyRequest} from "fastify"
import {MigrateRequestType} from "../schema"
import {execRsync, requestAxios, waitForIt} from "../lib"
import {FastifyBaseLogger} from "fastify/types/logger"
import chokidar from "chokidar"
import {AsyncBlockingQueue} from "../queue"


async function migrate(request: FastifyRequest<{ Body: MigrateRequestType }>, reply: FastifyReply) {
    const {checkpointId, interfaceHost, interfacePort, template} = request.body

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

    const sourceImagePath = `/var/lib/kubelet/migration`
    const destinationImagePath = `root@${interfaceHost}:/var/lib/kubelet`
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
            imageQueue.done = true
        })
    ])

    console.log('m')

    await imageWatcher.close()

    console.log('n')

    reply.code(204)
}

async function transferContainerImage(interfacePort: string, queue: AsyncBlockingQueue<string>, sourcePath: string,
                                      destinationPath: string, log: FastifyBaseLogger) {
    while (true) {
        console.log('a')
        if (queue.done) break
        console.log('b')
        await queue.dequeue()
        console.log('c')
        await execRsync(interfacePort, sourcePath, destinationPath, log)
        console.log('d')
    }

    console.log('e')

    while (!queue.isEmpty()) {
        console.log('f')
        await queue.dequeue()
        console.log('g')
    }

    console.log('h')

    await execRsync(interfacePort, sourcePath, destinationPath, log)

    console.log('i')
}

async function transferVolume(interfaceHost: string, interfacePort: string, volume: any, log: FastifyBaseLogger) {
    await execRsync(interfacePort, volume, `root@${interfaceHost}:/mount`, log)
}

export {migrate}
