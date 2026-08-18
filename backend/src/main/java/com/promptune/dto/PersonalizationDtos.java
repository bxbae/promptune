package com.promptune.dto;

import com.promptune.domain.ReceiverProfile;
import com.promptune.domain.UserPreference;

import java.util.List;

public class PersonalizationDtos {
    public record PersonalizationExport(UserPreference preferences, List<ReceiverProfile> receivers,
                                         boolean globalConsentGranted) {}
}
