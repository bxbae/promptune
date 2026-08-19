package com.promptune.service;

import com.promptune.domain.User;
import com.promptune.domain.UserPreference;
import com.promptune.repository.UserPreferenceRepository;
import com.promptune.repository.UserRepository;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;

/**
 * Phase 2-A: 로그인 사용자의 Preference를 Authentication(JWT) 기준으로 해석한다.
 *
 * 배경:
 * - UserPreferenceController는 Authentication(JWT subject = email)으로 사용자를 찾는다.
 * - 반면 PipelineController(/api/analyze, /api/execute)는 지금까지 요청 바디의
 *   Long userId를 써 왔는데, 이 두 경로는 SecurityConfig에서 permitAll이라 인증 없이도
 *   호출 가능하고, frontend(lib/api.ts)도 실제로는 userId를 1로 하드코딩해서 보내고
 *   있어 로그인한 실제 사용자와 무관할 수 있다.
 *
 * 따라서 Preference 조회의 identity source of truth는 요청 바디의 userId가 아니라
 * UserPreferenceController와 동일한 Authentication 기반으로 통일한다. 단, /api/analyze,
 * /api/execute는 비로그인 상태에서도 항상 동작해야 하므로(permitAll), 이 클래스는
 * UserPreferenceController와 달리 예외를 던지지 않고 아래 모든 경우에 보수적 기본값으로
 * 폴백한다:
 *   - Authentication이 없거나 인증되지 않음
 *   - 익명 사용자(anonymousUser)
 *   - 토큰은 유효하나 해당 이메일의 User가 없음
 *   - User는 있으나 아직 온보딩(Preference 저장)을 완료하지 않음
 */
@Service
public class PreferenceResolutionService {

    public static final String DEFAULT_SPEED = "fast";
    public static final String DEFAULT_DETAIL = "brief";
    public static final String DEFAULT_PRESERVE = "keep";

    private static final String ANONYMOUS_PRINCIPAL = "anonymousUser";

    // 온보딩 화면(frontend/src/app/onboarding/page.tsx)의 기존 오타.
    // V20__normalize_preference_values.sql이 기존 DB row를 정규화하지만,
    // 마이그레이션이 아직 적용되지 않은 환경(예: 로컬 DB)에서도 안전하도록
    // 코드 레벨에서도 방어적으로 보정한다.
    private static final String LEGACY_PRESERVE_TYPO = "imporve";
    private static final String PRESERVE_IMPROVE = "improve";

    private final UserRepository userRepository;
    private final UserPreferenceRepository preferenceRepository;

    public PreferenceResolutionService(
            UserRepository userRepository,
            UserPreferenceRepository preferenceRepository) {
        this.userRepository = userRepository;
        this.preferenceRepository = preferenceRepository;
    }

    /**
     * 해석된 Preference. fromLoggedInUser=false면 speed/detail/preserve는
     * 전부 보수적 기본값(DEFAULT_*)이라는 뜻이다.
     */
    public record ResolvedPreference(
            String speed,
            String detail,
            String preserve,
            boolean fromLoggedInUser) {
    }

    public ResolvedPreference resolve(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            return defaults();
        }

        String email = authentication.getName();
        if (email == null || email.isBlank() || ANONYMOUS_PRINCIPAL.equals(email)) {
            return defaults();
        }

        return userRepository.findByEmail(email)
                .map(User::getId)
                .flatMap(preferenceRepository::findByUserId)
                .map(this::normalize)
                .orElseGet(this::defaults);
    }

    private ResolvedPreference normalize(UserPreference pref) {
        String speed = pref.getSpeed() != null ? pref.getSpeed() : DEFAULT_SPEED;
        String detail = pref.getDetail() != null ? pref.getDetail() : DEFAULT_DETAIL;

        String preserveRaw = pref.getPreserve();
        String preserve;
        if (preserveRaw == null) {
            preserve = DEFAULT_PRESERVE;
        } else if (LEGACY_PRESERVE_TYPO.equals(preserveRaw)) {
            preserve = PRESERVE_IMPROVE;
        } else {
            preserve = preserveRaw;
        }

        return new ResolvedPreference(speed, detail, preserve, true);
    }

    private ResolvedPreference defaults() {
        return new ResolvedPreference(DEFAULT_SPEED, DEFAULT_DETAIL, DEFAULT_PRESERVE, false);
    }
}
