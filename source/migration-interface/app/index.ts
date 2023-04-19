import {FastifyInstance} from "fastify"
import {create} from "./api/create"
import {probe} from "./api/probe"
import {probeAll} from "./api/probeAll"
import {list} from "./api/list"
import {migrate} from "./api/migrate"
import {restore} from "./api/restore"
import {save} from "./api/save";
import {load} from "./api/load";
import {stop} from "./api/stop"
import {
    CreateRequestSchema,
    CreateRequestType,
    MigrateRequestSchema,
    MigrateRequestType,
    RestoreRequestSchema,
    RestoreRequestType,
} from "./schema"

function registerPath(server: FastifyInstance) {
    server.get('/',{ logLevel: "error" },  (request, reply) => {
        reply.code(200).send('welcome')
    })
    server.get<{ Params: CreateRequestType }>('/create/:containerName', CreateRequestSchema, create)
    server.get('/list', list)
    server.get('/probeAll', probeAll)
    server.get<{ Params: CreateRequestType }>('/probe/:containerName', CreateRequestSchema, probe)
    server.post<{ Body: MigrateRequestType }>('/migrate', MigrateRequestSchema, migrate)
    server.post<{ Body: RestoreRequestType }>('/restore', RestoreRequestSchema, restore)
    server.post<{ Body: MigrateRequestType }>('/save', MigrateRequestSchema, save)
    server.post<{ Body: RestoreRequestType }>('/load', RestoreRequestSchema, load)
    server.post('/stop', stop)
}

export {registerPath}
