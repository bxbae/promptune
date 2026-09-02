package com.promptune.service;

import org.springframework.stereotype.Component;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Pattern;

// 2026-09-02: ai-service의 output_preference.py::detect_output_preferences()와
// 동일한 패턴. backend가 습관 기록용으로 독립적으로 재사용(ai-service 호출 없이,
// 매 요청마다 왕복하지 않도록). 패턴을 고치게 되면 두 파일 다 같이 고쳐야 함 -
// 이 주석을 output_preference.py 쪽에도 남겨두는 걸 권장.
@Component
public class OutputPreferenceDetector {

    private static final Map<String, String[]> FORMAT_PATTERNS = new LinkedHashMap<>();
    static {
        FORMAT_PATTERNS.put("table", new String[]{"표로", "표 형태로", "테이블로", "표로 정리"});
        FORMAT_PATTERNS.put("markdown", new String[]{"마크다운으로", "마크다운 형식"});
        FORMAT_PATTERNS.put("checklist", new String[]{"체크리스트", "체크리스트 형식"});
        FORMAT_PATTERNS.put("json", new String[]{"json으로", "JSON으로", "json 형식"});
        FORMAT_PATTERNS.put("code_only", new String[]{"코드만"});
    }

    private static final Map<String, String[]> STRUCTURE_PATTERNS = new LinkedHashMap<>();
    static {
        STRUCTURE_PATTERNS.put("title_body_conclusion",
                new String[]{"제목/본문/결론", "제목-본문-결론", "서론 본론 결론", "서론-본론-결론"});
    }

    private static final Map<String, String[]> DETAIL_PATTERNS = new LinkedHashMap<>();
    static {
        DETAIL_PATTERNS.put("concise", new String[]{"간단하게", "간략하게", "짧게", "간단히"});
        DETAIL_PATTERNS.put("detailed", new String[]{"자세히", "상세하게", "구체적으로", "자세하게"});
    }

    /** length는 습관 카운트에서 제외 (4-1 참고). format/structure/detail_level만 반환. */
    public Map<String, String> detect(String text) {
        Map<String, String> prefs = new LinkedHashMap<>();
        prefs.put("format", findMatch(text, FORMAT_PATTERNS));
        prefs.put("structure", findMatch(text, STRUCTURE_PATTERNS));
        prefs.put("detail_level", findMatch(text, DETAIL_PATTERNS));
        return prefs;
    }

    private String findMatch(String text, Map<String, String[]> patterns) {
        for (Map.Entry<String, String[]> entry : patterns.entrySet()) {
            for (String p : entry.getValue()) {
                if (text.contains(p)) {
                    return entry.getKey();
                }
            }
        }
        return null;
    }
}
