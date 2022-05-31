import { Static, Type } from '@sinclair/typebox'

const BaseRequestProperties = {
    checkpointId: Type.String()
}

const CreateRequestProperties = {
    containerName: Type.String()
}

const CheckpointProperties = {
    ...BaseRequestProperties,
    volumes: Type.Array(Type.Any())
}

const MigrateRequestProperties = {
    ...CheckpointProperties,
    interfaceHost: Type.String(),
    interfacePort: Type.String(),
    containers: Type.Array(Type.Any())
}

const BaseRequest = Type.Object(BaseRequestProperties);
const CreateRequest = Type.Object(CreateRequestProperties);
const CheckpointRequest = Type.Object(CheckpointProperties);
const MigrateRequest = Type.Object(MigrateRequestProperties);

export type BaseRequestType = Static<typeof BaseRequest>;
export type CreateRequestType = Static<typeof CreateRequest>;
export type CheckpointRequestType = Static<typeof CheckpointRequest>;
export type MigrateRequestType = Static<typeof MigrateRequest>;

export const CreateRequestSchema = {
    schema: {
        params: CreateRequest
    }
}

export const CheckpointRequestSchema = {
    schema: {
        body: CheckpointRequest
    }
}

export const MigrateRequestSchema = {
    schema: {
        body: MigrateRequest
    }
}

export const BaseRequestSchema ={
    schema: {
        body: BaseRequest
    }
}
