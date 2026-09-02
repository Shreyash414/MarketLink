package com.marketlink.backend.offer;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.offer.entity.Offer;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
import com.marketlink.backend.domain.offer.repository.OfferRepository;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.offer.dto.CreateOfferRequest;
import com.marketlink.backend.offer.dto.OfferResponse;
import com.marketlink.backend.offer.service.OfferService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OfferServiceTest {

    @Mock
    private OfferRepository offerRepository;

    @Mock
    private LotRepository lotRepository;

    @Mock
    private BuyerProfileRepository buyerProfileRepository;

    @InjectMocks
    private OfferService offerService;

    private UUID farmerId;
    private UUID buyerId1;
    private UUID buyerId2;
    private UUID lotId;
    private Lot publishedLot;

    @BeforeEach
    void setUp() {
        farmerId = UUID.randomUUID();
        buyerId1 = UUID.randomUUID();
        buyerId2 = UUID.randomUUID();
        lotId = UUID.randomUUID();

        publishedLot = Lot.builder()
                .id(lotId)
                .farmerId(farmerId)
                .cropName("ONION")
                .quantity(500.0)
                .unit("KG")
                .expectedPrice(35.0)
                .minimumAcceptablePrice(28.0)
                .status(LotStatus.PUBLISHED)
                .build();
    }

    @Test
    @DisplayName("Buyer creates valid offer on published lot (transitions lot to OFFER_RECEIVED)")
    void testCreateOffer_Success() {
        CreateOfferRequest request = CreateOfferRequest.builder()
                .offeredPrice(32.0)
                .quantity(500.0)
                .notes("Immediate pickup")
                .build();

        Offer savedOffer = Offer.builder()
                .id(UUID.randomUUID())
                .lotId(lotId)
                .buyerId(buyerId1)
                .offeredPrice(32.0)
                .quantity(500.0)
                .status(OfferStatus.PENDING)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();

        when(lotRepository.findById(lotId)).thenReturn(Optional.of(publishedLot));
        when(offerRepository.save(any(Offer.class))).thenReturn(savedOffer);
        when(buyerProfileRepository.findById(buyerId1)).thenReturn(Optional.of(BuyerProfile.builder()
                .userId(buyerId1)
                .businessName("Agro Traders")
                .build()));

        OfferResponse response = offerService.createOffer(buyerId1, lotId, request);

        assertThat(response).isNotNull();
        assertThat(response.getOfferedPrice()).isEqualTo(32.0);
        assertThat(response.getStatus()).isEqualTo(OfferStatus.PENDING);
        assertThat(publishedLot.getStatus()).isEqualTo(LotStatus.OFFER_RECEIVED);
        verify(lotRepository).save(publishedLot);
    }

    @Test
    @DisplayName("Reject offer if price is below farmer's minimumAcceptablePrice")
    void testCreateOffer_BelowMinimumPrice() {
        CreateOfferRequest request = CreateOfferRequest.builder()
                .offeredPrice(25.0) // below 28.0 min acceptable
                .quantity(500.0)
                .build();

        when(lotRepository.findById(lotId)).thenReturn(Optional.of(publishedLot));

        assertThatThrownBy(() -> offerService.createOffer(buyerId1, lotId, request))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("minimum acceptable price");

        verify(offerRepository, never()).save(any(Offer.class));
    }

    @Test
    @DisplayName("Farmer accepts offer: transitions lot and offer to ACCEPTED, auto-rejects other pending offers")
    void testAcceptOffer_Success() {
        UUID offerId1 = UUID.randomUUID();
        UUID offerId2 = UUID.randomUUID();

        Offer offer1 = Offer.builder()
                .id(offerId1)
                .lotId(lotId)
                .buyerId(buyerId1)
                .offeredPrice(33.0)
                .quantity(500.0)
                .status(OfferStatus.PENDING)
                .build();

        Offer offer2 = Offer.builder()
                .id(offerId2)
                .lotId(lotId)
                .buyerId(buyerId2)
                .offeredPrice(30.0)
                .quantity(500.0)
                .status(OfferStatus.PENDING)
                .build();

        when(offerRepository.findById(offerId1)).thenReturn(Optional.of(offer1));
        when(lotRepository.findById(lotId)).thenReturn(Optional.of(publishedLot));
        when(offerRepository.findByLotIdAndStatus(lotId, OfferStatus.PENDING))
                .thenReturn(List.of(offer1, offer2));
        when(offerRepository.save(any(Offer.class))).thenAnswer(i -> i.getArgument(0));

        OfferResponse response = offerService.acceptOffer(farmerId, offerId1);

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(OfferStatus.ACCEPTED);
        assertThat(publishedLot.getStatus()).isEqualTo(LotStatus.ACCEPTED);
        assertThat(offer2.getStatus()).isEqualTo(OfferStatus.REJECTED);
    }
}
