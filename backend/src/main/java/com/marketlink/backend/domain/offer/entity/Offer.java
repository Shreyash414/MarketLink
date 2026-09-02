package com.marketlink.backend.domain.offer.entity;

import com.marketlink.backend.domain.offer.enums.OfferStatus;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "offers", indexes = {
        @Index(name = "idx_offer_lot_id", columnList = "lotId"),
        @Index(name = "idx_offer_buyer_id", columnList = "buyerId"),
        @Index(name = "idx_offer_status", columnList = "status"),
        @Index(name = "idx_offer_created_at", columnList = "createdAt")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Offer {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID lotId;

    @Column(nullable = false)
    private UUID buyerId;

    @Column(nullable = false)
    private Double offeredPrice;

    @Column(nullable = false)
    private Double quantity;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 25)
    @Builder.Default
    private OfferStatus status = OfferStatus.PENDING;

    @Column(length = 500)
    private String notes;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        if (this.status == null) {
            this.status = OfferStatus.PENDING;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = Instant.now();
    }
}
