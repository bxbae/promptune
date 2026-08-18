package com.promptune.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;

// S3Client 빈 설정.
// 자격증명은 액세스 키를 코드/설정에 넣지 않고, DefaultCredentialsProvider로
// EC2 인스턴스에 붙은 IAM 역할(promptune-ec2-s3-role)에서 자동으로 가져온다.
// 로컬 개발 시에는 ~/.aws/credentials 등 DefaultCredentialsProvider가 찾는
// 다른 소스를 쓰면 된다.
@Configuration
public class S3Config {

    @Value("${app.aws.region:ap-northeast-2}")
    private String region;

    @Bean
    public S3Client s3Client() {
        return S3Client.builder()
                .region(Region.of(region))
                .credentialsProvider(DefaultCredentialsProvider.create())
                .build();
    }
}
