loadDefaultConfig()
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

server.listen({ port: 8888, host: '0.0.0.0' }, (err, address) => {
    if (err) {
        console.error(err)
        process.exit(1)
    }
})

function loadDefaultConfig() {
    process.env.LOG_LEVEL = process.env.LOG_LEVEL || 'info'
    process.env.HOST = process.env.HOST || '127.0.0.1'
}
