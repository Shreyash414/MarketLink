package com.marketlink.backend.voice.service;

import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.offer.entity.Offer;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
import com.marketlink.backend.domain.offer.repository.OfferRepository;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.marketprice.dto.MarketPriceResponse;
import com.marketlink.backend.marketprice.service.MarketPriceService;
import com.marketlink.backend.offer.dto.OfferResponse;
import com.marketlink.backend.offer.service.OfferService;
import com.marketlink.backend.voice.dto.VoiceOfferResponse;
import com.marketlink.backend.voice.dto.VoicePriceQueryResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class VoiceChannelService {

    private final MarketPriceService marketPriceService;
    private final OfferService offerService;
    private final CropRepository cropRepository;
    private final MarketRepository marketRepository;
    private final LotRepository lotRepository;
    private final OfferRepository offerRepository;
    private final BuyerProfileRepository buyerProfileRepository;

    @Transactional(readOnly = true)
    public VoicePriceQueryResponse queryVoicePrice(String cropName, String marketName) {
        String cleanCrop = cropName.trim().toUpperCase();
        Crop crop = cropRepository.findByNameIgnoreCase(cleanCrop)
                .orElseThrow(() -> new ResourceNotFoundException("Crop not found: " + cropName));

        UUID marketId = null;
        String resolvedMarketName = "major markets";
        if (marketName != null && !marketName.isBlank()) {
            List<Market> markets = marketRepository.findByNameIgnoreCase(marketName.trim());
            if (!markets.isEmpty()) {
                Market market = markets.getFirst();
                marketId = market.getId();
                resolvedMarketName = market.getName();
            }
        }

        MarketPriceResponse mp = marketPriceService.getLatestMarketPrice(crop.getId(), marketId);

        String summary = String.format("The latest modal price of %s at %s is %.0f Rupees per %s recorded on %s.",
                crop.getName(),
                mp.getMarketName() != null ? mp.getMarketName() : resolvedMarketName,
                mp.getModalPrice(),
                mp.getUnit() != null ? mp.getUnit() : "QUINTAL",
                mp.getPriceDate() != null ? mp.getPriceDate().toString() : "today");

        return VoicePriceQueryResponse.builder()
                .cropName(crop.getName())
                .marketName(mp.getMarketName() != null ? mp.getMarketName() : resolvedMarketName)
                .modalPrice(mp.getModalPrice())
                .unit(mp.getUnit())
                .priceDate(mp.getPriceDate())
                .voiceSummary(summary)
                .build();
    }

    @Transactional(readOnly = true)
    public List<VoiceOfferResponse> getPendingOffersForFarmer(UUID farmerId) {
        List<Lot> farmerLots = lotRepository.findByFarmerIdOrderByCreatedAtDesc(farmerId);
        List<VoiceOfferResponse> voiceOffers = new ArrayList<>();

        for (Lot lot : farmerLots) {
            if (lot.getStatus() == LotStatus.OFFER_RECEIVED || lot.getStatus() == LotStatus.PUBLISHED) {
                List<Offer> pendingOffers = offerRepository.findByLotIdAndStatus(lot.getId(), OfferStatus.PENDING);
                for (Offer offer : pendingOffers) {
                    String buyerBusiness = buyerProfileRepository.findById(offer.getBuyerId())
                            .map(b -> b.getBusinessName())
                            .orElse("A verified buyer");

                    String summary = String.format("Offer for %.0f %s of %s from %s at %.0f Rupees per %s.",
                            offer.getQuantity(),
                            lot.getUnit(),
                            lot.getCropName(),
                            buyerBusiness,
                            offer.getOfferedPrice(),
                            lot.getUnit());

                    voiceOffers.add(VoiceOfferResponse.builder()
                            .offerId(offer.getId())
                            .lotId(lot.getId())
                            .cropName(lot.getCropName())
                            .buyerBusinessName(buyerBusiness)
                            .offeredPrice(offer.getOfferedPrice())
                            .quantity(offer.getQuantity())
                            .unit(lot.getUnit())
                            .voiceSummary(summary)
                            .build());
                }
            }
        }

        return voiceOffers;
    }

    @Transactional
    public String acceptOfferByVoice(UUID farmerId, UUID offerId) {
        OfferResponse response = offerService.acceptOffer(farmerId, offerId);
        return String.format("Offer of %.0f Rupees per %s for %s has been successfully accepted.",
                response.getOfferedPrice(),
                response.getUnit() != null ? response.getUnit() : "KG",
                response.getCropName());
    }
}
