import {FastifyReply, FastifyRequest} from "fastify"
import {inspectContainer, listContainer} from "../docker"
import {FastifyBaseLogger} from "fastify/types/logger"
import dotenv from "dotenv";
import {readFileSync} from "fs";

async function list(request: FastifyRequest, reply: FastifyReply) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await listContainer(config[process.env.SPEC_CONTAINER_ANNOTATION!], request.log, {all: true})
    return Promise.all(containerInfos.map(containerInfo => getFs(containerInfo.Id, request.log)))
}

async function getFs(containerName: string, log: FastifyBaseLogger) {
    const {Id, Name, GraphDriver: {Name: driverName, Data: {UpperDir}}} = await inspectContainer(containerName, log)
    const fs = driverName === 'overlay2' ? UpperDir : null
    return {name: Name, id: Id, fs: fs}
}

export {list}
