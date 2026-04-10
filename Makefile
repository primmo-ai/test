.PHONY: run run-ollama stop clean

run:
	docker compose up --build

run-ollama:
	docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build

stop:
	docker compose down

clean:
	docker compose down -v
