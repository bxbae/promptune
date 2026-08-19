package com.promptune.service;

import com.promptune.domain.User;
import com.promptune.domain.UserPreference;
import com.promptune.repository.UserPreferenceRepository;
import com.promptune.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class PreferenceResolutionServiceTest {

    private final UserRepository userRepository = mock(UserRepository.class);
    private final UserPreferenceRepository preferenceRepository = mock(UserPreferenceRepository.class);
    private final PreferenceResolutionService service =
            new PreferenceResolutionService(userRepository, preferenceRepository);

    @Test
    void nullAuthentication_returnsConservativeDefaults() {
        PreferenceResolutionService.ResolvedPreference resolved = service.resolve(null);

        assertEquals(PreferenceResolutionService.DEFAULT_SPEED, resolved.speed());
        assertEquals(PreferenceResolutionService.DEFAULT_DETAIL, resolved.detail());
        assertEquals(PreferenceResolutionService.DEFAULT_PRESERVE, resolved.preserve());
        assertFalse(resolved.fromLoggedInUser());
    }

    @Test
    void anonymousAuthentication_returnsConservativeDefaults() {
        Authentication anonymous = new AnonymousAuthenticationToken(
                "key",
                "anonymousUser",
                List.of(new SimpleGrantedAuthority("ROLE_ANONYMOUS")));

        PreferenceResolutionService.ResolvedPreference resolved = service.resolve(anonymous);

        assertFalse(resolved.fromLoggedInUser());
        assertEquals(PreferenceResolutionService.DEFAULT_SPEED, resolved.speed());
        assertEquals(PreferenceResolutionService.DEFAULT_DETAIL, resolved.detail());
        assertEquals(PreferenceResolutionService.DEFAULT_PRESERVE, resolved.preserve());
    }

    @Test
    void loggedInUserWithoutSavedPreference_returnsConservativeDefaults() {
        Authentication auth =
                new UsernamePasswordAuthenticationToken("user@promptune.dev", null, List.of());

        User user = mock(User.class);
        when(user.getId()).thenReturn(1L);
        when(userRepository.findByEmail("user@promptune.dev")).thenReturn(Optional.of(user));
        when(preferenceRepository.findByUserId(1L)).thenReturn(Optional.empty());

        PreferenceResolutionService.ResolvedPreference resolved = service.resolve(auth);

        assertFalse(resolved.fromLoggedInUser());
        assertEquals(PreferenceResolutionService.DEFAULT_SPEED, resolved.speed());
        assertEquals(PreferenceResolutionService.DEFAULT_DETAIL, resolved.detail());
        assertEquals(PreferenceResolutionService.DEFAULT_PRESERVE, resolved.preserve());
    }

    @Test
    void loggedInUserWithSavedPreference_returnsStoredValues() {
        Authentication auth =
                new UsernamePasswordAuthenticationToken("user@promptune.dev", null, List.of());

        User user = mock(User.class);
        when(user.getId()).thenReturn(1L);

        UserPreference pref =
                new UserPreference(1L, "accurate", "detailed", "improve");

        when(userRepository.findByEmail("user@promptune.dev")).thenReturn(Optional.of(user));
        when(preferenceRepository.findByUserId(1L)).thenReturn(Optional.of(pref));

        PreferenceResolutionService.ResolvedPreference resolved = service.resolve(auth);

        assertTrue(resolved.fromLoggedInUser());
        assertEquals("accurate", resolved.speed());
        assertEquals("detailed", resolved.detail());
        assertEquals("improve", resolved.preserve());
    }

    @Test
    void legacyPreserveTypo_isNormalizedToImprove() {
        Authentication auth =
                new UsernamePasswordAuthenticationToken("user@promptune.dev", null, List.of());

        User user = mock(User.class);
        when(user.getId()).thenReturn(1L);

        UserPreference pref =
                new UserPreference(1L, "fast", "brief", "imporve");

        when(userRepository.findByEmail("user@promptune.dev")).thenReturn(Optional.of(user));
        when(preferenceRepository.findByUserId(1L)).thenReturn(Optional.of(pref));

        PreferenceResolutionService.ResolvedPreference resolved = service.resolve(auth);

        assertTrue(resolved.fromLoggedInUser());
        assertEquals("improve", resolved.preserve());
    }

    @Test
    void unknownEmail_returnsConservativeDefaults() {
        Authentication auth =
                new UsernamePasswordAuthenticationToken("ghost@promptune.dev", null, List.of());

        when(userRepository.findByEmail("ghost@promptune.dev"))
                .thenReturn(Optional.empty());

        PreferenceResolutionService.ResolvedPreference resolved = service.resolve(auth);

        assertFalse(resolved.fromLoggedInUser());
        assertEquals(PreferenceResolutionService.DEFAULT_SPEED, resolved.speed());
        assertEquals(PreferenceResolutionService.DEFAULT_DETAIL, resolved.detail());
        assertEquals(PreferenceResolutionService.DEFAULT_PRESERVE, resolved.preserve());
    }
}
