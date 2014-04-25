all: test

test:
	django-admin.py test --pythonpath=./ --settings=tests.settings
	flake8 multiform tests
