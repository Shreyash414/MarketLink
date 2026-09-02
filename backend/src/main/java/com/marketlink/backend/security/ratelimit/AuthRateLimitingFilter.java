package com.marketlink.backend.security.ratelimit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.common.response.ErrorResponse;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.NonNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
@RequiredArgsConstructor
public class AuthRateLimitingFilter extends OncePerRequestFilter {

    private final ObjectMapper objectMapper;

    // Maximum 15 requests per minute per IP for sensitive auth routes
    private static final int MAX_REQUESTS_PER_WINDOW = 15;
    private static final long WINDOW_MS = 60_000L; // 1 minute
    private static final int MAX_TRACKED_IPS = 10_000;

    private static class RateWindow {
        final long windowStart;
        final AtomicInteger counter;

        RateWindow(long windowStart) {
            this.windowStart = windowStart;
            this.counter = new AtomicInteger(1);
        }
    }

    private final Map<String, RateWindow> requestCounters = new ConcurrentHashMap<>();

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain filterChain) throws ServletException, IOException {
        String path = request.getRequestURI();

        if (isRateLimitedAuthPath(path, request.getMethod())) {
            String clientIp = getClientIp(request);
            long now = System.currentTimeMillis();

            // Periodic memory cleanup if table exceeds capacity
            if (requestCounters.size() > MAX_TRACKED_IPS) {
                requestCounters.entrySet().removeIf(entry -> (now - entry.getValue().windowStart) > WINDOW_MS);
            }

            RateWindow window = requestCounters.compute(clientIp, (key, existing) -> {
                if (existing == null || (now - existing.windowStart) > WINDOW_MS) {
                    return new RateWindow(now);
                } else {
                    existing.counter.incrementAndGet();
                    return existing;
                }
            });

            if (window != null && window.counter.get() > MAX_REQUESTS_PER_WINDOW) {
                log.warn("Rate limit exceeded for IP: {} on endpoint {}", clientIp, path);
                response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
                response.setContentType(MediaType.APPLICATION_JSON_VALUE);

                ErrorResponse error = ErrorResponse.builder()
                        .success(false)
                        .status(HttpStatus.TOO_MANY_REQUESTS.value())
                        .error(HttpStatus.TOO_MANY_REQUESTS.getReasonPhrase())
                        .message("Too many authentication attempts. Please try again in one minute.")
                        .path(path)
                        .timestamp(Instant.now())
                        .build();

                objectMapper.writeValue(response.getOutputStream(), error);
                return;
            }
        }

        filterChain.doFilter(request, response);
    }

    private boolean isRateLimitedAuthPath(String path, String method) {
        return "POST".equalsIgnoreCase(method) &&
                (path.startsWith("/api/v1/auth/login") || path.startsWith("/api/v1/auth/register"));
    }

    private String getClientIp(HttpServletRequest request) {
        String xfHeader = request.getHeader("X-Forwarded-For");
        if (xfHeader != null && !xfHeader.isBlank()) {
            return xfHeader.split(",")[0].trim();
        }
        return request.getRemoteAddr() != null ? request.getRemoteAddr() : "UNKNOWN_IP";
    }

    public void resetForTesting() {
        requestCounters.clear();
    }
}
