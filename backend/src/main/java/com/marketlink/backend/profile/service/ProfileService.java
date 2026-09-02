package com.marketlink.backend.profile.service;

import com.marketlink.backend.common.exception.AccessForbiddenException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.profile.dto.BuyerProfileDto;
import com.marketlink.backend.profile.dto.FarmerProfileDto;
import com.marketlink.backend.profile.dto.UpdateBuyerProfileRequest;
import com.marketlink.backend.profile.dto.UpdateFarmerProfileRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProfileService {

    private final UserRepository userRepository;
    private final FarmerProfileRepository farmerProfileRepository;
    private final BuyerProfileRepository buyerProfileRepository;

    @Transactional(readOnly = true)
    public FarmerProfileDto getFarmerProfile(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getRole() != Role.FARMER) {
            throw new AccessForbiddenException("User is not registered as a farmer");
        }

        FarmerProfile profile = farmerProfileRepository.findByUserId(userId).orElse(null);
        return FarmerProfileDto.fromEntities(user, profile);
    }

    @Transactional
    public FarmerProfileDto updateFarmerProfile(UUID userId, UpdateFarmerProfileRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getRole() != Role.FARMER) {
            throw new AccessForbiddenException("User is not registered as a farmer");
        }

        FarmerProfile profile = farmerProfileRepository.findByUserId(userId)
                .orElseGet(() -> FarmerProfile.builder().userId(userId).build());

        if (request.getFullName() != null) profile.setFullName(request.getFullName());
        if (request.getVillage() != null) profile.setVillage(request.getVillage());
        if (request.getDistrict() != null) profile.setDistrict(request.getDistrict());
        if (request.getState() != null) profile.setState(request.getState());
        if (request.getLandHoldingAcres() != null) profile.setLandHoldingAcres(request.getLandHoldingAcres());
        if (request.getPreferredLanguage() != null) profile.setPreferredLanguage(request.getPreferredLanguage());

        // Note: verificationState and role remain untouched on the User entity
        profile = farmerProfileRepository.save(profile);
        return FarmerProfileDto.fromEntities(user, profile);
    }

    @Transactional(readOnly = true)
    public BuyerProfileDto getBuyerProfile(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getRole() != Role.BUYER) {
            throw new AccessForbiddenException("User is not registered as a buyer");
        }

        BuyerProfile profile = buyerProfileRepository.findByUserId(userId).orElse(null);
        return BuyerProfileDto.fromEntities(user, profile);
    }

    @Transactional
    public BuyerProfileDto updateBuyerProfile(UUID userId, UpdateBuyerProfileRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getRole() != Role.BUYER) {
            throw new AccessForbiddenException("User is not registered as a buyer");
        }

        BuyerProfile profile = buyerProfileRepository.findByUserId(userId)
                .orElseGet(() -> BuyerProfile.builder().userId(userId).build());

        if (request.getBusinessName() != null) profile.setBusinessName(request.getBusinessName());
        if (request.getGstin() != null) profile.setGstin(request.getGstin());
        if (request.getDistrict() != null) profile.setDistrict(request.getDistrict());
        if (request.getState() != null) profile.setState(request.getState());
        if (request.getTradeCategory() != null) profile.setTradeCategory(request.getTradeCategory());

        // Note: verificationState and role remain untouched on the User entity
        profile = buyerProfileRepository.save(profile);
        return BuyerProfileDto.fromEntities(user, profile);
    }
}
