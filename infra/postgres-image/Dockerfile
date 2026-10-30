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

FROM postgres:17.11-alpine3.24@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b
COPY --from=gosu-build --chmod=0755 /out/gosu /usr/local/bin/gosu
COPY --from=gosu-build /src/gosu/LICENSE /usr/share/licenses/gosu/LICENSE
RUN gosu --version && gosu postgres sh -c 'test "$(id -u)" = 70 && test "$(id -g)" = 70'
