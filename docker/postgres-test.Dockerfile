FROM golang:1.26.10-alpine3.24@sha256:5cb67f19c5e7994dcb80c074f7cfca8aeeada45bbdca035f73df269cefdcce61 AS gosu-builder

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
    grep -F 'go1.26.10' /out/gosu-build-info.txt; \
    /out/gosu --version; \
    /out/gosu nobody true

FROM postgres:16.15-alpine@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685

COPY --from=gosu-builder /out/gosu /usr/local/bin/gosu

# The base-image APK index may lag Alpine's signed package repository.
# Verify the exact patched upstream APK before installing it, fail closed.
RUN set -eux; \
    zlib_apk='/tmp/zlib-1.3.2-r1.apk'; \
    wget -q -O "$zlib_apk" "https://dl-cdn.alpinelinux.org/alpine/v3.24/main/$(apk --print-arch)/zlib-1.3.2-r1.apk"; \
    apk verify "$zlib_apk"; \
    apk add --no-cache \
        "$zlib_apk" \
        'musl=1.2.6-r3' \
        'musl-utils=1.2.6-r3' \
        'libcrypto3=3.5.9-r0' \
        'libssl3=3.5.9-r0' \
        'libuuid=2.42.3-r1' \
        'krb5-libs=1.22.3-r0' \
        'libxslt=1.1.43-r4'; \
    rm -f "$zlib_apk"; \
    apk list --installed musl 2>/dev/null | grep -q '^musl-1\.2\.6-r3 '; \
    apk list --installed musl-utils 2>/dev/null | grep -q '^musl-utils-1\.2\.6-r3 '; \
    apk list --installed zlib 2>/dev/null | grep -q '^zlib-1\.3\.2-r1 '; \
    apk list --installed libcrypto3 2>/dev/null | grep -q '^libcrypto3-3\.5\.9-r0 '; \
    apk list --installed libssl3 2>/dev/null | grep -q '^libssl3-3\.5\.9-r0 '; \
    apk list --installed libuuid 2>/dev/null | grep -q '^libuuid-2\.42\.3-r1 '; \
    apk list --installed krb5-libs 2>/dev/null | grep -q '^krb5-libs-1\.22\.3-r0 '; \
    apk list --installed libxslt 2>/dev/null | grep -q '^libxslt-1\.1\.43-r4 '; \
    gosu --version; \
    gosu nobody true

USER postgres
