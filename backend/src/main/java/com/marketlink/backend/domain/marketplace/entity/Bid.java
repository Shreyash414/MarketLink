package com.marketlink.backend.domain.marketplace.entity;

import com.marketlink.backend.domain.marketplace.enums.BidStatus;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "marketplace_bids")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Bid {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID lotId;

    @Column(nullable = false)
    private UUID buyerId;

    @Column(nullable = false)
    private Double offeredPricePerKg;

    @Column(nullable = false)
    private Double totalQuantityKg;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private BidStatus status = BidStatus.PENDING;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = Instant.now();
        if (this.status == null) {
            this.status = BidStatus.PENDING;
        }
    }
}
