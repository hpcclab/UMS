FROM node:alpine

HEALTHCHECK CMD wget -q localhost:8888 || exit 1

WORKDIR /app

RUN apk add rsync openssh bash

COPY package.json .

RUN npm install --production

COPY . .

RUN npm run build

CMD ["npm", "run", "start"]

RUN chmod 400 /app/id_rsa
