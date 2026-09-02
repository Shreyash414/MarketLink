package com.marketlink.backend.crop.service;

import com.marketlink.backend.common.exception.DuplicateResourceException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.crop.dto.CreateCropRequest;
import com.marketlink.backend.crop.dto.CropResponse;
import com.marketlink.backend.crop.dto.UpdateCropRequest;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class CropService {

    private final CropRepository cropRepository;

    @Transactional
    public CropResponse createCrop(CreateCropRequest request) {
        String normalizedName = request.getName().trim().toUpperCase();
        if (cropRepository.existsByNameIgnoreCase(normalizedName)) {
            throw new DuplicateResourceException("Crop with name '" + normalizedName + "' already exists");
        }

        Crop crop = Crop.builder()
                .name(normalizedName)
                .category(request.getCategory().trim().toUpperCase())
                .unit(request.getUnit().trim().toUpperCase())
                .active(true)
                .build();

        Crop savedCrop = cropRepository.save(crop);
        log.info("Created new master crop record: id={}, name={}", savedCrop.getId(), savedCrop.getName());
        return CropResponse.fromEntity(savedCrop);
    }

    @Transactional(readOnly = true)
    public CropResponse getCropById(UUID id) {
        Crop crop = cropRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Crop not found with id: " + id));
        return CropResponse.fromEntity(crop);
    }

    @Transactional(readOnly = true)
    public List<CropResponse> getAllCrops(Boolean activeOnly, String category) {
        List<Crop> crops;
        boolean filterActive = (activeOnly == null || activeOnly);

        if (category != null && !category.isBlank()) {
            String cat = category.trim();
            if (filterActive) {
                crops = cropRepository.findByCategoryIgnoreCaseAndActiveTrueOrderByNameAsc(cat);
            } else {
                crops = cropRepository.findByCategoryIgnoreCaseOrderByNameAsc(cat);
            }
        } else {
            if (filterActive) {
                crops = cropRepository.findByActiveTrueOrderByNameAsc();
            } else {
                crops = cropRepository.findAll();
            }
        }

        return crops.stream()
                .map(CropResponse::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional
    public CropResponse updateCrop(UUID id, UpdateCropRequest request) {
        Crop crop = cropRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Crop not found with id: " + id));

        if (request.getName() != null && !request.getName().isBlank()) {
            String normalizedName = request.getName().trim().toUpperCase();
            if (cropRepository.existsByNameIgnoreCaseAndIdNot(normalizedName, id)) {
                throw new DuplicateResourceException("Another crop with name '" + normalizedName + "' already exists");
            }
            crop.setName(normalizedName);
        }

        if (request.getCategory() != null && !request.getCategory().isBlank()) {
            crop.setCategory(request.getCategory().trim().toUpperCase());
        }

        if (request.getUnit() != null && !request.getUnit().isBlank()) {
            crop.setUnit(request.getUnit().trim().toUpperCase());
        }

        if (request.getActive() != null) {
            crop.setActive(request.getActive());
        }

        Crop updatedCrop = cropRepository.save(crop);
        log.info("Updated master crop record: id={}, name={}", updatedCrop.getId(), updatedCrop.getName());
        return CropResponse.fromEntity(updatedCrop);
    }

    @Transactional
    public void deleteCrop(UUID id) {
        Crop crop = cropRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Crop not found with id: " + id));
        cropRepository.delete(crop);
        log.info("Deleted crop record: id={}", id);
    }
}
