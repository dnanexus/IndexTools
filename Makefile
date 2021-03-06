repo = dnanexus/IndexTools
package = indextools
version = 0.1.3
tests = tests
pytestopts = -s -vv --show-capture=all

all: clean install test

build_cgranges:
	cd cgranges \
	&& python setup.py build_ext -i \
	&& python setup.py bdist_wheel

install_cgranges: build_cgranges
	pip install --upgrade cgranges/dist/cgranges*.whl

build: clean
	poetry build

lock:
	poetry lock

install: build
	pip install --upgrade dist/$(package)-$(version)-*.whl $(installargs)

install_test_deps:
	pip install -r requirements-test.txt

test: install_test_deps
	coverage run -m pytest $(pytestopts) $(tests)
	coverage report -m
	coverage xml

lint:
	flake8 $(package)

reformat:
	black $(package)
	black $(tests)

clean:
	rm -Rf __pycache__
	rm -Rf **/__pycache__/*
	rm -Rf **/*.so
	rm -Rf **/*.pyc
	rm -Rf dist
	rm -Rf build
	rm -Rf $(package).egg-info
	rm -Rf cgranges/build
	rm -Rf cgranges/dist
	rm -Rf cgranges/*.egg-info

docker:
	# update lockfile
	poetry lock
	# build
	docker build -f Dockerfile -t $(repo):$(version) .
	# add alternate tags
	docker tag $(repo):$(version) $(repo):latest
	# push to Docker Hub
	# requires user to be logged in to account with
	# permissions to push to $(repo)
	docker push $(repo)

tag:
	git tag $(version)

push_tag:
	git push origin --tags

del_tag:
	git tag -d $(version)

set_version:
	poetry version $(dunamai from git --no-metadata --style semver)

pypi_release:
	poetry publish

release: clean tag
	${MAKE} install test pypi_release push_tag || (${MAKE} del_tag set_version && exit 1)

	# create release in GitHub
	curl -v -i -X POST \
		-H "Content-Type:application/json" \
		-H "Authorization: token $(token)" \
		https://api.github.com/repos/$(repo)/releases \
		-d '{"tag_name":"$(version)","target_commitish": "master","name": "$(version)","body": "$(desc)","draft": false,"prerelease": false}'
