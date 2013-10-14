clamp
=====

Implements clamp in Python. Pre-alpha version - API subject to change.

You need to install. Soon this will be on PyPI, before then, in the checkout directory:

````bash
$ jython27 setup.py install
````

Example project using this package:
https://github.com/jimbaker/clamped

(NOTE: example project needs to be updated!!!!)

The clamp project supports setuptools integration:

To create a jar in site-packages/jars and register this new jar in site-packages/jar.pth:

````bash
$ jython27 setup.py build_jar
````

To create a single jar version of the current Jython installation (such as a virtualenv). This setup.py custom command will use the project name as the base for the jar:

````bash
$ jython27 setup.py singlejar
````

To create a single jar version of the current Jython installation, you
can also run this script, which is installed in Jython's bin
directory. By default, the jar is named `jython-single.jar`. Use
`--help` for more info:

````bash
$ bin/singlejar # same, but outputs jython-single.jar, 
````


TODO
====

* Add support for variadic constructors of clamped classes, that is
  something like `new BarClamp(Object...)`

* Provide basic support for annotations

* Extend setup.py support of install so that it can use build_jar; see
  http://www.niteoweb.com/blog/setuptools-run-custom-code-during-install
  for some ideas

* Annotation magic? It would be nice to import annotations into
  Python, use as class decorators and function decorators, and then
  still compile a Java class that works.

* Instance fields support, comparable to `__slots__`, but baked into
  the emitted Java class.

