import {FastifyReply, FastifyRequest} from "fastify"
import {MigrateRequestType} from "../schema"
import {execRsync} from "../lib"
import {FastifyBaseLogger} from "fastify/types/logger"
import {AsyncBlockingQueue} from "../queue"
import {migrationInterface} from "../interface";


async function save(request: FastifyRequest<{ Body: MigrateRequestType }>, reply: FastifyReply) {
    const start = Date.now()
    const responses = await migrationInterface.migrateImages(start, request.body)
    request.log.info(responses)
    return responses
}

async function transferImage(waitDestination: Promise<void>, start: number, interfacePort: string,
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
    return {image_layers_transfer: (Date.now() - start) / 1000, image_layers_delay: delay}
}


export {
    save,
    transferImage,
}
