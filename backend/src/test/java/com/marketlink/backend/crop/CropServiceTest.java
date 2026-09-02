package com.marketlink.backend.crop;

import com.marketlink.backend.common.exception.DuplicateResourceException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.crop.dto.CreateCropRequest;
import com.marketlink.backend.crop.dto.CropResponse;
import com.marketlink.backend.crop.dto.UpdateCropRequest;
import com.marketlink.backend.crop.service.CropService;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
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
class CropServiceTest {

    @Mock
    private CropRepository cropRepository;

    @InjectMocks
    private CropService cropService;

    private Crop sampleCrop;
    private UUID cropId;

    @BeforeEach
    void setUp() {
        cropId = UUID.randomUUID();
        sampleCrop = Crop.builder()
                .id(cropId)
                .name("ONION")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();
    }

    @Test
    @DisplayName("Successfully create crop when name is unique")
    void testCreateCrop_Success() {
        CreateCropRequest request = CreateCropRequest.builder()
                .name("Onion")
                .category("Vegetable")
                .unit("kg")
                .build();

        when(cropRepository.existsByNameIgnoreCase("ONION")).thenReturn(false);
        when(cropRepository.save(any(Crop.class))).thenReturn(sampleCrop);

        CropResponse response = cropService.createCrop(request);

        assertThat(response).isNotNull();
        assertThat(response.getName()).isEqualTo("ONION");
        assertThat(response.getCategory()).isEqualTo("VEGETABLE");
        assertThat(response.getUnit()).isEqualTo("KG");
        assertThat(response.getActive()).isTrue();

        verify(cropRepository).save(any(Crop.class));
    }

    @Test
    @DisplayName("Throw DuplicateResourceException when creating crop with existing name")
    void testCreateCrop_DuplicateName() {
        CreateCropRequest request = CreateCropRequest.builder()
                .name("Onion")
                .category("Vegetable")
                .unit("kg")
                .build();

        when(cropRepository.existsByNameIgnoreCase("ONION")).thenReturn(true);

        assertThatThrownBy(() -> cropService.createCrop(request))
                .isInstanceOf(DuplicateResourceException.class)
                .hasMessageContaining("Crop with name 'ONION' already exists");

        verify(cropRepository, never()).save(any(Crop.class));
    }

    @Test
    @DisplayName("Get crop by ID returns crop when found")
    void testGetCropById_Found() {
        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));

        CropResponse response = cropService.getCropById(cropId);

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(cropId);
        assertThat(response.getName()).isEqualTo("ONION");
    }

    @Test
    @DisplayName("Get crop by ID throws ResourceNotFoundException when not found")
    void testGetCropById_NotFound() {
        UUID unknownId = UUID.randomUUID();
        when(cropRepository.findById(unknownId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> cropService.getCropById(unknownId))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("Crop not found with id: " + unknownId);
    }

    @Test
    @DisplayName("Get all crops filters by active and category")
    void testGetAllCrops_Filtered() {
        when(cropRepository.findByCategoryIgnoreCaseAndActiveTrueOrderByNameAsc("VEGETABLE"))
                .thenReturn(List.of(sampleCrop));

        List<CropResponse> results = cropService.getAllCrops(true, "VEGETABLE");

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getName()).isEqualTo("ONION");
    }

    @Test
    @DisplayName("Update crop successfully updates properties")
    void testUpdateCrop_Success() {
        UpdateCropRequest request = UpdateCropRequest.builder()
                .name("Red Onion")
                .category("Vegetable")
                .unit("Quintal")
                .active(true)
                .build();

        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(cropRepository.existsByNameIgnoreCaseAndIdNot("RED ONION", cropId)).thenReturn(false);
        when(cropRepository.save(any(Crop.class))).thenAnswer(inv -> inv.getArgument(0));

        CropResponse response = cropService.updateCrop(cropId, request);

        assertThat(response.getName()).isEqualTo("RED ONION");
        assertThat(response.getUnit()).isEqualTo("QUINTAL");
    }

    @Test
    @DisplayName("Update crop throws DuplicateResourceException if renamed to existing crop")
    void testUpdateCrop_DuplicateRename() {
        UpdateCropRequest request = UpdateCropRequest.builder()
                .name("Tomato")
                .build();

        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(cropRepository.existsByNameIgnoreCaseAndIdNot("TOMATO", cropId)).thenReturn(true);

        assertThatThrownBy(() -> cropService.updateCrop(cropId, request))
                .isInstanceOf(DuplicateResourceException.class)
                .hasMessageContaining("Another crop with name 'TOMATO' already exists");
    }
}
