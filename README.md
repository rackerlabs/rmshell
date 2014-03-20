rore
=======

A command line tool for working with Redmine

Requires a config file like:
```
[default]
url=https://redmine.yourorg.tld
key=7c6cnotarealkey2b198c24449cca20b61c95854
```

Uses [python-redmine](https://github.com/maxtepkeev/python-redmine)

INSTALLATION
============

```
$ pip install rore
```
Or to install directly from checkout:
```
$ python setup.py build
$ python setup.py install
```

USAGE
=====

```
$ rore isues --query
```
```
$ rore issues --create --project deploy --subject 'Deploy broken!'
```
```
$ rore projects --list
```

DOCUMENTATION
=============


Nothing exists right now except for the help output.
```
$ rore --help
```
```
$ rore issues --help
```

CONTRIBUTING
============

License is Apache 2.0.

Pull requests welcome.

Find me in #rackspace-dev on Freenode as jlk
