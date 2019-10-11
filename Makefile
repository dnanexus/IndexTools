repo = dnanexus/IndexTools
package = indextools
tests = tests
# Use this option to show full stack trace for errors
#pytestopts = --full-trace
#pytestopts = -ra --tb=short
#pytestopts = -vv --show-capture=all

BUILD = poetry build && pip install --upgrade dist/$(package)-$(version)-py3-none-any.whl $(installargs)
TEST = env PYTHONPATH="." coverage run -m pytest $(pytestops) $(tests) ; coverage report -m

all:
	$(BUILD)
	$(TEST)

install:
	$(BUILD)

test:
	$(TEST)

lint:
	flake8 $(package)

reformat:
	black $(package)
	black $(tests)

clean:
	rm -Rf __pycache__
	rm -Rf **/__pycache__/*
	rm -Rf **/*.c
	rm -Rf **/*.so
	rm -Rf **/*.pyc
	rm -Rf dist
	rm -Rf build
	rm -Rf $(package).egg-info

docker:
	# build
	docker build -f Dockerfile -t $(repo):$(version) .
	# add alternate tags
	docker tag $(repo):$(version) $(repo):latest
	# push to Docker Hub
	docker login -u jdidion && \
	docker push $(repo)

release:
	$(clean)
	# build
	$(BUILD)
	$(TEST)
	# bump version
	poetry version $(dunamai from git --no-metadata --style semver)
	# publish
	poetry publish
	# push new tag after successful build
	git push origin --tags
	# create release in GitHub
	curl -v -i -X POST \
		-H "Content-Type:application/json" \
		-H "Authorization: token $(token)" \
		https://api.github.com/repos/$(repo)/releases \
		-d '{"tag_name":"$(version)","target_commitish": "master","name": "$(version)","body": "$(desc)","draft": false,"prerelease": false}'
