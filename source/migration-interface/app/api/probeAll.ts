import {FastifyReply, FastifyRequest} from "fastify"
import {CreateRequestType} from "../schema"
import dotenv from "dotenv";
import {readFileSync} from "fs";
import {migrationInterface} from "../interface";
import {SPEC_CONTAINER_ANNOTATION} from "../const";

async function probeAll(request: FastifyRequest<{ Params: CreateRequestType }>, reply: FastifyReply) {
    const config = dotenv.parse(readFileSync('/etc/podinfo/annotations', 'utf8'))
    const containerInfos: any[] = await migrationInterface.listContainer(config[SPEC_CONTAINER_ANNOTATION], {all: true})

    const states = await Promise.all(containerInfos.map(containerInfo => migrationInterface.inspectContainer(containerInfo.Id)))

    let created = false
    let running = false

    for (const state of states) {
        const {State} = state
        const {Status, ExitCode} = State
        if (Status === "exited" || Status === "dead") {
            reply.code(503)
            return ExitCode || 1
        } else if (Status === "created") {
            created = true
        } else {
            running = true
        }
    }

    if (created && running) {
        reply.code(201)
        return ""
    } else if (created) {
        reply.code(204)
        return
    } else {
        return ""
    }
}

export {probeAll}
