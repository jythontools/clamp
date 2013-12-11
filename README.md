clamp
=====

Implements clamp in Python. Pre-alpha version - API subject to change.

You need to install. Soon this will be on PyPI, before then, in the checkout directory:

````bash
$ jython27 setup.py install
````

Example project using this package; this provides crucial documentation on how to use Clamp by going through an example:
https://github.com/jimbaker/clamped

The clamp project supports setuptools integration.

To create a jar for a clamped module in site-packages/jars and
register this new jar in site-packages/jar.pth:

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

* Add support for [variadic constructors](#variadic-constructors) of
  clamped classes. This means that in Java, using code can simply
  perform `new BarClamp(x, y, ...)`; in Python, `BarClamp(x, y, ...)`.

* Provide basic support for annotations.

* Extend setup.py support of install so that it can use build_jar; see
  http://www.niteoweb.com/blog/setuptools-run-custom-code-during-install
  for some ideas.

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

* Standalone jar support in Jython does not currently support `.pth`
  files and consequently `site-packages`. Clamp works around this by
  packaging everything in `Lib/`, but this is not desirable due to
  possible collisions. Also, it would be nice if jars in
  `site-packages` could simply be included directly without unpacking.


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
  [PEP 302]: http://www.python.org/dev/peps/pep-0302/
  [Python descriptors]: http://docs.python.org/2/howto/descriptor.html
