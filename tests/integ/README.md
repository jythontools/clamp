Running tests
=============
Before you run the tests make sure you've built the latest clamp.

Running tests themselves is really easy:
````bash
$ cd tests/integ
$ jython27 setup.py test
````

The output would look something like this:
````
running test
running build_jar
Ran 2 tests in 5s, failures: 0
````

Developing tests
================
There are two parts to the tests, the python side to be clamped lives in
`clamp_samples` directory and the JUnit tests live in `junit_tests` directory.

Essentially, we create some sample Python class, then we test it from the 
Java side using JUnit.

The Python bits
---------------
* Create a new sample python file which would contain something like below:

````python
from java.lang import Long, Object
from clamp import clamp_base, Constant

TestBase = clamp_base("org")


class ConstSample(TestBase, Object):
    myConstant = Constant(Long(1234), Long.TYPE)
````

* Add an import of it in the `__init__.py` (so that clamp will notice it when "clamping".

The Java bits
-------------
In the `junit_tests` directory add a new Test[Sample].java file and write a JUnit test(s).

````java
import org.junit.Test;
import static org.junit.Assert.*;

import org.clamp_samples.const.ConstSample;

public class TestConstant {
    @Test
    public void testConstant() throws Exception {
        ConstTest constObj = new ConstTest();

        assertEquals(1234, constObj.myConstant);
    }
}
````
