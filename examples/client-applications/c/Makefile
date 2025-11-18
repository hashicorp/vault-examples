CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2 -I. -I/opt/homebrew/Cellar/json-c/0.18/include/json-c
LDFLAGS = -lcurl -ljson-c -lpthread -L/opt/homebrew/lib

TARGET = vault-app
SOURCES = src/main.c src/vault_client.c src/config.c
HEADERS = src/vault_client.h config.h

$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES) $(LDFLAGS)

clean:
	rm -f $(TARGET)

install-deps-ubuntu:
	sudo apt-get install libcurl4-openssl-dev libjson-c-dev

install-deps-macos:
	brew install curl json-c

.PHONY: clean install-deps-ubuntu install-deps-macos