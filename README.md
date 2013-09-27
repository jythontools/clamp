clamp
=====

Implements clamp in Python. Pre-alpha version - API subject to change.

Example project using this package:
https://github.com/jimbaker/clamped


TODO
====

* Support singlejar custom command

* Add support for variadic constructors of clamped classes, that is
  something like `new BarClamp(Object...)`

* Provide basic support for annotations

* Extend setup.py support of install so that it can use buildjar; see
  http://www.niteoweb.com/blog/setuptools-run-custom-code-during-install
  for some ideas

* Annotation magic? It would be nice to import annotations into
  Python, use as class decorators and function decorators, and then
  still compile a Java class that works.

* Instance fields support, comparable to `__slots__`, but baked into
  the emitted Java class.

