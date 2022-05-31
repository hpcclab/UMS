import {FastifyRequest} from "fastify";
import {BaseRequestType} from "../schema";
import {listContainer, startContainer} from "../docker";

async function restore(request: FastifyRequest<{Body: BaseRequestType}>) {
    const containerInfos: any[] = await listContainer(request.log, {filters: {statusCode: ["created", "exited"]}})
    if (containerInfos === []) {
        throw {statusCode: 404, message: 'No container found'}
    }
    const { checkpointId } = request.body;
    return await Promise.all(containerInfos.map(containerInfo => startContainer(containerInfo.Id, request.log, {checkpoint: checkpointId})))
}

export { restore }
