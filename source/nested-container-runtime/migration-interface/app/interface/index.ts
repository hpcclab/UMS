import {FastifyBaseLogger} from "fastify/types/logger";
import {AsyncBlockingQueue} from "../queue";

interface MigrationInterface {
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


export {
    MigrationInterface
}
