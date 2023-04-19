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
