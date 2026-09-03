package com.agri.voice.voice.dto;

public sealed interface ExotelEvent permits ClearEvent, ConnectedEvent, DtmfEvent,
        MarkEvent, MediaEvent, StartEvent, StopEvent {

    String event();
}
