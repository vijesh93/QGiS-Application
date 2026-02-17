# Load environment variables
include .env
export

.PHONY: dev build stop clean shell

# Start development environment with hot-reload
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Build for production
build:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Stop all containers
stop:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Clean volumes (CAUTION: deletes your database data)
clean:
	docker-compose down -v

# Open a terminal inside the database (useful for SQL)
db-shell:
	docker-compose exec db psql -U ${DB_USER} -d geoportal