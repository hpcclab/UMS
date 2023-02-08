import {FastifyBaseLogger} from "fastify/types/logger"
import {migrationInterface, MigrationInterface} from "./index";
import {AsyncBlockingQueue} from "../queue";
import {ContainerInfo, execBash, findDestinationFileSystemId, requestAxios, waitForIt} from "../lib";
import fs, {readFileSync} from "fs";
import dotenv from "dotenv";
import {transferContainerFS, transferContainerImage, transferVolume} from "../api/migrate";
import chokidar from "chokidar";
import {MigrateRequestType} from "../schema";
import {
    INTERFACE_DIND,
    SCRATCH_IMAGE,
    SPEC_CONTAINER_ANNOTATION,
    START_MODE_ACTIVE,
    START_MODE_ANNOTATION
} from "../const";


class DinD implements MigrationInterface {
    log
    name
    buildScratchImagePromise

    constructor(log: FastifyBaseLogger) {
        this.log = log
        this.name = INTERFACE_DIND
        this.buildScratchImagePromise = this.buildScratchImage()
    }

    static async isCompatible(log: FastifyBaseLogger): Promise<boolean> {
        try {
            const response = await requestAxios({
                method: 'get',
                url: '/_ping'
            }, log)
            return !!(response.headers && response.headers['server'] && response.headers['server'].includes('Docker'))
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
        const [repo, tag] = image.split(':')
        await requestAxios({
            method: 'post',
            url: `/images/create`,
            params: {fromImage: repo, tag: tag || 'latest'}
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
        await requestAxios({
            method: 'post',
            url: `/containers/${name}/checkpoints`,
            data: {CheckpointID: checkpointId, Exit: exit}
        }, this.log)
        imageQueue.done = true
        return {checkpoint: (Date.now() - start) / 1000}
    }

    async restoreContainer(fileName: string) {
        await execBash(`docker container restore -i /var/lib/containers/storage/${fileName} --tcp-established --file-locks`, this.log)
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
        const {destinationId, destinationFs} = findDestinationFileSystemId(containers, containerInfo)

        const sourceImagePath = `/var/lib/docker/containers/${containerInfo.Id}/checkpoints/${checkpointId}`
        const destinationImagePath = `root@${interfaceHost}:/var/lib/docker/containers/${destinationId}/checkpoints`
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
            transferContainerFS(waitDestination, start, interfaceHost, interfacePort, containerInfo, destinationFs, this.log),
            this.checkpointContainer(start, containerInfo.Id, checkpointId, exit, imageQueue)
        ])

        await imageWatcher.close()

        return responses.reduce((prev: { [key: string]: number }, curr: any) => ({...prev, ...curr}), {})
    }

    async restore({checkpointId}: {checkpointId: string}): Promise<any> {
        const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
        const containerInfos: any[] = await migrationInterface.listContainer(config[SPEC_CONTAINER_ANNOTATION], {all: true})
        return Promise.all(containerInfos.map(
            containerInfo => migrationInterface.startContainer(containerInfo.Id, {checkpoint: checkpointId}))
        )
    }
}

export {
    DinD
}
