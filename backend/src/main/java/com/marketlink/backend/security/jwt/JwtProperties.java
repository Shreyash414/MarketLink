package com.marketlink.backend.security.jwt;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "marketlink.security.jwt")
public class JwtProperties {
    private String secret = "404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970";
    private long expirationMs = 86400000L; // 24 hours
    private long refreshExpirationMs = 604800000L; // 7 days
}
