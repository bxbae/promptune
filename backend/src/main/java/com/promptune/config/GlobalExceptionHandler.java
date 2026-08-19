package com.promptune.config;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

// 코드 전체에서 throw new ResponseStatusException(HttpStatus.XXX, "메시지")로 던진 에러를
// 그대로 JSON 응답에 실어 보내기 위한 전역 처리기.
// 이게 없으면 Spring Boot 기본 에러 핸들러가 reason(메시지)을 버리고
// {"status":400,"error":"Bad Request"}처럼 원인을 알 수 없는 응답만 돌려줌.
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, Object>> handleResponseStatusException(ResponseStatusException ex) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("status", ex.getStatusCode().value());
        body.put("error", ex.getReason());   // 우리가 넣은 실제 메시지

        return ResponseEntity.status(ex.getStatusCode()).body(body);
    }
}
