package com.marketlink.backend.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.data.mongodb.repository.config.EnableMongoRepositories;

@Configuration
@Profile("!test")
@EnableMongoRepositories(basePackages = {"com.marketlink.backend.domain.image.repository"})
public class MongoConfig {
}
