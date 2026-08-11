package com.promptune.repository;

import com.promptune.domain.ConsentRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface ConsentRecordRepository extends JpaRepository<ConsentRecord, Long> {
    Optional<ConsentRecord> findTopByUserIdOrderByGrantedAtDesc(Long userId);
}