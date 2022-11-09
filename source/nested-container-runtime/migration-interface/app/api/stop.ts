import {FastifyRequest} from "fastify"
import {listContainer, stopContainer} from "../docker"
import dotenv from "dotenv";
import {readFileSync} from "fs";

async function stop(request: FastifyRequest) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await listContainer(config[process.env.SPEC_CONTAINER_ANNOTATION!], request.log)
    await Promise.all(containerInfos.map(containerInfo => stopContainer(containerInfo.Id, request.log)))
}

export {stop}
