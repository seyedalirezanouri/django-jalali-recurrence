coverage:
	pytest

test:
	pytest

testall:
	tox

build: clean
	python -m build

clean:
	rm -rf dist/*
	rm -rf build/*

push: build
	git push

release: push
	twine check dist/*
	twine upload dist/*

.PHONY: coverage test testall build clean push
