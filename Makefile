.PHONY: run test build up down demo

run:
	python -m bot.main

test:
	python -m pytest

build:
	docker build -t copytrader:latest .

up:
	docker compose up --build -d

down:
	docker compose down

demo:
	python scripts/demo.py
