import {FastifyBaseLogger} from "fastify/types/logger"
import {exec as childExec} from 'child_process'
import util from "util"
import Rsync from "rsync"
import fastify from "fastify";
import axios, {AxiosRequestConfig} from "axios";
import {HOST, LOG_LEVEL} from "./const";

const server = fastify({
    logger: {
        level: LOG_LEVEL
    }
})

const exec = util.promisify(childExec)

class HttpError extends Error {
    public statusCode: number

    constructor(message: string, statusCode: number) {
        super(message)
        this.statusCode = statusCode
        Object.setPrototypeOf(this, new.target.prototype)
    }
}

type ContainerInfo = {
    Id: string
}


const axiosInstance = axios.create({
    baseURL: `http://${HOST}`
})


async function requestAxios(config: AxiosRequestConfig, log: FastifyBaseLogger, timeout: number = 0) {
    try {
        const host = `${HOST}`.split(':')
        await waitForIt(host[0], host[1], log, timeout)
        const response = await axiosInstance(config)
        log.debug(JSON.stringify(response.data))
        return {statusCode: response.status, message: response.data, headers: response.headers}
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

function findDestinationFileSystemId(containers: any, containerInfo: any) {
    let destinationId, destinationFs
    for (const container of containers) {
        if (containerInfo.Names.includes(container.name)) {
            destinationId = container.id
            destinationFs = container.fs
            break
        }
    }
    if (destinationId === undefined) {
        throw new HttpError(`Cannot find Id of the destination container (${containers.toString()}): ${containerInfo.Names[0]}`, 500)
    }
    return {destinationId, destinationFs}
}

async function waitForIt(interfaceHost: string, interfacePort: string, log: FastifyBaseLogger, timeout: number = 0) {
    await execBash(`/app/wait-for-it.sh ${interfaceHost}:${interfacePort} -t ${timeout}`, log)
}

async function execBash(command: string, log: FastifyBaseLogger) {
    try {
        const {
            stdout,
            stderr
        } = await exec(command)
        log.debug(stdout)
        log.error(stderr)
        return stdout
    } catch (error: any) {
        throw new HttpError(error.message, 500)
    }
}

function execRsync(port: string, source: string, destination: string, log: FastifyBaseLogger) {
    const rsync = new Rsync()
        .shell(`ssh -i /app/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p ${port}`)
        .flags('avz')
        .set('inplace')
        .set('append')
        .source(source)
        .destination(destination)

    return new Promise((resolve, reject) => {
        // signal handler function
        const quitting = function () {
            if (rsyncPid) {
                rsyncPid.kill()
            }
            process.exit()
        }
        process.on("SIGINT", quitting) // run signal handler on CTRL-C
        process.on("SIGTERM", quitting) // run signal handler on SIGTERM
        process.on("exit", quitting) // run signal handler when main process exits

        const rsyncPid = rsync.execute(function (error, code, cmd) {
            if (error) {
                reject(error)
            }
            log.debug(`execute ${cmd}. return ${code}`)
            resolve(code)
        }, function (data) {
            log.debug(data.toString())
        }, function (data) {
            log.debug(data.toString())
        })
    })
}

export {
    server,
    HttpError,
    ContainerInfo,
    requestAxios,
    findDestinationFileSystemId,
    waitForIt,
    execBash,
    execRsync
}
