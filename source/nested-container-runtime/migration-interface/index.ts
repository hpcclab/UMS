loadDefaultConfig()
require('dotenv').config()
import fastify from 'fastify'
import {registerPath} from './app'


const server = fastify({
    logger: {
        level: process.env.LOG_LEVEL
    }
})

registerPath(server)

server.setErrorHandler(function (error, request, reply) {
    this.log.error(error)
    reply.status(error.statusCode || 500).send(error)
})

server.listen(8888, '0.0.0.0', (err, address) => {
    if (err) {
        console.error(err)
        process.exit(1)
    }
    console.log(`Server listening at ${address}`)
})

function loadDefaultConfig() {
    process.env.LOG_LEVEL = 'info'
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
}
