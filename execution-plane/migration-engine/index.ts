loadDefaultConfig()
require('dotenv').config()
import fastify from 'fastify'
import {registerPath} from './app'


const server = fastify({
    logger: true
})

server.register(require('fastify-multipart'))

registerPath(server)

server.listen(8888, '0.0.0.0', (err, address) => {
    if (err) {
        console.error(err)
        process.exit(1)
    }
    console.log(`Server listening at ${address}`)
})

function loadDefaultConfig() {
    process.env.DOMAIN = 'migration'
    process.env.SPEC_CONTAINER_ANNOTATION = `${process.env.DOMAIN}-containers`
    process.env.START_MODE_ANNOTATION = `${process.env.DOMAIN}-start-mode`
    process.env.START_MODE_ACTIVE = 'active'
    process.env.START_MODE_PASSIVE = 'passive'
    process.env.START_MODE_NULL = 'null'
}
