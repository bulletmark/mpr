NAME = $(shell basename $(CURDIR))
PYNAME = $(subst -,_,$(NAME))

check:
	ruff check .
	mypy .
	vermin -vv --exclude importlib.metadata --no-tips -i */*.py

build:
	rm -rf dist
	python3 -m build

upload: build
	twine3 upload dist/*

doc:
	update-readme-usage -a

format:
	ruff format */*.py

clean:
	@rm -vrf *.egg-info .venv/ build/ dist/ __pycache__ */__pycache__
