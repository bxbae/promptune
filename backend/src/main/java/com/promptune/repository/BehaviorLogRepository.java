package com.promptune.repository;

import com.promptune.domain.BehaviorLogEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface BehaviorLogRepository extends JpaRepository<BehaviorLogEntity, Long> {
    List<BehaviorLogEntity> findByUserId(Long userId);
    void deleteByUserId(Long userId);
}
