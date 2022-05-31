import {FastifyReply, FastifyRequest} from "fastify";
import {inspectContainer} from "../docker";
import {CreateRequestType} from "../schema";

async function probe(request: FastifyRequest<{Params: CreateRequestType}>, reply: FastifyReply) {
    const {containerName} = request.params

    const {State} = await inspectContainer(containerName, request.log)
    const {Status, ExitCode} = State

    if (Status === "created") {
        reply.code(204)
        return
    } else if (Status === "exited" || Status === "dead") {
        reply.code(503)
        return ExitCode || 1
    } else {
        return
    }
}

export {probe}
