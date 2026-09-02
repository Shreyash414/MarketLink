package com.marketlink.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@SpringBootApplication
@EnableJpaRepositories(basePackages = {
        "com.marketlink.backend.domain.user.repository",
        "com.marketlink.backend.domain.marketplace.repository",
        "com.marketlink.backend.domain.content.repository",
        "com.marketlink.backend.domain.crop.repository",
        "com.marketlink.backend.domain.market.repository",
        "com.marketlink.backend.domain.quality.repository",
        "com.marketlink.backend.domain.marketprice.repository",
        "com.marketlink.backend.domain.offer.repository"
})
public class MarketLinkBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(MarketLinkBackendApplication.class, args);
    }
}
