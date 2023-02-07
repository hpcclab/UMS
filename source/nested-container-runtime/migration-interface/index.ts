loadDefaultConfig()
import {registerPath} from './app'
import {server} from "./app/lib";

registerPath(server)

server.setErrorHandler(function (error, request, reply) {
    this.log.error(error)
    reply.status(error.statusCode || 500).send(error)
})

server.listen({ port: 8888, host: '0.0.0.0' }, (err, address) => {
    if (err) {
        console.error(err)
        process.exit(1)
    }
})

function loadDefaultConfig() {
    process.env.DOCKER_HOST = process.env.DOCKER_HOST || '127.0.0.1:2375'
    process.env.SCRATCH_IMAGE = process.env.SCRATCH_IMAGE || 'nims/scratch'
    process.env.LOG_LEVEL = process.env.LOG_LEVEL || 'info'
    process.env.DOMAIN = 'migration'
    process.env.SPEC_CONTAINER_ANNOTATION = `${process.env.DOMAIN}-containers`
    process.env.START_MODE_ANNOTATION = `${process.env.DOMAIN}-start-mode`
    process.env.START_MODE_ACTIVE = 'active'
    process.env.START_MODE_PASSIVE = 'passive'
    process.env.START_MODE_NULL = 'null'
    process.env.START_MODE_FAIL = 'fail'
    process.env.INTERFACE_ANNOTATION = 'migration-interface'
    process.env.INTERFACE_DIND = 'dind'
    process.env.INTERFACE_PIND = 'pind'
    process.env.INTERFACE_FF = 'ff'
    process.env.INTERFACE_SSU = 'ssu'
}
