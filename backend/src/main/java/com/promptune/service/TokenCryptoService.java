package com.promptune.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

@Service
public class TokenCryptoService {

    private static final int IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH = 128;
    private static final String ALGORITHM = "AES/GCM/NoPadding";

    private final String tokenKeyBase64;
    private final SecureRandom secureRandom = new SecureRandom();

    public TokenCryptoService(@Value("${microsoft.token-key:}") String tokenKeyBase64) {
        this.tokenKeyBase64 = tokenKeyBase64;
    }

    public String encrypt(String plaintext) {
        byte[] key = requireKey();
        try {
            byte[] iv = new byte[IV_LENGTH];
            secureRandom.nextBytes(iv);
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_LENGTH, iv));
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            byte[] combined = new byte[iv.length + ciphertext.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(ciphertext, 0, combined, iv.length, ciphertext.length);
            return Base64.getEncoder().encodeToString(combined);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "토큰 암호화에 실패했습니다.");
        }
    }

    public String decrypt(String encrypted) {
        byte[] key = requireKey();
        try {
            byte[] combined = Base64.getDecoder().decode(encrypted);
            if (combined.length <= IV_LENGTH) {
                throw new IllegalArgumentException("invalid ciphertext");
            }
            byte[] iv = new byte[IV_LENGTH];
            System.arraycopy(combined, 0, iv, 0, IV_LENGTH);
            byte[] ciphertext = new byte[combined.length - IV_LENGTH];
            System.arraycopy(combined, IV_LENGTH, ciphertext, 0, ciphertext.length);
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_LENGTH, iv));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "토큰 복호화에 실패했습니다.");
        }
    }

    private byte[] requireKey() {
        if (tokenKeyBase64 == null || tokenKeyBase64.isBlank()) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Microsoft 연결 기능이 설정되지 않았습니다. MICROSOFT_TOKEN_KEY를 설정하세요.");
        }
        byte[] key;
        try {
            key = Base64.getDecoder().decode(tokenKeyBase64.trim());
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "MICROSOFT_TOKEN_KEY가 유효한 Base64가 아닙니다.");
        }
        if (key.length != 32) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "MICROSOFT_TOKEN_KEY는 Base64로 인코딩된 32바이트 AES 키여야 합니다.");
        }
        return key;
    }

    /** Microsoft 연결 기능 사용 전 AES 키 설정 여부를 검증한다. */
    public void validateKeyConfigured() {
        requireKey();
    }
}
