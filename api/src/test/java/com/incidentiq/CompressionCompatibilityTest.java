package com.incidentiq;

import java.nio.charset.StandardCharsets;
import net.jpountz.lz4.LZ4Factory;
import org.junit.jupiter.api.Test;
import org.xerial.snappy.Snappy;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;

class CompressionCompatibilityTest {
    private static final byte[] PAYLOAD = "incidentiq-kafka-native-codec-compatibility".repeat(32)
            .getBytes(StandardCharsets.UTF_8);

    @Test
    void patchedSnappyNativeCodecRoundTrips() throws Exception {
        assertArrayEquals(PAYLOAD, Snappy.uncompress(Snappy.compress(PAYLOAD)));
    }

    @Test
    void patchedLz4CodecRoundTrips() {
        var factory = LZ4Factory.fastestInstance();
        var compressed = factory.fastCompressor().compress(PAYLOAD);
        var restored = new byte[PAYLOAD.length];
        factory.fastDecompressor().decompress(compressed, 0, restored, 0, restored.length);
        assertArrayEquals(PAYLOAD, restored);
    }
}
