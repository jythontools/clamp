import org.junit.Test;
import static org.junit.Assert.*;

import org.clamp_samples.const_.ConstSample;

public class TestConstant {
    @Test
    public void testConstant() throws Exception {
        ConstSample constObj = new ConstSample();

        assertEquals(1234, constObj.myConstant);
    }
}