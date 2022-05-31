import {FastifyReply, FastifyRequest} from "fastify";
import {inspectContainer, listContainer} from "../docker";
import {FastifyLoggerInstance} from "fastify/types/logger";

async function list(request: FastifyRequest, reply: FastifyReply) {
    const containerInfos: any[] = await listContainer(request.log);
    return await Promise.all(containerInfos.map(containerInfo => getFs(containerInfo.Id, request.log)))
}

async function getFs(containerName: string, log: FastifyLoggerInstance) {
    const {Id, Name, GraphDriver: {Name: driverName, Data: {UpperDir}}} = await inspectContainer(containerName, log)
    const fs = driverName === 'overlay2' ? UpperDir : null
    return {name: Name, id: Id, fs: fs}
}

export {list}
