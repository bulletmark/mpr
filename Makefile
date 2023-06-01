NAME = $(shell basename $(CURDIR))
PYNAME = $(subst -,_,$(NAME))

all:
	@echo "Type make install|uninstall"
	@echo "or make sdist|upload|check|clean"

install:
	pip install -U .
	make clean

uninstall:
	pip uninstall $(NAME)

sdist:
	rm -rf dist
	python3 setup.py sdist bdist_wheel

upload: sdist
	twine3 upload --skip-existing dist/*

doc:
	update-readme-usage

check:
	ruff .
	vermin --no-tips -i $(PYNAME).py setup.py
	python3 setup.py check

clean:
	@rm -vrf *.egg-info build/ dist/ __pycache__/
