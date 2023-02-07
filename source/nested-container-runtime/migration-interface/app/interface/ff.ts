import {FastifyBaseLogger} from "fastify/types/logger"
import {MigrationInterface} from "./index";
import {AsyncBlockingQueue} from "../queue";
import {execBash, HttpError} from "../lib";


class FF implements MigrationInterface {
    name
    buildScratchImagePromise

    constructor(log: FastifyBaseLogger) {
        this.name = process.env.INTERFACE_FF || 'ff'
        this.buildScratchImagePromise = Promise.resolve()
    }

    static async isCompatible(log: FastifyBaseLogger): Promise<boolean> {
        try {
            const response = await execBash("ps -A -ww | grep -c [^]]fastfreeze", log)
            console.log(response) // todo
            return !(!/^\d+$/.test(response) || parseInt(response, 10) < 1);
        } catch (e) {
            return false
        }
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
        // todo
    }

    async restoreContainer(_fileName: string, _log: FastifyBaseLogger) {
        // todo
    }

    async stopContainer(_name: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }

    async removeContainer(_name: string, _log: FastifyBaseLogger) {
        throw new HttpError('Not implemented', 501)
    }
}

export {
    FF
}
