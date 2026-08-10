package com.promptune.repository;

import com.promptune.domain.ModelUsageLog;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ModelUsageLogRepository extends JpaRepository<ModelUsageLog, Long> {
}