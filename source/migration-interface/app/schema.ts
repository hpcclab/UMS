import {Static, Type} from '@sinclair/typebox'


const CreateRequestProperties = {
    containerName: Type.String()
}

const MigrateRequestProperties = {
    checkpointId: Type.String(),
    interfaceHost: Type.String(),
    interfacePort: Type.String(),
    containers: Type.Array(Type.Any()),
    volumes: Type.Array(Type.Any()),
    template: Type.Any()
}

const RestoreRequestProperties = {
    checkpointId: Type.String(),
    template: Type.Any()
    // volumes: Type.Array(Type.Any())
}

const CreateRequest = Type.Object(CreateRequestProperties)
const MigrateRequest = Type.Object(MigrateRequestProperties)
const RestoreRequest = Type.Object(RestoreRequestProperties)

export type CreateRequestType = Static<typeof CreateRequest>
export type MigrateRequestType = Static<typeof MigrateRequest>
export type RestoreRequestType = Static<typeof RestoreRequest>

export const CreateRequestSchema = {
    schema: {
        params: CreateRequest
    }
}
export const MigrateRequestSchema = {
    schema: {
        body: MigrateRequest
    }
}

export const RestoreRequestSchema = {
    schema: {
        body: RestoreRequest
    }
}
