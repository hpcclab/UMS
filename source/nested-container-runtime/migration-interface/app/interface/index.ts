import {FastifyBaseLogger} from "fastify/types/logger";
import {AsyncBlockingQueue} from "../queue";
import {HttpError, server} from "../lib";
import {DinD} from "./dind";
import dotenv from "dotenv";
import {readFileSync} from "fs";
import {PinD} from "./pind";
import {FF} from "./ff";

interface MigrationInterface {
    name: string;
    buildScratchImagePromise: Promise<any>;

    buildScratchImage(log: FastifyBaseLogger): Promise<any>;

    pullImage(image: string, log: FastifyBaseLogger): Promise<any>;

    listContainer(containerSpecString: string, log: FastifyBaseLogger, params: any): Promise<any>;

    inspectContainer(containerName: string, log: FastifyBaseLogger): Promise<any>;

    createContainer(container: any, log: FastifyBaseLogger): Promise<any>;

    startContainer(name: string, log: FastifyBaseLogger, params: any): Promise<any>;

    checkpointContainer(start: number, name: string, checkpointId: string, exit: boolean, imageQueue: AsyncBlockingQueue<string>, log: FastifyBaseLogger): Promise<any>;

    restoreContainer(fileName: string, log: FastifyBaseLogger): Promise<any>;

    stopContainer(name: string, log: FastifyBaseLogger): Promise<any>;

    removeContainer(name: string, log: FastifyBaseLogger): Promise<any>;
}

async function createMigrationInterface(log: FastifyBaseLogger) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    if (config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_PIND) return new PinD(log)
    if (config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_DIND) return new DinD(log)
    if (config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_FF) return new DinD(log)
    if (config[process.env.INTERFACE_ANNOTATION!] === process.env.INTERFACE_SSU) return new DinD(log)
    if (await PinD.isCompatible(log)) return new PinD(log)
    if (await DinD.isCompatible(log)) return new DinD(log)
    if (await FF.isCompatible(log)) return new FF(log)
    throw new HttpError('Interface not found', 404)
}


const migrationInterface = await createMigrationInterface(server.log)


export {
    MigrationInterface,
    migrationInterface
}
