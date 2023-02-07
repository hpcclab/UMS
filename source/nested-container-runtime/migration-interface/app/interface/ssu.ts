import {FastifyBaseLogger} from "fastify/types/logger"
import {MigrationInterface} from "./index";
import {AsyncBlockingQueue} from "../queue";
import {HttpError} from "../lib";


class SSU implements MigrationInterface {
    name
    buildScratchImagePromise

    constructor(log: FastifyBaseLogger) {
        this.name = process.env.INTERFACE_SSU || 'ssu'
        this.buildScratchImagePromise = Promise.resolve()
    }

    async buildScratchImage(_log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }

    async pullImage(_image: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }

    async listContainer(_containerSpecString: string, _log: FastifyBaseLogger, _params: any = null) {
        throw new HttpError('Not implemented', 501)
    }

    async inspectContainer(_containerName: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }

    async createContainer(_container: any, _log: FastifyBaseLogger): Promise<any> {
        throw new HttpError('Not implemented', 501)
    }


    async startContainer(_name: string, _log: FastifyBaseLogger, _params: any = null) {
        throw new HttpError('Not implemented', 501)
    }

    async checkpointContainer(_start: number, _name: string, _checkpointId: string, _exit: boolean, _imageQueue: AsyncBlockingQueue<string>, _log: FastifyBaseLogger): Promise<any> {
        throw new HttpError('Not implemented', 501)
    }

    async restoreContainer(_fileName: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }

    async stopContainer(_name: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }

    async removeContainer(_name: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }
}

export {
    SSU
}
