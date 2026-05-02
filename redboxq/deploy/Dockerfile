# Multi-stage build for redboxq.
#
# Builds against the vendored dependencies — the docker build never
# reaches out to proxy.golang.org so corporate proxies / flaky networks
# don't break it. Run `go mod vendor` after every dep change.

FROM golang:1.23-alpine AS build
WORKDIR /src

# Belt-and-suspenders: if vendor/ is somehow missing, allow direct
# fallback when the public proxy is unreachable.
ENV GOPROXY=https://proxy.golang.org,direct
ENV GOSUMDB=sum.golang.org
ENV GOFLAGS=-mod=vendor

COPY go.mod go.sum ./
COPY vendor ./vendor
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
