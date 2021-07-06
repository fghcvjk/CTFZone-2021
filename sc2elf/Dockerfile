FROM ubuntu:20.04

RUN apt update && apt install -y socat \
    curl \
    xz-utils

RUN useradd -u 1001 -m ctf

USER ctf

# install wasmtime
RUN curl https://wasmtime.dev/install.sh -sSf | bash

# copy files
RUN mkdir -p /home/ctf/task
COPY sc2elf.wasm /home/ctf/task/sc2elf.wasm
COPY tmpl /home/ctf/task/tmpl
COPY flag.txt /home/ctf/task/flag.txt

WORKDIR /home/ctf/task

ENTRYPOINT while sleep 1; do socat TCP-LISTEN:31337,fork,reuseaddr,forever EXEC:"/home/ctf/.wasmtime/bin/wasmtime sc2elf.wasm --dir ./"; done
