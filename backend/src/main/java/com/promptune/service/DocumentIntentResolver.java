package com.promptune.service;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * 현재 발화와 직전 대화 문맥을 함께 보고 문서 생성 실행 여부를 결정한다.
 *
 * 핵심 원칙
 * - 문서 생성 의도가 명확하면 추가 질문보다 실행을 우선한다.
 * - 일반 문서 생성 / 빈 양식 생성 / 사내 기존 양식 사용을 구분한다.
 * - "업무보고서", "ㅇㅇ", "파일로 만들어줘" 같은 후속 발화는 직전 턴을 이어받는다.
 */
@Service
public class DocumentIntentResolver {

    public record DocumentAction(
            String title,
            String content,
            String format,
            boolean useExistingTemplate) {
    }

    private static final Pattern CREATE_VERB = Pattern.compile(
            "(만들어(?:줘)?|생성해(?:줘)?|작성해(?:줘)?|써줘|제작해(?:줘)?)");

    private static final Pattern DOCUMENT_NOUN = Pattern.compile(
            "(업무\\s*보고서|주간\\s*보고서|월간\\s*보고서|보고서|회의록|계획서|제안서|시말서|경위서|사유서|소명서|공지문|안내문|문서|양식|템플릿)");

    private static final Pattern FILE_NOUN = Pattern.compile(
            "(파일|pdf|워드|word|docx|엑셀|excel|xlsx|마크다운|markdown|텍스트파일|txt|ppt|파워포인트|슬라이드|프레젠테이션)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern AFFIRMATIVE = Pattern.compile(
            "^(응|ㅇㅇ+|네|예|그래|좋아|맞아|그렇게\\s*해줘|해줘|그걸로\\s*해줘|이걸로\\s*해줘)[.!?~\\s]*$",
            Pattern.CASE_INSENSITIVE);

    /**
     * "지금까지 종합해서 보고서로 만들어줘"처럼
     * 현재 발화만으로는 본문이 없고 앞선 업무 결과를
     * 재료로 문서를 만들어야 하는 요청.
     */
    private static final Pattern SYNTHESIS_REFERENCE = Pattern.compile(
            "(지금까지|지금껏|앞에서|방금까지|"
                    + "이전\\s*(내용|대화|결과)|"
                    + "위\\s*(내용|결과)|"
                    + "종합해서|종합하여|종합해|"
                    + "전체\\s*내용|모아서)");

    public Optional<DocumentAction> resolve(
            String currentPrompt,
            List<Map<String, String>> history) {

        String current = safe(currentPrompt).trim();

        if (current.isBlank()) {
            return Optional.empty();
        }

        String previousUser = previous(history, "user");
        String previousAssistant = previous(history, "assistant");

        boolean hasCreateVerb = CREATE_VERB.matcher(current).find();
        boolean hasDocumentNoun = DOCUMENT_NOUN.matcher(current).find();
        boolean hasFileNoun = FILE_NOUN.matcher(current).find();

        boolean directDocumentRequest =
                hasCreateVerb && (hasDocumentNoun || hasFileNoun);

        boolean contextualFileRequest =
                hasCreateVerb
                        && hasFileNoun
                        && !hasDocumentNoun
                        && !previousAssistant.isBlank();

        boolean typeOnlyFollowup =
                hasDocumentNoun
                        && !hasCreateVerb
                        && previousTurnWasDocumentClarification(
                                previousUser,
                                previousAssistant);

        boolean affirmativeFollowup =
                AFFIRMATIVE.matcher(current).matches()
                        && previousTurnWasDocumentConfirmation(
                                previousUser,
                                previousAssistant);

        boolean synthesisDocumentRequest =
                directDocumentRequest
                        && SYNTHESIS_REFERENCE.matcher(current).find();

        if (!directDocumentRequest
                && !contextualFileRequest
                && !typeOnlyFollowup
                && !affirmativeFollowup) {
            return Optional.empty();
        }

        String intentContext;
        String source;

        if (synthesisDocumentRequest) {
            source = buildSynthesisSource(
                    history,
                    current);
            intentContext = source;
        } else if (contextualFileRequest) {
            intentContext = previousUser + "\n" + previousAssistant + "\n" + current;
            source = previousAssistant;
        } else if (typeOnlyFollowup) {
            intentContext = previousUser + "\n" + current;
            source = previousUser
                    + "\n\n사용자가 선택한 문서 유형: "
                    + current;
        } else if (affirmativeFollowup) {
            intentContext = previousUser + "\n" + previousAssistant;
            source = previousUser.isBlank()
                    ? previousAssistant
                    : previousUser;
        } else {
        intentContext = current;

        // 2026-09-08: 이전 대화(previousUser/previousAssistant)를 안 쓰고
        // current만 쓰던 문제 수정. 완전히 새로운 화제의 첫 메시지라면
        // previousUser/previousAssistant가 비어있을 테니 그 경우엔 기존과
        // 동일하게 current만 쓰이게 됨.
        StringBuilder combined = new StringBuilder();

        if (!previousAssistant.isBlank()) {
            combined.append("[이전 대화 - AI 응답]\n")
                    .append(previousAssistant)
                    .append("\n\n");
        }

        if (!previousUser.isBlank()) {
            combined.append("[이전 대화 - 사용자 발화]\n")
                    .append(previousUser)
                    .append("\n\n");
        }

        combined.append("[지금 요청]\n").append(current);

        source = combined.toString();
    }

        String title = detectTitle(current, intentContext);
        boolean templateRequest = containsTemplateRequest(intentContext);
        boolean useExistingTemplate = wantsExistingTemplate(intentContext);
        String format = detectFormat(current, intentContext, templateRequest);

        String content =
                synthesisDocumentRequest
                        ? enrichSynthesisReportRequest(
                                source,
                                title)
                        : enrichDocumentRequest(
                                source,
                                title,
                                templateRequest);

        return Optional.of(
                new DocumentAction(
                        title,
                        content,
                        format,
                        useExistingTemplate));
    }

