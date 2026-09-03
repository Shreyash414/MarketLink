package com.marketlink.backend.common.context;

import org.slf4j.MDC;

import java.util.UUID;

/**
 * Thread-local context holder for correlation IDs across HTTP requests and outbound service calls.
 */
public final class CorrelationIdContext {

    public static final String CORRELATION_ID_HEADER = "X-Correlation-ID";
    public static final String MDC_KEY = "correlationId";

    private static final ThreadLocal<String> CURRENT_CORRELATION_ID = new ThreadLocal<>();

    private CorrelationIdContext() {
    }

    /**
     * Retrieves the correlation ID for the current thread, or generates a new one if unset.
     */
    public static String getCorrelationId() {
        String id = CURRENT_CORRELATION_ID.get();
        if (id == null || id.isBlank()) {
            id = UUID.randomUUID().toString();
            setCorrelationId(id);
        }
        return id;
    }

    /**
     * Sets the correlation ID for the current thread and updates SLF4J MDC.
     */
    public static void setCorrelationId(String correlationId) {
        if (correlationId != null && !correlationId.isBlank()) {
            CURRENT_CORRELATION_ID.set(correlationId);
            MDC.put(MDC_KEY, correlationId);
        } else {
            clear();
        }
    }

    /**
     * Clears the correlation ID from thread local and MDC.
     */
    public static void clear() {
        CURRENT_CORRELATION_ID.remove();
        MDC.remove(MDC_KEY);
    }
}
