package com.promptune.controller;

import com.promptune.domain.Document;
import com.promptune.domain.User;
import com.promptune.dto.DocumentDtos.UpdateDocumentRequest;
import com.promptune.repository.DocumentRepository;
import com.promptune.repository.UserRepository;
import com.promptune.service.AiServiceClient;
import com.promptune.service.S3StorageService;
import com.promptune.service.DocumentTemplateResolver;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Locale;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final DocumentRepository documentRepository;
    private final UserRepository userRepository;
    private final S3StorageService s3StorageService;
    private final AiServiceClient aiServiceClient;
    private final DocumentTemplateResolver templateResolver;

    public DocumentController(DocumentRepository documentRepository,
                               UserRepository userRepository,
                               S3StorageService s3StorageService,
                               AiServiceClient aiServiceClient,
                               DocumentTemplateResolver templateResolver) {
        this.documentRepository = documentRepository;
        this.userRepository = userRepository;
        this.s3StorageService = s3StorageService;
        this.aiServiceClient = aiServiceClient;
        this.templateResolver = templateResolver;
    }

    // 실제 파일을 받아 S3(promptune-document 버킷)에 업로드하고, 메타데이터를 DB에 저장한다.
    // 내용(텍스트) 추출·청크 분할·임베딩 생성은 아직 이 단계의 범위가 아니라서
    // document_chunks는 생성하지 않는다 (추후 파싱 파이프라인 연동 시 추가 예정).
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Document upload(@RequestParam("file") MultipartFile file,
                            @RequestParam("title") String title,
                            @RequestParam(value = "description", required = false) String description,
                            @RequestParam(value = "documentType", required = false) String documentType,
                            Authentication authentication) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "파일이 비어있습니다.");
        }
        if (documentType != null && !documentType.isBlank() && !com.promptune.domain.DocumentType.isValid(documentType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "documentType은 POLICY/TEMPLATE/GUIDE/REPORT/OTHER 중 하나여야 합니다.");
        }

        User user = currentUser(authentication);
        String resolvedTitle = (title == null || title.isBlank())
                ? file.getOriginalFilename()
                : title;
        String fileType = extractExtension(file.getOriginalFilename());

        String s3Key = s3StorageService.uploadDocument(user.getId(), file);

        Document document = new Document(user.getId(), resolvedTitle, s3Key, fileType);
        document.setDescription(description);
        if (documentType != null && !documentType.isBlank()) {
            document.setDocumentType(documentType.toUpperCase());
        }
        document = documentRepository.save(document);

        // AI 인덱싱(청킹·임베딩) 요청 — 실패해도 업로드 자체는 성공으로 처리
        // (문서는 이미 저장·검색가능 상태, 인덱싱만 나중에 재시도하면 되므로 업로드를 막을 이유 없음)
        try {
            aiServiceClient.indexDocument(document.getId(), user.getId(), fileType, file);
        } catch (Exception e) {
            System.err.println("[문서 인덱싱 실패] documentId=" + document.getId() + " / " + e.getMessage());
        }

        return document;
    }

    public record GenerateDocumentRequest(
            String title,
            String content,
            String format,
            Long templateDocumentId) {
    }

    @PostMapping(
            value = "/generate",
            consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<byte[]> generateDocument(
            @RequestBody GenerateDocumentRequest req,
            Authentication authentication) {

        // 다운로드도 로그인 사용자 기능으로 유지
        User user = currentUser(authentication);

        if (req.title() == null || req.title().isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "title은 비어 있을 수 없습니다.");
        }

        if (req.content() == null || req.content().isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "content는 비어 있을 수 없습니다.");
        }

        if (req.format() == null || req.format().isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "format은 비어 있을 수 없습니다.");
        }

        String format = req.format()
                .trim()
                .toLowerCase(Locale.ROOT);

        Document template = null;

        if (req.templateDocumentId() != null) {
            template = documentRepository
                    .findById(req.templateDocumentId())
                    .orElseThrow(() -> new ResponseStatusException(
                            HttpStatus.NOT_FOUND,
                            "템플릿 문서를 찾을 수 없습니다."));

            if (!template.getOwnerUserId().equals(user.getId())) {
                throw new ResponseStatusException(
                        HttpStatus.FORBIDDEN,
                        "본인 템플릿 문서만 사용할 수 있습니다.");
            }

            if (!"TEMPLATE".equalsIgnoreCase(template.getDocumentType())) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "templateDocumentId는 TEMPLATE 문서여야 합니다.");
            }
        }

        if (!List.of("docx", "pdf", "xlsx", "txt", "md").contains(format)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "지원 형식은 docx, pdf, xlsx, txt, md입니다.");
        }

        if (template == null) {
            String templateIntent =
                    (req.title() + " " + req.content())
                            .toLowerCase(Locale.ROOT);

            boolean wantsExistingTemplate =
                    templateIntent.contains("회사 양식")
                    || templateIntent.contains("사내 양식")
                    || templateIntent.contains("기존 양식")
                    || templateIntent.contains("내부 양식")
                    || templateIntent.contains("업로드한 양식")
                    || templateIntent.contains("회사 템플릿")
                    || templateIntent.contains("사내 템플릿")
                    || templateIntent.contains("기존 템플릿");

            if (wantsExistingTemplate) {
                template = templateResolver.resolve(
                        user.getId(),
                        req.title(),
                        req.content(),
                        format);
            }
        }

        if (template == null) {
            return aiServiceClient.generateDocument(
                    req.title().trim(),
                    req.content(),
                    format);
        }

        byte[] templateBytes =
                s3StorageService.download(template.getS3Key());

        String templateFilename = template.getTitle();

        if (template.getFileType() != null
                && !template.getFileType().isBlank()
                && !templateFilename.toLowerCase(Locale.ROOT)
                        .endsWith("." + template.getFileType()
                                .toLowerCase(Locale.ROOT))) {
            templateFilename =
                    templateFilename + "." + template.getFileType();
        }

        return aiServiceClient.generateDocument(
                req.title().trim(),
                req.content(),
                format,
                templateBytes,
                templateFilename);
    }


    @GetMapping
    public List<Document> myDocuments(Authentication authentication) {
        User user = currentUser(authentication);
        return documentRepository.findByOwnerUserId(user.getId());
    }

    @PatchMapping("/{id}")
    public Document update(@PathVariable Long id, @RequestBody UpdateDocumentRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "문서를 찾을 수 없습니다."));

        if (!document.getOwnerUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 문서만 수정할 수 있습니다.");
        }

        // 제목·설명·문서유형은 Document 자체를 그냥 고침 (조각 재분할 대상 아님)
        if (req.title() != null) document.setTitle(req.title());
        if (req.description() != null) document.setDescription(req.description());
        if (req.documentType() != null) {
            if (!com.promptune.domain.DocumentType.isValid(req.documentType())) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                        "documentType은 POLICY/TEMPLATE/GUIDE/REPORT/OTHER 중 하나여야 합니다.");
            }
            document.setDocumentType(req.documentType().toUpperCase());
        }

        return documentRepository.save(document);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id, Authentication authentication) {
        User user = currentUser(authentication);
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "문서를 찾을 수 없습니다."));

        if (!document.getOwnerUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 문서만 삭제할 수 있습니다.");
        }

        documentRepository.deleteById(id);  // document_chunks는 ON DELETE CASCADE로 자동 같이 삭제됨
        s3StorageService.delete(document.getS3Key());  // S3 객체도 같이 정리
        return ResponseEntity.ok().build();
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }

    private String extractExtension(String filename) {
        if (filename == null) return null;
        int dot = filename.lastIndexOf('.');
        if (dot < 0 || dot == filename.length() - 1) return null;
        return filename.substring(dot + 1).toLowerCase(Locale.ROOT);
    }
}
