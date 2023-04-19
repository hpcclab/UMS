import {migrationInterface, MigrationInterface} from "./index";
import {FastifyBaseLogger} from "fastify/types/logger";
import {AsyncBlockingQueue} from "../queue";
import {ContainerInfo, execBash, requestAxios, waitForIt} from "../lib";
import fs, {readFileSync} from "fs";
import dotenv from "dotenv";
import {transferContainerImage, transferVolume} from "../api/migrate";
import chokidar from "chokidar";
import {MigrateRequestType} from "../schema";
import {
    INTERFACE_PIND,
    SCRATCH_IMAGE,
    SPEC_CONTAINER_ANNOTATION,
    START_MODE_ACTIVE,
    START_MODE_ANNOTATION
} from "../const";
import {transferImage} from "../api/save";

class PinD implements MigrationInterface {
    log
    name
    buildScratchImagePromise
    creatingContainers: string[]

    constructor(log: FastifyBaseLogger) {
        this.log = log
        this.name = INTERFACE_PIND
        this.buildScratchImagePromise = this.buildScratchImage()
        this.creatingContainers = []
    }

    static async isCompatible(log: FastifyBaseLogger): Promise<boolean> {
        try {
            const response = await requestAxios({
                method: 'get',
                url: '/_ping'
            }, log)
            return !!(response.headers && response.headers['server'] && response.headers['server'].includes('Libpod'))
        } catch (e) {
            return false
        }
    }

    async buildScratchImage() {
        try {
            await requestAxios({
                method: 'get',
                url: `/images/${SCRATCH_IMAGE}/json`,
            }, this.log);
        } catch (error: any) {
            if (error.statusCode == 404) {
                await requestAxios({
                    method: 'post',
                    url: `/build`,
                    params: {t: SCRATCH_IMAGE, q: true},
                    headers: {
                        'Content-Type': 'application/tar'
                    },
                    data: fs.createReadStream('/app/Dockerfile.tar.gz')
                }, this.log);
                return
            }
            throw error
        }
    }

    async pullImage(image: string) {
        const repo = image.split(':')
        const tag = repo.pop()
        await requestAxios({
            method: 'post',
            url: `/images/create`,
            params: {fromImage: repo.join(':'), tag: tag || 'latest'}
        }, this.log)
    }

