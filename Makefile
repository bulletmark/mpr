NAME = $(shell basename $(CURDIR))
PYFILES = $(wildcard $(NAME)/*.py)

check:
	ruff check $(PYFILES)
	mypy $(PYFILES)
	vermin -vv --exclude importlib.metadata --no-tips -i $(PYFILES)

build:
	rm -rf dist
	python3 -m build --sdist --wheel

upload: build
	twine3 upload dist/*

doc:
	update-readme-usage -a

format:
	ruff check --select I --fix $(PYFILES) && ruff format $(PYFILES)

clean:
	@rm -vrf *.egg-info .venv/ build/ dist/ __pycache__ */__pycache__
