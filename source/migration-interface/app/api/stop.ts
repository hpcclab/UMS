import {FastifyRequest} from "fastify"
import dotenv from "dotenv";
import {readFileSync} from "fs";
import {migrationInterface} from "../interface";
import {SPEC_CONTAINER_ANNOTATION} from "../const";

async function stop(request: FastifyRequest) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await migrationInterface.listContainer(config[SPEC_CONTAINER_ANNOTATION])
    await Promise.all(containerInfos.map(containerInfo => migrationInterface.stopContainer(containerInfo.Id)))
}

export {stop}
