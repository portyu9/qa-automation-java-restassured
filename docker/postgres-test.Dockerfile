FROM golang:1.26.6-alpine3.24@sha256:3889b425f035be855a72fb4755265311293b6d414521f0a519d819df32222d83 AS gosu-builder

ARG GOSU_COMMIT=6456aaa0f3c854d199d0f037f068eb97515b7513
ARG GOSU_TAG=1.19

RUN set -eux; \
    apk add --no-cache git; \
    git init /src; \
    git -C /src fetch --depth 1 https://github.com/tianon/gosu.git "refs/tags/${GOSU_TAG}"; \
    git -C /src checkout --detach FETCH_HEAD; \
    test "$(git -C /src rev-parse HEAD)" = "$GOSU_COMMIT"

WORKDIR /src
ENV CGO_ENABLED=0
RUN set -eux; \
    go mod download; \
    go build -trimpath -ldflags='-d -w' -buildvcs=true -o /out/gosu github.com/tianon/gosu; \
    go version -m /out/gosu | tee /out/gosu-build-info.txt; \
    grep -F 'go1.26.6' /out/gosu-build-info.txt; \
    /out/gosu --version; \
    /out/gosu nobody true

FROM postgres:16.15-alpine@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685

USER root
COPY --from=gosu-builder /out/gosu /usr/local/bin/gosu

RUN set -eux; \
    apk add --no-cache \
        'libcrypto3=3.5.8-r0' \
        'libssl3=3.5.8-r0'; \
    test "$(apk info -v libcrypto3)" = 'libcrypto3-3.5.8-r0'; \
    test "$(apk info -v libssl3)" = 'libssl3-3.5.8-r0'; \
    gosu --version; \
    gosu nobody true
