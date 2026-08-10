package com.promptune.repository;

import com.promptune.domain.BehaviorLogEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BehaviorLogRepository extends JpaRepository<BehaviorLogEntity, Long> {
}