package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * DTO matching Model-app MarketDataResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppMarketDataResponse {

    private String commodity;

    @JsonProperty("data_source")
    private String dataSource;

    @JsonProperty("is_live")
    private Boolean isLive;

    @JsonProperty("record_count")
    private Integer recordCount;

    @Builder.Default
    private List<ModelAppMandiPriceRecord> records = List.of();
}