    async listContainer(containerSpecString: string, params: any = null) {
        const response = await requestAxios({
            method: 'get',
            url: '/containers/json',
            params: params
        }, this.log)
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

    async inspectContainer(containerName: string) {
        const response = await requestAxios({
            method: 'get',
            url: `/containers/${containerName}/json`,
        }, this.log)
        return response.message
    }

    async createContainer(container: any): Promise<any> {
        try {
            const response = await requestAxios({
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
            }, this.log)
            return response.message
        } catch (error: any) {
            if (error.statusCode == 404) {
                await this.pullImage(container.image)
                return this.createContainer(container)
            }
            throw error
        }
    }


    async startContainer(name: string, params: any = null) {
        const response = await requestAxios({
            method: 'post',
            url: `/containers/${name}/start`,
            params: params
        }, this.log)
        return response.message
    }

    async checkpointContainer(start: number, name: string, checkpointId: string, exit: boolean, imageQueue: AsyncBlockingQueue<string>): Promise<any> {
        await execBash(`docker container checkpoint ${name} -P -e /var/lib/containers/storage/${checkpointId}-${name}/pre.tar.gz --tcp-established --file-locks`, this.log)
        const preCheckpoint = Date.now()
        await execBash(`docker container checkpoint ${name} --with-previous -e /var/lib/containers/storage/${checkpointId}-${name}/checkpoint.tar.gz --tcp-established --file-locks${exit ? "" : " -R"}`, this.log)
        imageQueue.done = true
        return {checkpoint: (Date.now() - preCheckpoint) / 1000, pre_checkpoint: (preCheckpoint - start) / 1000}
    }

    async restoreContainer(fileName: string) {
        await this.loadImage(fileName)
        await execBash(`docker container restore --import-previous /var/lib/containers/storage/${fileName}/pre.tar.gz -i /var/lib/containers/storage/${fileName}/checkpoint.tar.gz --tcp-established --file-locks`, this.log)
        return ""
    }

    async saveImage(start: number, name: string, checkpointId: string, imageQueue: AsyncBlockingQueue<string>) {
        const {ImageName} = await this.inspectContainer(name)
        await execBash(`docker save -q -o /var/lib/containers/storage/${checkpointId}-${name}/image.tar ${ImageName}`, this.log)
        imageQueue.done = true
        return {saveImage: (Date.now() - start) / 1000}
    }

    async loadImage(fileName: string) {
        await execBash(`docker load -q -i /var/lib/containers/storage/${fileName}/image.tar`, this.log)
        return ""
    }

    async stopContainer(name: string) {
        try {
            await requestAxios({
                method: 'post',
                url: `/containers/${name}/stop`
            }, this.log)
        } catch (error: any) {
            if (error.statusCode !== 304) {
                throw error
            }
        }
    }

    async removeContainer(name: string) {
        await requestAxios({
            method: 'delete',
            url: `/containers/${name}`,
            params: {v: true}
        }, this.log)
    }

    async migrate(start: number, body: MigrateRequestType): Promise<any> {
        const waitDestination = waitForIt(body.interfaceHost, body.interfacePort, this.log)

        const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
        const containerInfos: any[] = await migrationInterface.listContainer(config[SPEC_CONTAINER_ANNOTATION])
        const exit = config[START_MODE_ANNOTATION] !== START_MODE_ACTIVE
        return Promise.all([
            ...containerInfos.map(
                containerInfo => this.migrateContainer(waitDestination, start, body, containerInfo, exit)
            ),
            ...body.volumes.map(
                (volume: string) => transferVolume(waitDestination, start, body.interfaceHost, body.interfacePort, volume, this.log)
            )
        ])
    }

    async migrateContainer(waitDestination: Promise<void>, start: number, {checkpointId, interfaceHost, interfacePort, containers}:
                               MigrateRequestType,
                           containerInfo: ContainerInfo, exit: boolean) {
        const sourceImagePath = `/var/lib/containers/storage/${checkpointId}-${containerInfo.Id}`
        const destinationImagePath = `root@${interfaceHost}:/var/lib/containers/storage`
        await fs.promises.mkdir(sourceImagePath)
        const imageQueue = new AsyncBlockingQueue<string>()
        let imageQueueInit: (value: unknown) => void
        const imageQueueInitPromise = new Promise(resolve => {
            imageQueueInit = resolve
        })
        const imageWatcher = chokidar.watch(sourceImagePath)
        imageWatcher
            .on('all', (event, path) => {
                if ((event === 'add' || event == 'change') && imageQueue.isEmpty()) {
                    imageQueue.enqueue(path)
                }
            })
            .on('ready', () => {
                imageQueueInit(null)
            })

        await imageQueueInitPromise

        const responses = await Promise.all([
            transferContainerImage(waitDestination, start, interfacePort, imageQueue, sourceImagePath, destinationImagePath, this.log),
            this.checkpointContainer(start, containerInfo.Id, checkpointId, exit, imageQueue)
        ])

        await imageWatcher.close()

        return responses.reduce((prev: { [key: string]: number }, curr: any) => ({...prev, ...curr}), {})
    }

    async migrateImages(start: number, body: MigrateRequestType): Promise<any> {
        const waitDestination = waitForIt(body.interfaceHost, body.interfacePort, this.log)

        const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
        const containerInfos: any[] = await migrationInterface.listContainer(config[SPEC_CONTAINER_ANNOTATION])
        return Promise.all(containerInfos.map(
                containerInfo => this.migrateImage(waitDestination, start, body, containerInfo)
        ))
    }

    async migrateImage(waitDestination: Promise<void>, start: number, {checkpointId, interfaceHost, interfacePort, containers}:
                               MigrateRequestType, containerInfo: ContainerInfo) {
        const sourceImagePath = `/var/lib/containers/storage/${checkpointId}-${containerInfo.Id}-image`
        const destinationImagePath = `root@${interfaceHost}:/var/lib/containers/storage`
        await fs.promises.mkdir(sourceImagePath)
        const imageQueue = new AsyncBlockingQueue<string>()
        let imageQueueInit: (value: unknown) => void
        const imageQueueInitPromise = new Promise(resolve => {
            imageQueueInit = resolve
        })
        const imageWatcher = chokidar.watch(sourceImagePath)
        imageWatcher
            .on('all', (event, path) => {
                if ((event === 'add' || event == 'change') && imageQueue.isEmpty()) {
                    imageQueue.enqueue(path)
                }
            })
            .on('ready', () => {
                imageQueueInit(null)
            })

        await imageQueueInitPromise

        const responses = await Promise.all([
            transferImage(waitDestination, start, interfacePort, imageQueue, sourceImagePath, destinationImagePath, this.log),
            this.saveImage(start, containerInfo.Id, checkpointId, imageQueue)
        ])

        await imageWatcher.close()

        return responses.reduce((prev: { [key: string]: number }, curr: any) => ({...prev, ...curr}), {})
    }

    async restore({checkpointId}: {checkpointId: string}): Promise<any> {
        const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
        const containerInfos: any[] = await this.listContainer(config[SPEC_CONTAINER_ANNOTATION], {all: true})
        await Promise.all(containerInfos.map(async containerInfo => {
            try {
                await this.stopContainer(containerInfo.Id)
                await this.removeContainer(containerInfo.Id)
            } catch (error: any) {
                if (error.statusCode !== 404) {
                    throw error
                }
            }
        }))

        const fileList = await fs.promises.readdir('/var/lib/containers/storage/')
        return Promise.all(fileList
            .filter(fileName => fileName.startsWith(checkpointId))
            .map(fileName => this.restoreContainer(fileName))
        )
    }

    async loadImages({checkpointId}: {checkpointId: string}): Promise<any> {
        const fileList = await fs.promises.readdir('/var/lib/containers/storage/')
        return Promise.all(fileList
            .filter(fileName => fileName.startsWith(checkpointId))
            .map(fileName => this.loadImage(fileName))
        )
    }
}

export {
    PinD
}
