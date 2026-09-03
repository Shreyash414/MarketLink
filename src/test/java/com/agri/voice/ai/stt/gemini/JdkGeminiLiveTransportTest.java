package com.agri.voice.ai.stt.gemini;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class JdkGeminiLiveTransportTest {

    private final WebSocket socket = mock(WebSocket.class);
    private final RecordingListener listener = new RecordingListener();
    private JdkGeminiLiveTransport.ProviderListener providerListener;

    @BeforeEach
    void setUp() {
        JdkGeminiLiveTransport transport = new JdkGeminiLiveTransport(mock(HttpClient.class));
        providerListener = transport.new ProviderListener(listener);
    }

    @Test
    void forwardsCompleteTextMessage() {
        providerListener.onText(socket, "{\"setupComplete\":{}}", true);

        assertThat(listener.messages).containsExactly("{\"setupComplete\":{}}");
        assertThat(listener.errors).isEmpty();
        verify(socket).request(1);
    }

    @Test
    void assemblesFragmentedTextMessage() {
        providerListener.onText(socket, "{\"setup", false);
        providerListener.onText(socket, "Complete\":{}}", true);

        assertThat(listener.messages).containsExactly("{\"setupComplete\":{}}");
        assertThat(listener.errors).isEmpty();
    }

    @Test
    void decodesCompleteUtf8BinaryMessage() {
        String json = "{\"serverContent\":{\"inputTranscription\":{\"text\":\"गेहूं\"}}}";

        providerListener.onBinary(socket, utf8(json), true);

        assertThat(listener.messages).containsExactly(json);
        assertThat(listener.errors).isEmpty();
        verify(socket).request(1);
    }

    @Test
    void assemblesFragmentedBinaryMessageIncludingSplitUtf8CodePoint() {
        String json = "{\"serverContent\":{\"interimInputTranscription\":{\"text\":\"गेहूं\"}}}";
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        int split = indexInsideMultibyteCodePoint(bytes);

        providerListener.onBinary(socket, ByteBuffer.wrap(bytes, 0, split), false);
        providerListener.onBinary(socket, ByteBuffer.wrap(bytes, split, bytes.length - split), true);

        assertThat(listener.messages).containsExactly(json);
        assertThat(listener.errors).isEmpty();
    }

    @Test
    void rejectsMalformedUtf8BinaryWithoutExposingPayload() {
        providerListener.onBinary(socket, ByteBuffer.wrap(new byte[] {(byte) 0xc3, 0x28}), true);

        assertThat(listener.messages).isEmpty();
        assertThat(listener.errors).singleElement().satisfies(error -> {
            assertThat(error).isInstanceOf(IllegalArgumentException.class);
            assertThat(error.getMessage()).isEqualTo("provider binary response was not valid UTF-8");
        });
    }

    @Test
    void forwardsCloseStatusAndReason() {
        providerListener.onClose(socket, 1000, "complete");

        assertThat(listener.closeCode).isEqualTo(1000);
        assertThat(listener.closeReason).isEqualTo("complete");
    }

    @Test
    void forwardsTransportError() {
        IllegalStateException failure = new IllegalStateException("connection failed");

        providerListener.onError(socket, failure);

        assertThat(listener.errors).containsExactly(failure);
    }

    private ByteBuffer utf8(String value) {
        return ByteBuffer.wrap(value.getBytes(StandardCharsets.UTF_8));
    }

    private int indexInsideMultibyteCodePoint(byte[] bytes) {
        for (int index = 1; index < bytes.length; index++) {
            if ((bytes[index] & 0xc0) == 0x80) {
                return index;
            }
        }
        throw new AssertionError("test data does not contain a multibyte UTF-8 code point");
    }

    private static final class RecordingListener implements GeminiLiveTransport.Listener {

        private final List<String> messages = new ArrayList<>();
        private final List<Throwable> errors = new ArrayList<>();
        private Integer closeCode;
        private String closeReason;

        @Override
        public void onText(String message) {
            messages.add(message);
        }

        @Override
        public void onClosed(int statusCode, String reason) {
            closeCode = statusCode;
            closeReason = reason;
        }

        @Override
        public void onError(Throwable error) {
            errors.add(error);
        }
    }
}
