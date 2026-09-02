package com.marketlink.backend.domain.user.entity;

import jakarta.persistence.*;
import lombok.*;

import java.util.UUID;

@Entity
@Table(name = "farmer_profiles")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FarmerProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, unique = true)
    private UUID userId;

    @Column(nullable = false, length = 100)
    private String fullName;

    private String village;
    private String district;
    private String state;
    private Double landHoldingAcres;

    @Column(length = 20)
    @Builder.Default
    private String preferredLanguage = "en";
}
