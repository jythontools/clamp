Clamp background
================

Clamp is part of the jythontools project
(https://github.com/jythontools). Although Jython has already very
integration with Java, Clamp improves this support by enabling precise
generation of the Java bytecode used to wrap Python classes. In a
nutshell, this means such clamped classes can be used as modern Java
classes.

Clamp integrates with setuptools. Clamped packages are installed into
site-packages. Clamp can also take an entire Jython installation,
including site-packages, and wrap it into a **single jar**.

Clamp thereby provides the following benefits:

* JVM frameworks can readily work with clamped code, oblivious of its
  source

* Especially those frameworks that need single jar support

* Developers can stay as much in Python as possible. Note that Clamp
  currently can only clamp Python classes that inherit from a Java
  base class and/or extend Java interfaces.

* We are working on a SQLAlchemy-like DSL that is declarative, using
  metaclasses and other metaprogramming techniques.


Clamp example: Clamped
======================

Please see the "Clamped" project on how to use this package. This
project provides crucial documentation on how to use Clamp by going
through an example in the README: https://github.com/jimbaker/clamped

The [Clamped README][clamped] also details some aspects of the
bytecode generation and how it enables direct Java usage.

Lastly, there is a preliminary [talk][] on Clamp available
([source][talk source]). Note that this talk goes more into the
implementation of Clamp, including how we use metaprogramming.


Important caveats
=================

Clamp is currently in a pre-alpha version, with its API subject to
change. In particular, the argument structure for the setuptools clamp
keyword recently changed, as of the 0.4 release. Clamp also recently
went through a major refactoring to transform it from a useful spike
to a production-ready package.

You need to install Clamp from this github repo. You will also want to
use the [jython-ssl branch][] for Jython 2.7, until the necessary SSL work
lands in Jython trunk. Again, see the [Clamped project][clamped]
for details on how to work with this branch.

From the checkout directory:

````bash
$ jython27 setup.py install
````

Soon this will be on PyPI, but this awaiting sufficient unit testing
of Clamp.


Integrated with setuptools
--------------------------

The clamp project supports setuptools integration. You simply need to
add one keyword, `clamp`, as well as depend on the Clamp package:

````python
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = "clamped",
    version = "0.1",
    packages = find_packages(),
    install_requires = ["clamp>=0.4"],
    clamp = {
        "modules": ["clamped"]},
)
````

At a minimum, you need to specify the `modules` you wish to clamp.


`clamp` command
---------------

This is a post-install task.

The `clamp` command installs into site-packages any embedded
jars. Modules that are specified and clamps any modules into a
jar. All such jars are registered in jar.pth.

````bash
$ jython27 setup.py clamp
````

FIXME Layout considerations. Subject to change.

FIXME Combining `clamp` with `install`. See http://www.niteoweb.com/blog/setuptools-run-custom-code-during-install
for some ideas.


`build_jar` command
-------------------

Not normally needed.

To create a jar for a clamped module in site-packages/jars and
register this new jar in site-packages/jar.pth:

````bash
$ jython27 setup.py build_jar
````


`singlejar` command
-------------------

To create a single jar version of the current Jython installation
(such as a virtualenv). This setup.py custom command will use the
project name as the base for the jar:

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

