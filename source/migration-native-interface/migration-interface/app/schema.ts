import {Static, Type} from '@sinclair/typebox'

const BaseRequestProperties = {
    checkpointId: Type.String(),
    template: Type.Any()
    // volumes: Type.Array(Type.Any())
}

const MigrateRequestProperties = {
    ...BaseRequestProperties,
    interfaceHost: Type.String(),
    interfacePort: Type.String()
}

const BaseRequest = Type.Object(BaseRequestProperties)
const MigrateRequest = Type.Object(MigrateRequestProperties)

export type BaseRequestType = Static<typeof BaseRequest>
export type MigrateRequestType = Static<typeof MigrateRequest>

export const MigrateRequestSchema = {
    schema: {
        body: MigrateRequest
    }
}

export const BaseRequestSchema = {
    schema: {
        body: BaseRequest
    }
}