    /**
     * 같은 채팅의 이전 대화를 종합 보고서용 Evidence Package로 만든다.
     *
     * - 사용자 요구/AI 분석 결과는 유지
     * - 중간의 공지문 생성 턴은 제외
     * - 문서 생성 완료 안내 같은 메타 응답은 제외
     * - 실제 내부문서 분석/웹검색 결과는 그대로 유지
     */
    private String buildSynthesisSource(
            List<Map<String, String>> history,
            String current) {

        StringBuilder out = new StringBuilder();

        out.append("[현재 요청]\n")
                .append(current)
                .append("\n\n")
                .append("[이전 대화 근거]\n");

        int usedChars = 0;
        int itemIndex = 1;
        final int maxChars = 16000;

        if (history != null) {
            for (Map<String, String> message : history) {
                if (usedChars >= maxChars) {
                    break;
                }

                String role = safe(
                        message.get("role")).trim();

                String value = safe(
                        message.get("content")).trim();

                if (value.isBlank()
                        || shouldExcludeFromSynthesis(
                                role,
                                value)) {
                    continue;
                }

                int remaining =
                        maxChars - usedChars;

                String piece =
                        value.length() > remaining
                                ? value.substring(
                                        0,
                                        remaining)
                                : value;

                String label =
                        "user".equals(role)
                                ? "이전 사용자 요청"
                                : "이전 AI 결과";

                out.append("[")
                        .append(label)
                        .append(" ")
                        .append(itemIndex)
                        .append("]\n")
                        .append(piece)
                        .append("\n\n");

                usedChars += piece.length();
                itemIndex++;
            }
        }

        out.append("[대화 활용 원칙]\n")
                .append("- 보고서 주제와 직접 관련 있는 이전 내용만 사용합니다.\n")
                .append("- 내부문서 분석 결과는 현행 문제점의 근거로 사용합니다.\n")
                .append("- Web Search 결과는 최신 외부 기술/솔루션 조사 근거로 사용합니다.\n")
                .append("- 중간에 생성한 공지문, 회의 일정 안내 등 별도 업무 결과물은 보고서 본문에서 제외합니다.\n");

        return out.toString().trim();
    }