* Add support for [variadic constructors](#variadic-constructors) of
  clamped classes. This means that in Java, using code can simply
  perform `new BarClamp(x, y, ...)`; in Python, `BarClamp(x, y, ...)`.

* Provide basic support for annotations.

* [Annotation magic](#supporting-java-annotations). It would be nice to import
  annotations into Python, use as class decorators and function
  decorators, and then still compile a Java class that works.

* Instance fields support, comparable to `__slots__`, but baked into
  the emitted Java class. Such support would directly enable emitted
  clases to be used as POJOs by using Java code. Clamp should use
  `__slots__` if available. However, without further information, this
  would mean emitting fields of type `Object`. So there should be also
  some way of constraining the types of emitted instance fields in
  `ClampProxyMaker`. Likely this should be as simple as a new `slots`
  keyword when creating a proxymaker that simply maps fields to Java
  types.

* Map [Python descriptors][] to Java's convention of getters/setters. Note
  that `__delete__` is not a mappable idea!

* Add support for resolving external jars with Maven.

* Standalone jar support in Jython itself does not currently support
  `.pth` files and consequently `site-packages`. Clamp works around
  this by packaging everything in `Lib/`, but this is not desirable
  due to possible collisions. This means the possibility of subtle
  changes in class loader resolution, compared to what Jython offers
  with `sys.path`.

  Moreover, it would be nice if jars in `site-packages`
  could simply be included directly without unpacking.

* The `singlejar` command should generate Jython cache info on all
  included files and bundle in the generated uber jar. It's not clear
  how readily this precaching can be done on a per-jar basis with
  `build_jar`, but cache data is per jar; see
  `{python.cachedir}/packages/*.pkc`; the corresponding code in
  Jython's internals is in `org.python.core.packagecache`.

* Testing and placement in PyPI. Due to the bytecode construction,
  writing unit tests for this type of functionality seems to be
  nontrivial, but still very much needed to move this from an initial
  spike to not being in a pre-alpha stage.


Known issues
============

It's not feasible to use `__new__` in your Python classes that are
clamped. Why not? Java expects that constructing an object for a given
class returns an object of that class! The solution is simple: call a
factory function, in Python or Java, to return arbitrary objects. This
is just a simple, but fundamental, mismatch between Python and Java in
its object model.

A related issue is that you cannot change the `__class__` of an
instance of clamped class.


Variadic constructors
=====================

Clamp currently supports no-arg constructors of clamped classes, as
seen in the generated code below for a Jython proxy:

````java
    public BarClamp() {
        super();
        this.__initProxy__(Py.EmptyObjects);
    }
````

Note that it should be a simple matter to add variadic constructors,
eg `BarClamp(Object... args)`, by using the underlying support in
`__initProxy__`, also generated in Jython proxies:

````java
    public void __initProxy__(final Object[] array) {
        Py.initProxy((PyProxy)this, "clamped", "BarClamp", array);
    }
````

This should be as simple as using `ClassFile.addMethod` to generate
the following code:

````java
    public BarClamp(Object[] args) {
        super(args);
        this.__initProxy__(args);
    }
````

`__initProxy__` will in turn take care of boxing any args as
`PyObject` args.


Supporting Java annotations
===========================

Java annotations are widely used in contemporary Java code. Following
an example in the Apache Quartz documentation, in Quartz one might
write the following in Java:

````java
@PersistJobDataAfterExecution
@DisallowConcurrentExecution
public class ColorJob implements Job {
    ...
}
````

Compiled usage of such annotations is very simple: they simply are
part of the metadata of the class. As metadata, they are then used for
metaprogramming at the Java level, eg, to support introspection or
bytecode rewriting.

It would seem that class decorators would be the natural analogue to
writing this in Jython:

````python
@PersistJobDataAfterExecution
@DisallowConcurrentExecution
class ColorJob(Job):
    ...
````

But there are a few problems. First, Java annotations are
interfaces. To solve, clamp can support a module, let's call it
`clamp.magic`, which when imported, will intercept any subsequent
imports of Java class/method annotations and turn them into class
decorators/function decorators. This requires the top-level script of
`clamp.magic` to insert an appropriate meta importer to
`sys.meta_path`, as described in [PEP 302][].

Next, class decorators are applied *after* type construction in
Python. The solution is for such class decorators to transform
(rewrite) the bytecode for generated Java class to add any desired
annotations, then save it under the original class name. Such
transformations can be readily done with the ASM package by using an
<code>[AnnotationVisitor][]</code>, as documented in section 4.2 of
the [ASM user guide][].

Lastly, saving under the original class name requires a little more
work, because currently all generated classes in Clamp are directly
written using `JarOutputStream`; simply resaving will result in a
`ZipException` of `"duplicate entry"`. This simply requires deferring
the write of a module, including any supporting Java classes, until
the top-level script of the module has completed.

Mapping method annotations to function decorators should likewise be
straightforward. Field annotations currently would only correspond to
static fields, which has direct support in Clamp - there's no Python
syntax equivalent.


<!-- references -->

  [AnnotationVisitor]: http://asm.ow2.org/asm40/javadoc/user/org/objectweb/asm/AnnotationVisitor.html
  [ASM user guide]: http://download.forge.objectweb.org/asm/asm4-guide.pdf
  [clamped]: https://github.com/jimbaker/clamped
  [jython-ssl branch]: https://bitbucket.org/jimbaker/jython-ssl
  [PEP 302]: http://www.python.org/dev/peps/pep-0302/
  [Python descriptors]: http://docs.python.org/2/howto/descriptor.html
  [talk]: https://github.com/jimbaker/clamped/blob/master/talk.pdf
  [talk source]: https://github.com/jimbaker/clamped/blob/master/talk.md
