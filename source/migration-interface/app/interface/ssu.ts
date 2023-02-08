import {FastifyBaseLogger} from "fastify/types/logger"
import {MigrationInterface} from "./index";
import {AsyncBlockingQueue, Lock} from "../queue";
import {ContainerInfo, requestAxios, waitForIt} from "../lib";
import {transferContainerImage} from "../api/migrate";
import chokidar from "chokidar";
import {MigrateRequestType} from "../schema";
import {INTERFACE_SSU} from "../const";


class SSU implements MigrationInterface {
    log
    name
    buildScratchImagePromise
    lock

    constructor(log: FastifyBaseLogger) {
        this.log = log
        this.name = INTERFACE_SSU
        this.buildScratchImagePromise = Promise.resolve()
        this.lock = new Lock()
    }

    async buildScratchImage() {
        throw new Error("Method not implemented.")
    }

    async pullImage(_image: string) {
        throw new Error("Method not implemented.")
    }

    async listContainer(_containerSpecString: string, _params: any = null) {
        throw new Error("Method not implemented.")
    }

    async inspectContainer(_containerName: string) {
        throw new Error("Method not implemented.")
    }

    async createContainer(_container: any): Promise<any> {
        throw new Error("Method not implemented.")
    }


    async startContainer(_name: string, _params: any = null) {
        throw new Error("Method not implemented.")
    }

    async checkpointContainer(_start: number, _name: string, _checkpointId: string, _exit: boolean, _imageQueue: AsyncBlockingQueue<string>): Promise<any> {
        throw new Error("Method not implemented.")
    }

    async restoreContainer(_fileName: string) {
        throw new Error("Method not implemented.")
    }

    async stopContainer(_name: string) {
        throw new Error("Method not implemented.")
    }

    async removeContainer(_name: string) {
        throw new Error("Method not implemented.")
    }

    async migrate(start: number, {checkpointId, interfaceHost, interfacePort, template}:
        {checkpointId: string, interfaceHost: string, interfacePort: string, template: any}): Promise<any> {
        const sourceImagePath = `/var/lib/kubelet/migration`
        const destinationImagePath = `root@${interfaceHost}:/var/lib/kubelet`


        await this.lock.lock();
        try {
            const waitDestination = waitForIt(interfaceHost, interfacePort, this.log)

            // todo check volume
            // let responses = await Promise.all([
            //         ...containerInfos.map(
            //             containerInfo => migrateOneContainerPind(checkpointId, interfaceHost, interfacePort,
            //                 containerInfo, exit, request.log)
            //         ),
            //         ...volumes.map(
            //             volume => transferVolume(interfaceHost, interfacePort, volume, request.log)
            //         )
            //     ])
            // request.log.info(responses)

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

            await Promise.all([
                transferContainerImage(waitDestination, start, interfacePort, imageQueue, sourceImagePath, destinationImagePath, this.log),
                requestAxios({
                    method: 'post',
                    url: `/Podmigrations`,
                    data: {
                        name: checkpointId,
                        action: 'checkpoint',
                        sourcePod: template.metadata.name,
                        template: {
                            metadata: template.metadata,
                            spec: template.spec
                        }
                    }
                }, this.log).then(() => {
                    // todo check if checkpointing is done
                    imageQueue.done = true
                })
            ])

            await imageWatcher.close()
        } finally {
            this.lock.unlock();
        }
    }

    async migrateContainer(waitDestination: Promise<void>, start: number, body: MigrateRequestType,
                           containerInfo: ContainerInfo, exit: boolean) {
        throw new Error("Method not implemented.");
    }

    async restore({checkpointId, template}: {checkpointId: string, template: any}): Promise<any> {
        return requestAxios({
            method: 'post',
            url: `/Podmigrations`,
            data: {
                name: checkpointId,
                action: 'restore',
                sourcePod: template.metadata.name,
                template: {
                    metadata: template.metadata,
                    spec: template.spec
                }
            }
        }, this.log)
    }
}

export {
    SSU
}
