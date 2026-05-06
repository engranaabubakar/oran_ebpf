SHELL := /bin/bash

BPF_CLANG ?= $(shell command -v clang || command -v clang-18 || command -v clang-17 || command -v clang-16 || echo clang)
BPF_CFLAGS ?= -O2 -g -Wall -Werror -target bpf -D__TARGET_ARCH_x86
SRC := src/tc_gtpu_telemetry.c
OUT := build/tc_gtpu_telemetry.o

.PHONY: all clean

all: $(OUT)

$(OUT): $(SRC) include/gtpu.h
	mkdir -p build
	$(BPF_CLANG) $(BPF_CFLAGS) -Iinclude -c $(SRC) -o $(OUT)

clean:
	rm -rf build
