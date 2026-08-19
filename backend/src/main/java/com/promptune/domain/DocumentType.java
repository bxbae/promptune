package com.promptune.domain;

// 회의 확정값: GUIDE는 기존 GUIDE·MANUAL 통합
public enum DocumentType {
    POLICY, TEMPLATE, GUIDE, REPORT, OTHER;

    // 문자열이 유효한 값인지 확인. 대소문자 무시하고 매칭.
    public static boolean isValid(String value) {
        if (value == null) return false;
        for (DocumentType t : values()) {
            if (t.name().equalsIgnoreCase(value)) return true;
        }
        return false;
    }
}
