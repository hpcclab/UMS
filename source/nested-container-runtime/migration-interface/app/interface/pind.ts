import {MigrationInterface} from "./index";
import {FastifyBaseLogger} from "fastify/types/logger";
import {AsyncBlockingQueue} from "../queue";
import {execBash, requestDocker} from "../lib";
import fs from "fs";

class PinD implements MigrationInterface {
    name
    buildScratchImagePromise

    constructor(log: FastifyBaseLogger) {
        this.name = process.env.INTERFACE_PIND || 'pind'
        this.buildScratchImagePromise = this.buildScratchImage(log)
    }

    static async isCompatible(log: FastifyBaseLogger): Promise<boolean> {
        try {
            const response = await requestDocker({
                method: 'get',
                url: '/_ping'
            }, log)
            return !!(response.headers && response.headers['server'] && response.headers['server'].includes('Libpod'))
        } catch (e) {
            return false
        }
    }

    async buildScratchImage(log: FastifyBaseLogger) {
        try {
            await requestDocker({
                method: 'get',
                url: `/images/${process.env.SCRATCH_IMAGE}/json`,
            }, log);
        } catch (error: any) {
            if (error.statusCode == 404) {
                await requestDocker({
                    method: 'post',
                    url: `/build`,
                    params: {t: process.env.SCRATCH_IMAGE, q: true},
                    headers: {
                        'Content-Type': 'application/tar'
                    },
                    data: fs.createReadStream('/app/Dockerfile.tar.gz')
                }, log);
                return
            }
            throw error
        }
    }

    async pullImage(image: string, log: FastifyBaseLogger) {
        const [repo, tag] = image.split(':')
        await requestDocker({
            method: 'post',
            url: `/images/create`,
            params: {fromImage: repo, tag: tag || 'latest'}
        }, log)
    }

    async listContainer(containerSpecString: string, log: FastifyBaseLogger, params: any = null) {
        const response = await requestDocker({
            method: 'get',
            url: '/containers/json',
            params: params
        }, log)
        const containerSpec = JSON.parse(containerSpecString
            .replace(/\\\"/g, "\"").replace(/\\\\/g, "\\"))
        return response.message.filter((containerInfo: { Names: string[] }) => {
            for (const container of containerSpec) {
                if (containerInfo.Names.includes(`/${container.name}`)) {
                    return true
                }
            }
            return false
        })
    }

    async inspectContainer(containerName: string, log: FastifyBaseLogger) {
        const response = await requestDocker({
            method: 'get',
            url: `/containers/${containerName}/json`,
        }, log)
        return response.message
    }

    async createContainer(container: any, log: FastifyBaseLogger): Promise<any> {
        try {
            const response = await requestDocker({
                method: 'post',
                url: `/containers/create`,
                params: {name: container.name},
                data: {
                    Env: container.hasOwnProperty('env') ? container.env.map((e: { name: any; value: any }) => `${e.name}=${e.value}`) : null,
                    Cmd: container.hasOwnProperty('command') ? container.command : null,
                    Image: container.image,
                    HostConfig: {
                        SecurityOpt: ['seccomp:unconfined'],
                        Binds: container.hasOwnProperty('volumeMounts') ?
                            container.volumeMounts.map((mount: { name: string, mountPath: string }) => `/mount/${mount.name}:${mount.mountPath}`)
                            : null,
                        PortBindings: container.hasOwnProperty('ports') ?
                            container.ports.reduce((obj: { [x: string]: { HostPort: string }[] }, v: {
                                protocol: string
                                containerPort: string
                            }) => {
                                const protocol = v.hasOwnProperty('protocol') ? v.protocol.toLowerCase() : 'tcp'
                                obj[`${v.containerPort}/${protocol}`] = [{HostPort: v.containerPort.toString()}]
                                return obj
                            }, {}) : null
                    }
                }
            }, log)
            return response.message
        } catch (error: any) {
            if (error.statusCode == 404) {
                await this.pullImage(container.image, log)
                return this.createContainer(container, log)
            }
            throw error
        }
    }


    async startContainer(name: string, log: FastifyBaseLogger, params: any = null) {
        const response = await requestDocker({
            method: 'post',
            url: `/containers/${name}/start`,
            params: params
        }, log)
        return response.message
    }

    async checkpointContainer(start: number, name: string, checkpointId: string, exit: boolean, imageQueue: AsyncBlockingQueue<string>, log: FastifyBaseLogger): Promise<any> {
        await execBash(`docker container checkpoint ${name} -e /var/lib/containers/storage/${checkpointId}-${name}.tar.gz --tcp-established --file-locks${exit ? "" : " -R"}`, log)
        imageQueue.done = true
        return {checkpoint: (Date.now() - start) / 1000}
    }

    async restoreContainer(fileName: string, log: FastifyBaseLogger) {
        await execBash(`docker container restore -i /var/lib/containers/storage/${fileName} --tcp-established --file-locks`, log)
        return ""
    }

    async stopContainer(name: string, log: FastifyBaseLogger) {
        try {
            await requestDocker({
                method: 'post',
                url: `/containers/${name}/stop`
            }, log)
        } catch (error: any) {
            if (error.statusCode !== 304) {
                throw error
            }
        }
    }

    async removeContainer(name: string, log: FastifyBaseLogger) {
        await requestDocker({
            method: 'delete',
            url: `/containers/${name}`,
            params: {v: true}
        }, log)
    }
}

export {
    PinD
}