import {FastifyRequest} from "fastify";
import {listContainer, stopContainer} from "../docker";

async function stop(request: FastifyRequest) {
    const containerInfos: any[] = await listContainer(request.log);
    await Promise.all(containerInfos.map(containerInfo => stopContainer(containerInfo.Id, request.log)))
}

export { stop }
