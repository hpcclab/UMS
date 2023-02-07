import {FastifyRequest} from "fastify"
import dotenv from "dotenv";
import {readFileSync} from "fs";
import {migrationInterface} from "../interface";

async function stop(request: FastifyRequest) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await migrationInterface.listContainer(config[process.env.SPEC_CONTAINER_ANNOTATION!], request.log)
    await Promise.all(containerInfos.map(containerInfo => migrationInterface.stopContainer(containerInfo.Id, request.log)))
}

export {stop}
