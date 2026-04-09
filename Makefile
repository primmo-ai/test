.PHONY: run stop clean

run:
	docker compose up --build

stop:
	docker compose down

clean:
	docker compose down -v
