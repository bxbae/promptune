package com.promptune.repository;

import com.promptune.domain.ResponseEdit;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface ResponseEditRepository extends JpaRepository<ResponseEdit, Long> {
    List<ResponseEdit> findByUserId(Long userId);
}
