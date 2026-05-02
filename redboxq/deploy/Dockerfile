# Multi-stage build for redboxq.

FROM golang:1.23-alpine AS build
WORKDIR /src

# Pin deps in their own layer so iteration on source doesn't re-download.
COPY go.mod go.sum ./
RUN go mod download

COPY cmd ./cmd
COPY internal ./internal
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/redboxq ./cmd/redboxq

FROM alpine:3.20
RUN apk add --no-cache ca-certificates curl
WORKDIR /app
COPY --from=build /out/redboxq /usr/local/bin/redboxq
COPY web ./web
EXPOSE 7000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://localhost:7000/health || exit 1
CMD ["redboxq"]
