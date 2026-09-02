package com.marketlink.backend.config;

import com.marketlink.backend.domain.image.entity.LotImage;
import com.marketlink.backend.domain.image.repository.LotImageRepository;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.data.domain.Example;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.repository.query.FluentQuery;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;
import java.util.stream.Collectors;

@Configuration
@Profile("test")
public class TestMongoConfig {

    @Bean
    @Primary
    public LotImageRepository testLotImageRepository() {
        return new InMemoryLotImageRepository();
    }

    public static class InMemoryLotImageRepository implements LotImageRepository {

        private final Map<UUID, LotImage> store = new ConcurrentHashMap<>();

        @Override
        public List<LotImage> findByLotIdOrderByCreatedAtDesc(UUID lotId) {
            return store.values().stream()
                    .filter(img -> lotId.equals(img.getLotId()))
                    .sorted((a, b) -> {
                        Instant t1 = a.getCreatedAt() != null ? a.getCreatedAt() : Instant.MIN;
                        Instant t2 = b.getCreatedAt() != null ? b.getCreatedAt() : Instant.MIN;
                        return t2.compareTo(t1);
                    })
                    .collect(Collectors.toList());
        }

        @Override
        public List<LotImage> findByLotId(UUID lotId) {
            return store.values().stream()
                    .filter(img -> lotId.equals(img.getLotId()))
                    .collect(Collectors.toList());
        }

        @Override
        public Optional<LotImage> findByIdAndLotId(UUID id, UUID lotId) {
            LotImage img = store.get(id);
            if (img != null && lotId.equals(img.getLotId())) {
                return Optional.of(img);
            }
            return Optional.empty();
        }

        @Override
        public void deleteByIdAndLotId(UUID id, UUID lotId) {
            LotImage img = store.get(id);
            if (img != null && lotId.equals(img.getLotId())) {
                store.remove(id);
            }
        }

        @Override
        public void deleteByLotId(UUID lotId) {
            store.values().removeIf(img -> lotId.equals(img.getLotId()));
        }

        @Override
        public <S extends LotImage> S save(S entity) {
            if (entity.getId() == null) {
                entity.setId(UUID.randomUUID());
            }
            if (entity.getCreatedAt() == null) {
                entity.setCreatedAt(Instant.now());
            }
            entity.setUpdatedAt(Instant.now());
            store.put(entity.getId(), entity);
            return entity;
        }

        @Override
        public <S extends LotImage> List<S> saveAll(Iterable<S> entities) {
            List<S> result = new ArrayList<>();
            for (S entity : entities) {
                result.add(save(entity));
            }
            return result;
        }

        @Override
        public <S extends LotImage> S insert(S entity) {
            return save(entity);
        }

        @Override
        public <S extends LotImage> List<S> insert(Iterable<S> entities) {
            return saveAll(entities);
        }

        @Override
        public Optional<LotImage> findById(UUID id) {
            return Optional.ofNullable(store.get(id));
        }

        @Override
        public boolean existsById(UUID id) {
            return store.containsKey(id);
        }

        @Override
        public List<LotImage> findAll() {
            return new ArrayList<>(store.values());
        }

        @Override
        public List<LotImage> findAllById(Iterable<UUID> ids) {
            List<LotImage> result = new ArrayList<>();
            for (UUID id : ids) {
                if (store.containsKey(id)) {
                    result.add(store.get(id));
                }
            }
            return result;
        }

        @Override
        public long count() {
            return store.size();
        }

        @Override
        public void deleteById(UUID id) {
            store.remove(id);
        }

        @Override
        public void delete(LotImage entity) {
            if (entity != null && entity.getId() != null) {
                store.remove(entity.getId());
            }
        }

        @Override
        public void deleteAllById(Iterable<? extends UUID> ids) {
            for (UUID id : ids) {
                store.remove(id);
            }
        }

        @Override
        public void deleteAll(Iterable<? extends LotImage> entities) {
            for (LotImage entity : entities) {
                delete(entity);
            }
        }

        @Override
        public void deleteAll() {
            store.clear();
        }

        @Override
        public List<LotImage> findAll(Sort sort) {
            return new ArrayList<>(store.values());
        }

        @Override
        public Page<LotImage> findAll(Pageable pageable) {
            List<LotImage> list = new ArrayList<>(store.values());
            return new PageImpl<>(list, pageable, list.size());
        }

        @Override
        public <S extends LotImage> Optional<S> findOne(Example<S> example) {
            return Optional.empty();
        }

        @Override
        public <S extends LotImage> List<S> findAll(Example<S> example) {
            return Collections.emptyList();
        }

        @Override
        public <S extends LotImage> List<S> findAll(Example<S> example, Sort sort) {
            return Collections.emptyList();
        }

        @Override
        public <S extends LotImage> Page<S> findAll(Example<S> example, Pageable pageable) {
            return Page.empty();
        }

        @Override
        public <S extends LotImage> long count(Example<S> example) {
            return 0;
        }

        @Override
        public <S extends LotImage> boolean exists(Example<S> example) {
            return false;
        }

        @Override
        public <S extends LotImage, R> R findBy(Example<S> example, Function<FluentQuery.FetchableFluentQuery<S>, R> queryFunction) {
            return null;
        }
    }
}
