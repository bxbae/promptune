package com.promptune.repository;

import com.promptune.domain.ReceiverProfile;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface ReceiverProfileRepository extends JpaRepository<ReceiverProfile, Long> {
    Optional<ReceiverProfile> findByUserIdAndReceiverName(Long userId, String receiverName);
    List<ReceiverProfile> findByUserId(Long userId);
}