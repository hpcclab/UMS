import {FastifyBaseLogger} from "fastify/types/logger"
import {exec as childExec} from 'child_process'
import util from "util"
import Rsync from "rsync"
import fastify from "fastify";

const server = fastify({
    logger: {
        level: process.env.LOG_LEVEL
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

async function waitForIt(interfaceHost: string, interfacePort: string, log: FastifyBaseLogger) {
    await execBash(`/app/wait-for-it.sh ${interfaceHost}:${interfacePort} -t 0`, log)
}

async function execBash(command: string, log: FastifyBaseLogger) {
    try {
        const {
            stdout,
            stderr
        } = await exec(command)
        log.debug(stdout)
        log.error(stderr)
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
    findDestinationFileSystemId,
    waitForIt,
    execBash,
    execRsync,
    HttpError
}
