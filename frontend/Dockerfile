FROM node:20-alpine

WORKDIR /app

RUN npm install -g expo-cli @expo/cli

COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 8081

ENV CI=1
ENV EXPO_NO_DOTENV=1

CMD ["npx", "expo", "start", "--web", "--non-interactive", "--port", "8081"]
