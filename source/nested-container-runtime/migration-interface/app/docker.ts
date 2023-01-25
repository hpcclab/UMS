import {AxiosInstance, AxiosRequestConfig} from "axios"
import {FastifyBaseLogger} from "fastify/types/logger"
import {execBash, HttpError, waitForIt} from "./lib"
import {AsyncBlockingQueue} from "./queue"

const axios: AxiosInstance = require("axios").default.create({
    baseURL: `http://${process.env.DOCKER_HOST}`
})


async function requestDocker(config: AxiosRequestConfig, log: FastifyBaseLogger) {
    try {
        const dockerHost = `${process.env.DOCKER_HOST}`.split(':')
        await waitForIt(dockerHost[0], dockerHost[1], log)
        const response = await axios(config)
        log.debug(JSON.stringify(response.data))
        return {statusCode: response.status, message: response.data}
    } catch (error: any) {
        log.debug(JSON.stringify(error))
        if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            if (error.response.status > 399) throw new HttpError(JSON.stringify(error.response.data), error.response.status)
            return {statusCode: error.response.status, message: JSON.stringify(error.response.data)}
        } else if (error.request) {
            // The request was made but no response was received
            // `error.request` is an instance of XMLHttpRequest in the browser and an instance of
            // http.ClientRequest in node.js
            throw new HttpError('The request was made but no response was received', 502)
        } else {
            // Something happened in setting up the request that triggered an Error
            throw new HttpError(error.message, 500)
        }
    }
}

async function pullImage(image: string, log: FastifyBaseLogger) {
    const [repo, tag] = image.split(':')
    await requestDocker({
        method: 'post',
        url: `/images/create`,
        params: {fromImage: repo, tag: tag || 'latest'}
    }, log)
}

async function listContainer(containerSpecString: string, log: FastifyBaseLogger, params: any = null) {
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

async function inspectContainer(containerName: string, log: FastifyBaseLogger) {
    const response = await requestDocker({
        method: 'get',
        url: `/containers/${containerName}/json`,
    }, log)
    return response.message
}

async function createContainer(container: any, log: FastifyBaseLogger): Promise<any> {
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
            await pullImage(container.image, log)
            return createContainer(container, log)
        }
        throw error
    }
}


async function startContainer(name: string, log: FastifyBaseLogger, params: any = null) {
    const response = await requestDocker({
        method: 'post',
        url: `/containers/${name}/start`,
        params: params
    }, log)
    return response.message
}

async function checkpointContainerDind(start: number, name: string, checkpointId: string, exit: boolean, imageQueue: AsyncBlockingQueue<string>, log: FastifyBaseLogger): Promise<any> {
    await requestDocker({
        method: 'post',
        url: `/containers/${name}/checkpoints`,
        data: {CheckpointID: checkpointId, Exit: exit}
    }, log)
    imageQueue.done = true
    return {checkpoint: (Date.now() - start) / 1000}
}

async function checkpointContainerPind(start: number, name: string, checkpointId: string, exit: boolean, imageQueue: AsyncBlockingQueue<string>, log: FastifyBaseLogger): Promise<any> {
    await execBash(`docker container checkpoint ${name} -e /var/lib/containers/storage/${checkpointId}-${name}.tar.gz --tcp-established --file-locks${exit ? "" : " -R"}`, log)
    imageQueue.done = true
    return {checkpoint: (Date.now() - start) / 1000}
}

async function restoreContainer(fileName: string, log: FastifyBaseLogger) {
    await execBash(`docker container restore -i /var/lib/containers/storage/${fileName} --tcp-established --file-locks`, log)
    return ""
}

async function stopContainer(name: string, log: FastifyBaseLogger) {
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

async function removeContainer(name: string, log: FastifyBaseLogger) {
    await requestDocker({
        method: 'delete',
        url: `/containers/${name}`,
        params: {v: true}
    }, log)
}

type ContainerInfo = {
    Id: string
}

export {
    requestDocker,
    pullImage,
    listContainer,
    inspectContainer,
    createContainer,
    startContainer,
    checkpointContainerDind,
    checkpointContainerPind,
    restoreContainer,
    stopContainer,
    removeContainer,
    ContainerInfo
}
