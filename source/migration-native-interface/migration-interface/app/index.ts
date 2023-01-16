import {FastifyInstance} from "fastify"
import {migrate} from "./api/migrate"
import {restore} from "./api/restore"
import {
    BaseRequestSchema,
    BaseRequestType,
    MigrateRequestSchema,
    MigrateRequestType
} from "./schema"

function registerPath(server: FastifyInstance) {
    server.get('/', { logLevel: "error" }, (request, reply) => {
        reply.code(200).send('welcome')
    })
    server.post<{ Body: MigrateRequestType }>('/migrate', MigrateRequestSchema, migrate)
    server.post<{ Body: BaseRequestType }>('/restore', BaseRequestSchema, restore)
}

export {registerPath}
