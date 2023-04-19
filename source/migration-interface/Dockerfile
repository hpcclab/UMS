FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build


FROM scratch

WORKDIR /app
COPY --from=build /app/dist .
COPY Dockerfile.tar.gz id_rsa package*.json wait-for-it.sh ./
