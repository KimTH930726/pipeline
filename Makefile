.PHONY: backend frontend dev install

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	$(MAKE) backend & $(MAKE) frontend & wait

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