    private boolean shouldExcludeFromSynthesis(
            String role,
            String content) {

        String value = safe(content).trim();

        if (value.isBlank()) {
            return true;
        }

        /*
         * STEP 4 공지문 생성은 같은 채팅에 있지만
         * STEP 6의 업무 자동화/솔루션 도입 보고서 근거가 아니다.
         */
        if ("user".equals(role)
                && containsAny(
                        value,
                        "공지문",
                        "공지 문")
                && CREATE_VERB.matcher(value).find()) {
            return true;
        }

        /*
         * 문서 생성 분기에서 저장되는
         * "요청하신 OO 문서를 생성합니다" 같은 메타 응답도
         * 보고서 Evidence가 아니다.
         */
        if ("assistant".equals(role)
                && value.length() < 250
                && containsAny(
                        value,
                        "문서를 생성합니다",
                        "문서를 생성합니다.",
                        "현재 첨부 문서를 바탕으로",
                        "요청하신")) {
            return true;
        }

        return false;
    }


    private String enrichSynthesisReportRequest(
            String source,
            String title) {

        String base = safe(source).trim();

        return base
                + "\n\n[종합 보고서 생성 규칙]\n"
                + "1. 위 이전 대화를 시간순 로그처럼 복사하지 말고 하나의 완성된 업무 보고서로 재구성하세요.\n"
                + "2. 업무 요청 배경과 목적은 초기 대화 맥락을 바탕으로 정리하세요.\n"
                + "3. 내부문서 분석 결과는 '현행 문제점'의 근거로 사용하세요.\n"
                + "4. Web Search에서 조사한 실제 결과는 '최신 AI Agent 솔루션 조사 결과'의 근거로 사용하세요.\n"
                + "5. 내부 문제점과 외부 솔루션을 서로 연결해 비교·검토하세요.\n"
                + "6. 대화 중 생성한 공지문, 회의 공지 작성 규칙, 체크리스트는 이번 보고서 본문에서 제외하세요.\n"
                + "7. 근거에 없는 제품 기능, 가격, 비용, 수치, 개발기간 단축률, 회사 정보는 임의로 만들지 마세요.\n"
                + "8. 확인되지 않은 내용은 '추가 확인 필요사항'으로 구분하세요.\n"
                + "9. 필요한 곳에는 표와 번호 목록을 사용하되 같은 내용을 반복하지 마세요.\n"
                + "10. 사용자의 질문이나 시스템 규칙을 본문에 그대로 노출하지 마세요.\n"
                + "11. 추가 질문 없이 현재 확보된 근거 범위에서 바로 완성된 보고서를 작성하세요.\n";
    }


    private boolean previousTurnWasDocumentClarification(
            String previousUser,
            String previousAssistant) {

        boolean previousCreateRequest =
                CREATE_VERB.matcher(previousUser).find()
                        && (DOCUMENT_NOUN.matcher(previousUser).find()
                        || FILE_NOUN.matcher(previousUser).find());

        boolean assistantAskedType = containsAny(
                previousAssistant,
                "어떤 종류",
                "무슨 보고서",
                "어떤 보고서",
                "종류를",
                "구체적으로 말씀",
                "업무보고서로");

        return previousCreateRequest && assistantAskedType;
    }

    private boolean previousTurnWasDocumentConfirmation(
            String previousUser,
            String previousAssistant) {

        boolean documentContext =
                DOCUMENT_NOUN.matcher(previousUser + " " + previousAssistant).find()
                        || FILE_NOUN.matcher(previousUser + " " + previousAssistant).find();

        boolean assistantAskedConfirmation = containsAny(
                previousAssistant,
                "만들어드릴까요",
                "만들까요",
                "생성해드릴까요",
                "작성해드릴까요",
                "파일로 만들어",
                "제공해 드릴까요",
                "제공해드릴까요");

        return documentContext && assistantAskedConfirmation;
    }

