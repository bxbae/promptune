package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "style_preference_score")
public class StylePreferenceScore {

    @Id
    @Column(name = "user_id")
    private Long userId;

    @Column(name = "sample_count")
    private int sampleCount = 0;

    @Column(name = "avg_length_ratio")
    private double avgLengthRatio = 1.0;

    @Column(name = "avg_structure_delta")
    private double avgStructureDelta = 0.0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    protected StylePreferenceScore() {}

    public StylePreferenceScore(Long userId) {
        this.userId = userId;
    }

    /** 새 관측값 하나를 러닝 애버리지에 반영 (누적 평균 갱신 공식). */
    public void accumulate(double lengthRatio, int structureDelta) {
        avgLengthRatio = (avgLengthRatio * sampleCount + lengthRatio) / (sampleCount + 1);
        avgStructureDelta = (avgStructureDelta * sampleCount + structureDelta) / (sampleCount + 1);
        sampleCount++;
        updatedAt = LocalDateTime.now();
    }

    public Long getUserId() { return userId; }
    public int getSampleCount() { return sampleCount; }
    public double getAvgLengthRatio() { return avgLengthRatio; }
    public double getAvgStructureDelta() { return avgStructureDelta; }
}
