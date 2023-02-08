import {FastifyReply, FastifyRequest} from "fastify"
import dotenv from "dotenv";
import {readFileSync} from "fs";
import {migrationInterface} from "../interface";
import {SPEC_CONTAINER_ANNOTATION} from "../const";

async function list(request: FastifyRequest, reply: FastifyReply) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await migrationInterface.listContainer(config[SPEC_CONTAINER_ANNOTATION], {all: true})
    return Promise.all(containerInfos.map(containerInfo => getFs(containerInfo.Id)))
}

async function getFs(containerName: string) {
    const {Id, Name, GraphDriver: {Name: driverName, Data: {UpperDir}}} = await migrationInterface.inspectContainer(containerName)
    const fs = driverName === 'overlay2' ? UpperDir : null
    return {name: Name, id: Id, fs: fs}
}

export {list}
