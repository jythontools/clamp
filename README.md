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

* Provide basic support for annotations.

* Extend setup.py support of install so that it can use build_jar; see
  http://www.niteoweb.com/blog/setuptools-run-custom-code-during-install
  for some ideas.

* [Annotation magic](#annotations). It would be nice to import
  annotations into Python, use as class decorators and function
  decorators, and then still compile a Java class that works.

* Instance fields support, comparable to `__slots__`, but baked into
  the emitted Java class. Such support would directly enable emitted
  clases to be used as POJOs by using Java code.

* Map Python descriptors to Java's convention of getters/setters. Note
  that `__delete__` is not a mappable idea!


<a name="annotations">Supporting Java annotations</a>
=====================================================

Java annotations are widely used in contemporary Java code. For
example, in Apache Quartz, one might write the following in Java:

````java
@PersistJobDataAfterExecution
@DisallowConcurrentExecution
public class ColorJob implements Job {
    ...
}
````

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
(rewrite) the bytecode for generated Java class, then save it under
the original class name. Such transformations can be readily done with
the ASM package by using an <code>[AnnotationVisitor][]</code>, as
documented in section 4.2 of the [ASM user guide][].

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
