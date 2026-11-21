# mobility — 외부뇌 모바일 연결 모듈

[외부뇌(External Brain)](https://github.com/aalkka/Claude_Brain) 볼트에 붙이는 모듈. 폰·태블릿의 옵시디언과 폰 앱이 PC 볼트에 닿게 한다. 망은 Tailscale 이다 — PC 는 127.0.0.1 에만 문을 열고, 밖에서는 같은 tailnet 의 기기만 닿는다.

본체(배포판)는 이 모듈이 없어도 데스크톱에서 완결된다. 이 모듈은 본체 기능을 폰에서 돌게 하는 것만 맡는다.

| 하는 일 | 어디서 |
|---|---|
| 폰에서 볼트 노트 열기·찾기·적기 · 원본 보기(PDF·hwp·시트·docx) · 필기 | 폰 옵시디언(폰 플러그인 · 폰 보기) |
| 폰에서 캘린더 보기·고치기 · 일정 알림 | 폰 옵시디언 «캘린더» · 폰 앱 |
| 받은함으로 공유 · 큰 파일 올리기 | 폰 «공유» › 외부뇌 |
| 분류 알림(«~면 알려 줘»)을 폰으로 · 폰으로 물어보고 답 받기 | 폰 앱 알림 |
| 폰에서 PC Claude 켜기(원격 제어) | 폰 앱·폰 옵시디언 «Claude 켜기» |

설치·처음 설정 → [적용 설명서](INSTALL.md) · 사용 설명서 → [manual/설명서-mobility.md](manual/설명서-mobility.md)

## 자리

- 모듈: `.claude/skills/mobility/` — 서버(`scripts/server.py`) · 처음 설정 조리법(`setup.json` · 스킬 `/mobility:setup`) · 바깥 설정 목록(`outside.json`) · 짝짓기(`scripts/pair.py`) · 알림 엔진(`scripts/alarms.py`·`alert.py`) · 출시물 깔기(`scripts/release.py`) · 시험(`scripts/*_check.py`).
- 개인 값: `3_시스템/_index/server/config.json`(git 밖 · 예시 = `config.example.json`). 열쇠는 서버가 처음 켤 때 만든다 — 묻지도 보이지도 않는다.
- 폰 출시물(폰 앱 APK · 폰 플러그인 · 폰 캘린더 · 폰 보기)은 이 저장소의 출시(Releases) 첨부 `mobility-release.zip` 이다. `release.py install` 이 받아 서버 자리(`3_시스템/_index/server/app·plugin/`)에 둔다.

## 라이선스

MIT — [LICENSE](LICENSE).
