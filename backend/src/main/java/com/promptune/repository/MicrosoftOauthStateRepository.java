package com.promptune.repository;

import com.promptune.domain.MicrosoftOauthState;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MicrosoftOauthStateRepository
        extends JpaRepository<MicrosoftOauthState, String> {
}
