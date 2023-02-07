import {FastifyReply, FastifyRequest} from "fastify"
import {CreateRequestType} from "../schema"
import dotenv from "dotenv"
import {readFileSync} from "fs"
import {migrationInterface} from "../interface";

async function create(request: FastifyRequest<{ Params: CreateRequestType }>, reply: FastifyReply) {
    const {containerName} = request.params

    try {
        await migrationInterface.stopContainer(containerName, request.log)
        await migrationInterface.removeContainer(containerName, request.log)
    } catch (error: any) {
        if (error.statusCode !== 404) {
            throw error
        }
    }

    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const startMode = config[process.env.START_MODE_ANNOTATION!]

    if (startMode === process.env.START_MODE_FAIL) {
        reply.code(403)
        return null
    } else if (startMode === process.env.START_MODE_NULL) {
        reply.code(204)
        return
    }

    const containerSpec = JSON.parse(config[process.env.SPEC_CONTAINER_ANNOTATION!]
        .replace(/\\\"/g, "\"").replace(/\\\\/g, "\\"))
        .find((container: { name: string }) => container.name === containerName)

    if (containerSpec.image.split(':')[0] === process.env.SCRATCH_IMAGE) {
        await migrationInterface.buildScratchImagePromise
    } else if (containerSpec.imagePullPolicy === 'Always') {
        await migrationInterface.pullImage(containerSpec.image, request.log)
    }

    await migrationInterface.createContainer(containerSpec, request.log)

    if (startMode === process.env.START_MODE_ACTIVE) {
        return migrationInterface.startContainer(containerName, request.log)
    } else {
        reply.code(204)
    }
}

export {create}
