package com.marketlink.backend.domain.marketprice.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "market_prices", indexes = {
        @Index(name = "idx_market_price_crop_market_date", columnList = "cropId, marketId, priceDate"),
        @Index(name = "idx_market_price_date", columnList = "priceDate"),
        @Index(name = "idx_market_price_crop", columnList = "cropId"),
        @Index(name = "idx_market_price_market", columnList = "marketId")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MarketPrice {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID cropId;

    @Column(nullable = false)
    private UUID marketId;

    @Column(name = "price_date", nullable = false)
    private LocalDate priceDate;

    @Column(nullable = false)
    private Double minPrice;

    @Column(nullable = false)
    private Double maxPrice;

    @Column(nullable = false)
    private Double modalPrice;

    private Double arrivalQuantity;

    @Column(nullable = false, length = 20)
    @Builder.Default
    private String unit = "QUINTAL";

    @Column(length = 100)
    @Builder.Default
    private String source = "APMC_AGMARKNET";

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = Instant.now();
        if (this.priceDate == null) {
            this.priceDate = LocalDate.now();
        }
        if (this.unit == null || this.unit.isBlank()) {
            this.unit = "QUINTAL";
        }
        if (this.source == null || this.source.isBlank()) {
            this.source = "APMC_AGMARKNET";
        }
    }
}
