.PHONY: initialize-development

# Initialize the project development environment.
initialize-development:
	@poetry install --sync
	@pre-commit install

.PHONY: test
test:
	@coverage run --source=grpc_prometheus_metrics -m pytest
	@coverage report -m

# Run pre-commit for all
pre-commit:
	@pre-commit run --all-files

run-test:
	@python -m unittest discover

# Fix the import path. Use pipe for sed to avoid the difference between Mac and GNU sed
compile-protos:
	@python -m grpc_tools.protoc \
	  --python_out=tests/integration//hello_world \
	  -I tests/integration/protos \
	  tests/integration/protos/*.proto
	@python -m grpc_tools.protoc \
      --plugin=protoc-gen-grpc=/usr/bin/grpc_python_plugin \
      --python_out=tests/integration//hello_world  \
      --grpc_python_out=tests/integration//hello_world  \
      -I tests/integration/protos \
      tests/integration/protos/*.proto

run-test-server:
	python -m tests.integration.hello_world.hello_world_server

run-test-client:
	python -m tests.integration.hello_world.hello_world_client

publish:
	# Markdown checker
	# pip install cmarkgfm
	rm -rf *.egg-info build dist
	python setup.py sdist bdist_wheel
	twine check dist/*
	twine upload dist/*
