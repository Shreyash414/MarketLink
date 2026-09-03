package com.marketlink.backend.domain.common.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Objects;

/**
 * Geographic Location Value Object representing GPS coordinates.
 * Validates latitude in [-90, 90] and longitude in [-180, 180].
 * Can be embedded in JPA entities (e.g. FarmerProfile, Lot) or used in DTOs.
 */
@Embeddable
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Location implements Serializable {

    private static final long serialVersionUID = 1L;

    public static final double MIN_LATITUDE = -90.0;
    public static final double MAX_LATITUDE = 90.0;
    public static final double MIN_LONGITUDE = -180.0;
    public static final double MAX_LONGITUDE = 180.0;

    @NotNull(message = "Latitude is required")
    @DecimalMin(value = "-90.0", message = "Latitude must be between -90 and 90")
    @DecimalMax(value = "90.0", message = "Latitude must be between -90 and 90")
    @Column(name = "latitude")
    private Double latitude;

    @NotNull(message = "Longitude is required")
    @DecimalMin(value = "-180.0", message = "Longitude must be between -180 and 180")
    @DecimalMax(value = "180.0", message = "Longitude must be between -180 and 180")
    @Column(name = "longitude")
    private Double longitude;

    /**
     * Factory method creating and strictly validating a Location instance.
     *
     * @param latitude  Latitude between -90 and 90
     * @param longitude Longitude between -180 and 180
     * @return Validated Location instance
     * @throws IllegalArgumentException if coordinates are null or out of bounds
     */
    public static Location of(Double latitude, Double longitude) {
        validateCoordinates(latitude, longitude);
        return new Location(latitude, longitude);
    }

    /**
     * Validates coordinate bounds.
     */
    public static void validateCoordinates(Double latitude, Double longitude) {
        if (latitude == null) {
            throw new IllegalArgumentException("Latitude cannot be null");
        }
        if (longitude == null) {
            throw new IllegalArgumentException("Longitude cannot be null");
        }
        if (latitude < MIN_LATITUDE || latitude > MAX_LATITUDE) {
            throw new IllegalArgumentException(
                    String.format("Latitude %s is out of range [%s, %s]", latitude, MIN_LATITUDE, MAX_LATITUDE)
            );
        }
        if (longitude < MIN_LONGITUDE || longitude > MAX_LONGITUDE) {
            throw new IllegalArgumentException(
                    String.format("Longitude %s is out of range [%s, %s]", longitude, MIN_LONGITUDE, MAX_LONGITUDE)
            );
        }
    }

    /**
     * Checks if current coordinates are valid.
     */
    public boolean isValid() {
        return latitude != null && longitude != null
                && latitude >= MIN_LATITUDE && latitude <= MAX_LATITUDE
                && longitude >= MIN_LONGITUDE && longitude <= MAX_LONGITUDE;
    }
}
