import {FastifyReply, FastifyRequest} from "fastify"
import {BaseRequestType} from "../schema"
import dotenv from "dotenv"
import {readFileSync} from "fs"
import * as fs from "fs"
import {migrationInterface} from "../interface";

async function restore(request: FastifyRequest<{ Body: BaseRequestType }>, reply: FastifyReply) {
    const {checkpointId} = request.body
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const pind = config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_PIND
    // todo check start annotations

    let responses
    if (pind) {
        const containerInfos: any[] = await migrationInterface.listContainer(config[process.env.SPEC_CONTAINER_ANNOTATION!], request.log, {all: true})
        await Promise.all(containerInfos.map(async containerInfo => {
            try {
                await migrationInterface.stopContainer(containerInfo.Id, request.log)
                await migrationInterface.removeContainer(containerInfo.Id, request.log)
            } catch (error: any) {
                if (error.statusCode !== 404) {
                    throw error
                }
            }
        }))

        const fileList = await fs.promises.readdir('/var/lib/containers/storage/')
        responses = await Promise.all(fileList
            .filter(fileName => fileName.startsWith(checkpointId))
            .map(fileName => migrationInterface.restoreContainer(fileName, request.log))
        )
    } else {
        const containerInfos: any[] = await migrationInterface.listContainer(config[process.env.SPEC_CONTAINER_ANNOTATION!], request.log, {all: true})
        responses = await Promise.all(containerInfos.map(
            containerInfo => migrationInterface.startContainer(containerInfo.Id, request.log, {checkpoint: checkpointId}))
        )
    }
    request.log.info(responses)
    reply.code(204)
}

export {restore}
