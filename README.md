rmshell
=======

A command line tool for working with Redmine

Requires a config file like:
```
[default]
url=https://redmine.yourorg.tld
key=7c6cnotarealkey2b198c24449cca20b61c95854
```

Uses [pyredmine](https://github.com/ianepperson/pyredminews)

INSTALLATION
============

```
$ python setup.py build
$ python setup.py install
```

USAGE
=====

```
$ rmshell isues --query
```
```
$ rmshell issues --create --project deploy --subject 'Deploy broken!'
```

DOCUMENTATION
=============


Nothing exists right now except for the help output.
```
$ rmshell --help
```
```
$ rmshell issues --help
```

CONTRIBUTING
============

License is Apache 2.0.

Pull requests welcome.

Find me in #rackspace-dev on Freenode as jlk
