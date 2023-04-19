import {FastifyBaseLogger} from "fastify/types/logger";
import {AsyncBlockingQueue} from "../queue";
import {ContainerInfo, HttpError, server} from "../lib";
import {DinD} from "./dind";
import dotenv from "dotenv";
import {readFileSync} from "fs";
import {PinD} from "./pind";
import {SSU} from "./ssu";
import {MigrateRequestType, RestoreRequestType} from "../schema";
import {INTERFACE_ANNOTATION, INTERFACE_DIND, INTERFACE_PIND, INTERFACE_SSU} from "../const";

interface MigrationInterface {
    log: FastifyBaseLogger;
    name: string;
    buildScratchImagePromise: Promise<any>;
    creatingContainers: string[];

    buildScratchImage(): Promise<any>;

    pullImage(image: string): Promise<any>;

    listContainer(containerSpecString: string, params: any): Promise<any>;

    inspectContainer(containerName: string): Promise<any>;

    createContainer(container: any): Promise<any>;

    startContainer(name: string, params: any): Promise<any>;

    checkpointContainer(start: number, name: string, checkpointId: string, exit: boolean, imageQueue: AsyncBlockingQueue<string>): Promise<any>;

    restoreContainer(fileName: string): Promise<any>;

    saveImage(start: number, name: string, checkpointId: string, imageQueue: AsyncBlockingQueue<string>): Promise<any>;

    loadImage(fileName: string): Promise<any>;

    stopContainer(name: string): Promise<any>;

    removeContainer(name: string): Promise<any>;

    migrate(start: number, body: MigrateRequestType): Promise<any>;

    migrateContainer(waitDestination: Promise<void>, start: number, body: MigrateRequestType,
                     containerInfo: ContainerInfo, exit: boolean): Promise<any>;

    migrateImages(start: number, body: MigrateRequestType): Promise<any>;

    migrateImage(waitDestination: Promise<void>, start: number, body: MigrateRequestType,
                     containerInfo: ContainerInfo): Promise<any>;

    restore(body: RestoreRequestType): Promise<any>;

    loadImages(body: RestoreRequestType): Promise<any>;
}

async function createMigrationInterface(log: FastifyBaseLogger) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    if (config[INTERFACE_ANNOTATION] === INTERFACE_PIND) return new PinD(log)
    if (config[INTERFACE_ANNOTATION] === INTERFACE_DIND) return new DinD(log)
    if (config[INTERFACE_ANNOTATION] === INTERFACE_SSU) return new SSU(log)
    if (await PinD.isCompatible(log)) return new PinD(log)
    if (await DinD.isCompatible(log)) return new DinD(log)
    throw new HttpError('Interface not found', 404)
}


const migrationInterface = await createMigrationInterface(server.log)


export {
    MigrationInterface,
    migrationInterface
}
