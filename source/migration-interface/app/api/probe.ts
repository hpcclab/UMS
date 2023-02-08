import {FastifyReply, FastifyRequest} from "fastify"
import {CreateRequestType} from "../schema"
import dotenv from "dotenv"
import {readFileSync} from "fs"
import {migrationInterface} from "../interface";
import {START_MODE_ANNOTATION, START_MODE_FAIL, START_MODE_NULL} from "../const";

async function probe(request: FastifyRequest<{ Params: CreateRequestType }>, reply: FastifyReply) {
    const {containerName} = request.params

    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const startMode = config[START_MODE_ANNOTATION]

    if (startMode === START_MODE_FAIL) {
        reply.code(403)
        return null
    } else if (startMode === START_MODE_NULL) {
        reply.code(204)
        return
    }

    const {State} = await migrationInterface.inspectContainer(containerName)
    const {Status, ExitCode} = State

    if (Status === "created") {
        reply.code(204)
        return
    } else if (Status === "exited" || Status === "dead") {
        reply.code(503)
        return ExitCode || 1
    } else {
        return ""
    }
}

export {probe}
