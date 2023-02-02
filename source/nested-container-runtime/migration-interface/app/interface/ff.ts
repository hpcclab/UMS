import {FastifyBaseLogger} from "fastify/types/logger"
import {MigrationInterface} from "./index";
import {AsyncBlockingQueue} from "../queue";
import {server} from "../lib";


class FF implements MigrationInterface {
    buildScratchImagePromise = this.buildScratchImage(server.log)

    async buildScratchImage(_log: FastifyBaseLogger) {
        // pass
    }

    async pullImage(_image: string, _log: FastifyBaseLogger) {
        // pass
    }

    async listContainer(_containerSpecString: string, _log: FastifyBaseLogger, _params: any = null) {
        // pass
    }

    async inspectContainer(_containerName: string, _log: FastifyBaseLogger) {
        // pass
    }

    async createContainer(_container: any, _log: FastifyBaseLogger): Promise<any> {
        // pass
    }


    async startContainer(_name: string, _log: FastifyBaseLogger, _params: any = null) {
        // pass
    }

    async checkpointContainer(_start: number, _name: string, _checkpointId: string, _exit: boolean, _imageQueue: AsyncBlockingQueue<string>, _log: FastifyBaseLogger): Promise<any> {
        // pass
    }

    async restoreContainer(_fileName: string, _log: FastifyBaseLogger) {
        // pass
    }

    async stopContainer(_name: string, _log: FastifyBaseLogger) {
        // pass
    }

    async removeContainer(_name: string, _log: FastifyBaseLogger) {
        // pass
    }
}

export {
    FF
}
