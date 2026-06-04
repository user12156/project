FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY frontend/ ./

# 배포에서는 nginx가 /api 요청을 백엔드 컨테이너로 프록시합니다.
# 그래서 프론트 빌드 안에는 별도 API 주소를 박지 않는 것이 기본값입니다.
ARG VITE_API_BASE_URL=
ARG VITE_GOOGLE_CLIENT_ID=
ARG VITE_GOOGLE_ALLOWED_ORIGINS=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}
ENV VITE_GOOGLE_ALLOWED_ORIGINS=${VITE_GOOGLE_ALLOWED_ORIGINS}

RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