    private String detectTitle(
            String current,
            String context) {

        String text = (current + "\n" + context).replaceAll("\\s+", " ");

        if (containsAny(text, "회의록")) return "회의록";
        if (containsAny(text, "주간 업무보고", "주간 보고")) return "주간 업무보고서";
        if (containsAny(text, "월간 업무보고", "월간 보고")) return "월간 업무보고서";
        if (containsAny(text, "업무보고")) return "업무보고서";
        if (containsAny(text, "보고서 양식", "보고서 템플릿")) return "보고서 양식";

        if (containsAny(
                text,
                "ai agent",
                "ai 에이전트")
                && containsAny(
                        text,
                        "자동화",
                        "솔루션",
                        "문제점",
                        "도입",
                        "개선")) {
            return "AI Agent 업무 자동화 개선 및 솔루션 도입 검토 보고서";
        }

        if (containsAny(text, "보고서")) return "업무보고서";
        if (containsAny(text, "계획서")) return "계획서";
        if (containsAny(text, "제안서")) return "제안서";
        if (containsAny(text, "시말서")) return "시말서";
        if (containsAny(text, "경위서")) return "경위서";
        if (containsAny(text, "사유서")) return "사유서";
        if (containsAny(text, "소명서")) return "소명서";
        if (containsAny(text, "공지문")) return "공지문";
        if (containsAny(text, "안내문")) return "안내문";

        return "PrompTune 생성 문서";
    }

    private String detectFormat(
            String current,
            String context,
            boolean templateRequest) {

        String text = (current + "\n" + context).toLowerCase();

        if (containsAny(text, "워드", "word", "docx")) {
            return "docx";
        }

        if (containsAny(text, "ppt", "파워포인트", "슬라이드", "프레젠테이션")) {
            return "pptx";
        }

        if (containsAny(text, "엑셀", "excel", "xlsx", "스프레드시트")) {
            return "xlsx";
        }

        if (containsAny(text, "마크다운", "markdown", ".md")) {
            return "md";
        }

        if (containsAny(text, "텍스트파일", "txt", "메모장")) {
            return "txt";
        }

        if (containsAny(text, "pdf")) {
            return "pdf";
        }

        if (templateRequest) {
            return "docx";
        }

        // 문서 생성의 기본값은 사용자가 바로 확인 가능한 PDF.
        return "pdf";
    }

    private boolean containsTemplateRequest(String text) {
        return containsAny(text, "양식", "템플릿", "작성용");
    }

    private boolean wantsExistingTemplate(String text) {
        String normalized = safe(text).toLowerCase();

        return containsAny(
                normalized,
                "회사 양식",
                "사내 양식",
                "기존 양식",
                "내부 양식",
                "업로드한 양식",
                "회사 템플릿",
                "사내 템플릿",
                "기존 템플릿");
    }

    private String enrichDocumentRequest(
            String source,
            String title,
            boolean templateRequest) {

        String base = safe(source).trim();

        if (templateRequest) {
            return base + "\n\n"
                    + "[문서 생성 규칙]\n"
                    + "추가 질문하지 말고 바로 편집 가능한 빈 양식을 생성하세요.\n"
                    + "제공되지 않은 사실은 만들지 말고 빈칸 또는 작성용 placeholder로 두세요.\n"
                    + "제목, 기본정보, 핵심 섹션, 표/목록, 작성란을 포함해 실제 업무에서 바로 사용할 수 있게 구성하세요.";
        }

        StringBuilder rule = new StringBuilder();
        rule.append(base).append("\n\n")
                .append("[문서 생성 규칙]\n")
                .append("정보가 부족해도 추가 질문하지 말고 합리적인 기본 업무 문서를 먼저 생성하세요.\n")
                .append("제공되지 않은 사람, 날짜, 수치, 회사 정보는 만들지 말고 빈칸 또는 작성용 placeholder로 두세요.\n");

        if (title.contains("보고서")) {
            rule.append("보고서에는 작성일, 작성부서, 작성자, 주요 업무, 진행 현황, 성과, 이슈/리스크, 향후 계획을 목적에 맞게 포함하세요.\n");
        }

        return rule.toString().trim();
    }

    private String previous(
            List<Map<String, String>> history,
            String role) {

        if (history == null || history.isEmpty()) {
            return "";
        }

        for (int i = history.size() - 1; i >= 0; i--) {
            Map<String, String> message = history.get(i);

            if (role.equals(message.get("role"))) {
                String content = safe(message.get("content")).trim();

                if (!content.isBlank()) {
                    return content;
                }
            }
        }

        return "";
    }

    private boolean containsAny(String text, String... keywords) {
        String value = safe(text).toLowerCase();

        for (String keyword : keywords) {
            if (value.contains(keyword.toLowerCase())) {
                return true;
            }
        }

        return false;
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }
}
