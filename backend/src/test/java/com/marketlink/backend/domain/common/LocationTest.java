package com.marketlink.backend.domain.common;

import com.marketlink.backend.domain.common.entity.Location;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class LocationTest {

    private Validator validator;

    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @Test
    @DisplayName("Valid coordinates are accepted")
    void testValidCoordinates() {
        Location loc = Location.of(28.6139, 77.2090);
        assertEquals(28.6139, loc.getLatitude());
        assertEquals(77.2090, loc.getLongitude());
        assertTrue(loc.isValid());

        Set<ConstraintViolation<Location>> violations = validator.validate(loc);
        assertTrue(violations.isEmpty());
    }

    @Test
    @DisplayName("Boundary latitude: -90.0 is valid")
    void testBoundaryLatitudeMin() {
        Location loc = Location.of(-90.0, 0.0);
        assertEquals(-90.0, loc.getLatitude());
        assertTrue(loc.isValid());
        assertTrue(validator.validate(loc).isEmpty());
    }

    @Test
    @DisplayName("Boundary latitude: 90.0 is valid")
    void testBoundaryLatitudeMax() {
        Location loc = Location.of(90.0, 0.0);
        assertEquals(90.0, loc.getLatitude());
        assertTrue(loc.isValid());
        assertTrue(validator.validate(loc).isEmpty());
    }

    @Test
    @DisplayName("Boundary longitude: -180.0 is valid")
    void testBoundaryLongitudeMin() {
        Location loc = Location.of(0.0, -180.0);
        assertEquals(-180.0, loc.getLongitude());
        assertTrue(loc.isValid());
        assertTrue(validator.validate(loc).isEmpty());
    }

    @Test
    @DisplayName("Boundary longitude: 180.0 is valid")
    void testBoundaryLongitudeMax() {
        Location loc = Location.of(0.0, 180.0);
        assertEquals(180.0, loc.getLongitude());
        assertTrue(loc.isValid());
        assertTrue(validator.validate(loc).isEmpty());
    }

    @Test
    @DisplayName("Latitude > 90 is rejected")
    void testLatitudeAboveMaxRejected() {
        assertThrows(IllegalArgumentException.class, () -> Location.of(90.0001, 77.0));

        Location loc = new Location(90.0001, 77.0);
        Set<ConstraintViolation<Location>> violations = validator.validate(loc);
        assertFalse(violations.isEmpty());
        assertFalse(loc.isValid());
    }

    @Test
    @DisplayName("Latitude < -90 is rejected")
    void testLatitudeBelowMinRejected() {
        assertThrows(IllegalArgumentException.class, () -> Location.of(-90.0001, 77.0));

        Location loc = new Location(-90.0001, 77.0);
        Set<ConstraintViolation<Location>> violations = validator.validate(loc);
        assertFalse(violations.isEmpty());
        assertFalse(loc.isValid());
    }

    @Test
    @DisplayName("Longitude > 180 is rejected")
    void testLongitudeAboveMaxRejected() {
        assertThrows(IllegalArgumentException.class, () -> Location.of(28.0, 180.0001));

        Location loc = new Location(28.0, 180.0001);
        Set<ConstraintViolation<Location>> violations = validator.validate(loc);
        assertFalse(violations.isEmpty());
        assertFalse(loc.isValid());
    }

    @Test
    @DisplayName("Longitude < -180 is rejected")
    void testLongitudeBelowMinRejected() {
        assertThrows(IllegalArgumentException.class, () -> Location.of(28.0, -180.0001));

        Location loc = new Location(28.0, -180.0001);
        Set<ConstraintViolation<Location>> violations = validator.validate(loc);
        assertFalse(violations.isEmpty());
        assertFalse(loc.isValid());
    }

    @Test
    @DisplayName("Null latitude or longitude is rejected")
    void testNullCoordinatesRejected() {
        assertThrows(IllegalArgumentException.class, () -> Location.of(null, 77.0));
        assertThrows(IllegalArgumentException.class, () -> Location.of(28.0, null));

        Location locNullLat = new Location(null, 77.0);
        assertFalse(locNullLat.isValid());
        assertFalse(validator.validate(locNullLat).isEmpty());

        Location locNullLng = new Location(28.0, null);
        assertFalse(locNullLng.isValid());
        assertFalse(validator.validate(locNullLng).isEmpty());
    }

    @Test
    @DisplayName("Precision is preserved without mutation")
    void testCoordinatePrecisionPreserved() {
        double lat = 28.61393912345;
        double lng = 77.20902198765;
        Location loc = Location.of(lat, lng);
        assertEquals(lat, loc.getLatitude());
        assertEquals(lng, loc.getLongitude());
    }
}
