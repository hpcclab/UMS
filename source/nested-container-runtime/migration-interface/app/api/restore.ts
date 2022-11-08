import {FastifyReply, FastifyRequest} from "fastify"
import {BaseRequestType} from "../schema"
import {listContainer, startContainer, restoreContainer, stopContainer, removeContainer} from "../docker"
import {HttpError} from "../lib"
import dotenv from "dotenv"
import {readFileSync} from "fs"
import * as fs from "fs"

async function restore(request: FastifyRequest<{ Body: BaseRequestType }>, reply: FastifyReply) {
    const {checkpointId} = request.body
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const pind = config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_PIND

    let responses
    if (pind) {
        const containerInfos: any[] = await listContainer(request.log, {all: true})
        await Promise.all(containerInfos.map(async containerInfo => {
            try {
                await stopContainer(containerInfo.Id, request.log)
                await removeContainer(containerInfo.Id, request.log)
            } catch (error: any) {
                if (error.statusCode !== 404) {
                    throw error
                }
            }
        }))

        const fileList = await fs.promises.readdir('/var/lib/containers/storage/')
        responses = await Promise.all(fileList
            .filter(fileName => fileName.startsWith(checkpointId))
            .map(fileName => restoreContainer(fileName, request.log))
        )
    } else {
        const containerInfos: any[] = await listContainer(request.log, {filters: {status: ["created", "exited"]}})
        if (containerInfos.length === 0) {
            throw new HttpError('No container found', 404)
        }
        responses = await Promise.all(containerInfos.map(
            containerInfo => startContainer(containerInfo.Id, request.log, {checkpoint: checkpointId}))
        )
    }
    request.log.info(responses)
    reply.code(204)
}

export {restore}
