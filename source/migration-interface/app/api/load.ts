import {FastifyReply, FastifyRequest} from "fastify"
import {RestoreRequestType} from "../schema"
import {migrationInterface} from "../interface";

async function load(request: FastifyRequest<{ Body: RestoreRequestType }>, reply: FastifyReply) {
    // todo check start annotations
    const responses = await migrationInterface.loadImages(request.body)
    request.log.info(responses)
    reply.code(204)
}

export {load}
