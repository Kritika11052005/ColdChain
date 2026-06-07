.PHONY: install dev dev-backend dev-frontend cli

install:
	cd backend && python -m pip install -r requirements.txt
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting both backend and frontend servers..."
	@echo "Please run 'make dev-backend' and 'make dev-frontend' in separate terminals if parallel execution is not supported by your shell."
	# In bash/zsh/PowerShell with appropriate tools:
	# (cd backend && uvicorn main:app --port 8000) & (cd frontend && npm run dev)

cli:
	@if [ -z "$(DOMAIN)" ]; then \
		echo "Usage: make cli DOMAIN=razorpay.com"; \
	else \
		python backend/cli/main.py $(DOMAIN); \
	fi
