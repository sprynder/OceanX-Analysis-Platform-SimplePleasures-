FROM golang:1.24-alpine 

WORKDIR /app

RUN apk add --no-cache git

COPY . .

RUN go mod tidy

EXPOSE 8080

CMD ["go", "run", "./cmd/api"]