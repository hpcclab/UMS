import {FastifyReply, FastifyRequest} from "fastify"
import {BaseRequestType} from "../schema"
import {requestAxios} from "../lib"

async function restore(request: FastifyRequest<{ Body: BaseRequestType }>, reply: FastifyReply) {
    const {checkpointId, template} = request.body

    let response = await requestAxios({
        method: 'post',
        url: `/Podmigrations`,
        data: {
            name: checkpointId,
            action: 'restore',
            sourcePod: template.metadata.name,
            template: {
                metadata: template.metadata,
                spec: template.spec
            }
        }
    }, request.log)
    request.log.info(response)
    reply.code(204)
    // todo lock and cleanup
}

export {restore}
