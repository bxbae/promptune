package com.promptune.repository;

import com.promptune.domain.MicrosoftConnection;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MicrosoftConnectionRepository
        extends JpaRepository<MicrosoftConnection, Long> {
}
