import org.junit.Test;
import static org.junit.Assert.*;

import org.clamp_samples.callable.CallableSample;

public class TestCallable {
    @Test
    public void testCallable() throws Exception {
        CallableSample callable = new CallableSample();

        assertEquals(42, callable.call());
    }
}