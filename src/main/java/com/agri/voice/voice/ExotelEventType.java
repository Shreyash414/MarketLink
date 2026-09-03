package com.agri.voice.voice;

import java.util.Arrays;
import java.util.Locale;
import java.util.Optional;

public enum ExotelEventType {
    CONNECTED("connected"),
    START("start"),
    MEDIA("media"),
    DTMF("dtmf"),
    STOP("stop"),
    MARK("mark"),
    CLEAR("clear");

    private final String wireValue;

    ExotelEventType(String wireValue) {
        this.wireValue = wireValue;
    }

    public String wireValue() {
        return wireValue;
    }

    public static Optional<ExotelEventType> fromWireValue(String value) {
        if (value == null || value.isBlank()) {
            return Optional.empty();
        }

        String normalized = value.trim().toLowerCase(Locale.ROOT);
        return Arrays.stream(values())
                .filter(type -> type.wireValue.equals(normalized))
                .findFirst();
    }
}
