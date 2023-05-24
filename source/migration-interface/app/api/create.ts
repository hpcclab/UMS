import {FastifyReply, FastifyRequest} from "fastify"
import {CreateRequestType} from "../schema"
import dotenv from "dotenv"
import {readFileSync} from "fs"
import {migrationInterface} from "../interface";
import {
    SCRATCH_IMAGE,
    SPEC_CONTAINER_ANNOTATION, START_MODE_ACTIVE,
    START_MODE_ANNOTATION,
    START_MODE_FAIL,
    START_MODE_NULL
} from "../const";

async function create(request: FastifyRequest<{ Params: CreateRequestType }>, reply: FastifyReply) {
    const {containerName} = request.params

    if (migrationInterface.creatingContainers.includes(containerName)) {
        reply.code(204)
        return
    } else {
        migrationInterface.creatingContainers.push(containerName)
    }

    try {
        await migrationInterface.stopContainer(containerName)
        await migrationInterface.removeContainer(containerName)
    } catch (error: any) {
        if (error.statusCode !== 404) {
            throw error
        }
    }

    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const startMode = config[START_MODE_ANNOTATION]

    if (startMode === START_MODE_FAIL) {
        reply.code(403)
        return null
    } else if (startMode === START_MODE_NULL) {
        reply.code(204)
        return
    }

    try {
        const containerSpec = JSON.parse(config[SPEC_CONTAINER_ANNOTATION]
            .replace(/\\\"/g, "\"").replace(/\\\\/g, "\\"))
            .find((container: { name: string }) => container.name === containerName)

        if (containerSpec.image.split(':')[0] === SCRATCH_IMAGE) {
            await migrationInterface.buildScratchImagePromise
        } else if (containerSpec.imagePullPolicy === 'Always') {
            await migrationInterface.pullImage(containerSpec.image)
        }

        await migrationInterface.createContainer(containerSpec)

        if (startMode === START_MODE_ACTIVE) {
            return migrationInterface.startContainer(containerName)
        } else {
            reply.code(204)
        }
    } finally {
        const index = migrationInterface.creatingContainers.indexOf(containerName);
        migrationInterface.creatingContainers.splice(index, 1)
    }
}

export {create}
