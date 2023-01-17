import {AxiosInstance, AxiosRequestConfig} from "axios"
import {FastifyBaseLogger} from "fastify/types/logger"
import {exec as childExec} from 'child_process'
import util from "util"
import Rsync from "rsync"

const exec = util.promisify(childExec)

class HttpError extends Error {
    public statusCode: number

    constructor(message: string, statusCode: number) {
        super(message)
        this.statusCode = statusCode
        Object.setPrototypeOf(this, new.target.prototype)
    }
}


const axios: AxiosInstance = require("axios").default.create({
    baseURL: `http://${process.env.HOST}:5000`
})


async function requestAxios(config: AxiosRequestConfig, log: FastifyBaseLogger) {
    try {
        await waitForIt(`${process.env.HOST}`, '5000', log)
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

async function waitForIt(interfaceHost: string, interfacePort: string, log: FastifyBaseLogger) {
    await execBash(`/app/wait-for-it.sh ${interfaceHost}:${interfacePort} -t 0`, log)
}

async function execBash(command: string, log: FastifyBaseLogger) {
    try {
        const {
            stdout,
            stderr
        } = await exec(command)
        log.error(stdout)
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
    requestAxios,
    waitForIt,
    execBash,
    execRsync,
    HttpError
}
