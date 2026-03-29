FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
COPY scripts ./scripts
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
