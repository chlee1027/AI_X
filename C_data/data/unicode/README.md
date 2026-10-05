# Unicode 17.0.0 데이터 번들

> 2026-10-06 역할 C: 계획서의 공통 위치에 맞춰 사람 3 OFFSCREEN 묶음(`C_data/data/offscreen/data/unicode/`)에서 이 폴더(`C_data/data/unicode/`)로 옮겼다. 파일 내용은 그대로다. 아래 링크는 옮긴 위치 기준으로 고쳤고, 라이선스 원문은 이 폴더에도 두었다(`Unicode-LICENSE.txt`).

`confusables.txt`, `Scripts.txt`, `IdentifierType.txt` 세 파일을 unicode.org에서 내려받아 **같은 17.0.0 버전으로 고정**했습니다. 최신 버전을 자동 추적하는 링크를 데이터 다운로드에 사용하지 않습니다. 원문 헤더와 본문을 수정하지 않았습니다. 출처·다운로드 시각·바이트 크기·SHA-256은 [source_manifest.json](../offscreen/data/source_manifest.json)에 있습니다.

| 파일 | 공식 고정 URL | 역할 |
|---|---|---|
| confusables.txt | [17.0.0/security/confusables.txt](https://www.unicode.org/Public/17.0.0/security/confusables.txt) | UTS #39의 시각적으로 혼동되는 문자 매핑 |
| Scripts.txt | [17.0.0/ucd/Scripts.txt](https://www.unicode.org/Public/17.0.0/ucd/Scripts.txt) | UCD의 코드포인트별 Script 속성 |
| IdentifierType.txt | [17.0.0/security/IdentifierType.txt](https://www.unicode.org/Public/17.0.0/security/IdentifierType.txt) | UTS #39의 식별자 유형 집합 |

세 파일 헤더는 모두 2025 Unicode 고지를 포함합니다. 적용 라이선스는 [Unicode License v3](Unicode-LICENSE.txt), SPDX `Unicode-3.0`입니다. 공식 [라이선스 정책](https://www.unicode.org/policies/licensing_policy.html)과 [FAQ](https://www.unicode.org/faq/unicode_license.html)를 확인했습니다. 재배포 시 파일 헤더와 라이선스 전문을 함께 보존합니다. 자세한 내용은 [THIRD_PARTY.md](../offscreen/THIRD_PARTY.md)에 있습니다.

사용 시 구분해야 할 점:

- confusables는 방향이 있는 **문자열 매핑**입니다. 오른쪽 결과가 여러 코드포인트일 수 있으므로 단일 문자 치환표로 축소하면 안 됩니다. 광고 여부를 판정하는 사전도 아닙니다. skeleton 처리 순서·정규화는 [UTS #39](https://www.unicode.org/reports/tr39/tr39-31.html)에 맞춰 구현해야 합니다.
- Scripts는 단일 Script 속성입니다. 다중 스크립트 맥락이 필요하면 별도 `ScriptExtensions.txt`가 필요합니다. `Common`·`Inherited`를 곧바로 악성 혼입으로 판단하면 안 됩니다. 명시되지 않은 범위의 기본값은 파일의 `@missing`에 따라 `Unknown`입니다. [UAX #24](https://www.unicode.org/reports/tr24/)를 참고합니다.
- IdentifierType의 둘째 필드는 공백으로 구분한 **집합**입니다. 순서에 의미를 부여하거나 첫 값만 저장하지 않습니다. 명시되지 않은 코드포인트의 기본값은 `Not_Character`입니다. 이 파일을 IdentifierStatus 또는 광고 위험도 라벨과 혼동하지 않습니다.

무결성 검증은 세 파일의 버전 헤더, SHA-256, 알려진 코드포인트 6개를 검사했습니다. 데이터 행 수는 confusables 6,565, Scripts 2,287, IdentifierType 5,104입니다. **행 수는 매핑/구간 레코드 수이며 문자 수가 아닙니다.** 검사 결과는 [검증결과.json](../offscreen/검증결과.json)에 보관했습니다.
