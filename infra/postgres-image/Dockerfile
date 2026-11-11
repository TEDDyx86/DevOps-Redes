# Preserve the official database/entrypoint; refresh only its privilege-drop helper.
FROM golang:1.27.3-alpine3.24@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb AS gosu-build

ENV CGO_ENABLED=0 GOTOOLCHAIN=local
WORKDIR /src/gosu
ADD --checksum=sha256:cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164 \
    https://codeload.github.com/tianon/gosu/tar.gz/refs/tags/1.19 /tmp/gosu.tar.gz
RUN tar -xzf /tmp/gosu.tar.gz --strip-components=1 -C /src/gosu \
    && go mod download \
    && go mod verify \
    && go build -mod=readonly -trimpath -buildvcs=false -ldflags='-w' -o /out/gosu . \
    && go version -m /out/gosu \
    && /out/gosu --version \
    && /out/gosu nobody true

FROM postgres:17.11-alpine3.24@sha256:e5d2edd28b1f8d40a0a6c0c9cdc545b19b56a0d5d88f94bc11a97d970d4700d0
COPY --from=gosu-build --chmod=0755 /out/gosu /usr/local/bin/gosu
COPY --from=gosu-build /src/gosu/LICENSE /usr/share/licenses/gosu/LICENSE
# Pin published security fixes; the upstream base rebuild still ships vulnerable versions.
RUN apk add --no-cache zlib=1.4-r0 krb5-libs=1.22.3-r0 libxslt=1.1.43-r4
RUN gosu --version && gosu postgres sh -c 'test "$(id -u)" = 70 && test "$(id -g)" = 70'
