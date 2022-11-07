import {FastifyRequest} from "fastify"
import {BaseRequestType} from "../schema"
import {listContainer, startContainer} from "../docker"
import {HttpError} from "../lib"

async function restore(request: FastifyRequest<{ Body: BaseRequestType }>) {
    const containerInfos: any[] = await listContainer(request.log, {filters: {status: ["created", "exited"]}})
    if (containerInfos.length === 0) {
        throw new HttpError('No container found', 404)
    }
    const {checkpointId} = request.body
    return await Promise.all(containerInfos.map(containerInfo => startContainer(containerInfo.Id, request.log, {checkpoint: checkpointId})))
}

export {restore}
