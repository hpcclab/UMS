import {FastifyBaseLogger} from "fastify/types/logger"
import {MigrationInterface} from "./index";
import {AsyncBlockingQueue} from "../queue";
import {ContainerInfo, execBash} from "../lib";
import {MigrateRequestType} from "../schema";
import {INTERFACE_FF} from "../const";


class FF implements MigrationInterface {
    log
    name
    buildScratchImagePromise

    constructor(log: FastifyBaseLogger) {
        this.log = log
        this.name = INTERFACE_FF
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

    async buildScratchImage() {
        throw new Error("Method not implemented.")
    }

    async pullImage() {
        throw new Error("Method not implemented.")
    }

    async listContainer() {
        throw new Error("Method not implemented.")
    }

    async inspectContainer() {
        throw new Error("Method not implemented.")
    }

    async createContainer(): Promise<any> {
        throw new Error("Method not implemented.")
    }


    async startContainer() {
        throw new Error("Method not implemented.")
    }

    async checkpointContainer(): Promise<any> {
        throw new Error("Method not implemented.")
    }

    async restoreContainer() {
        throw new Error("Method not implemented.")
    }

    async stopContainer() {
        throw new Error("Method not implemented.")
    }

    async removeContainer() {
        throw new Error("Method not implemented.")
    }

    migrate(start: number): Promise<any> {
        // todo
        return Promise.resolve(undefined);
    }

    async migrateContainer() {
        throw new Error("Method not implemented.");
    }

    restore(): Promise<any> {
        // todo
        return Promise.resolve(undefined);
    }
}

export {
    FF
}
