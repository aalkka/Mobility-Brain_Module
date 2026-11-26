# mobility 적용 설명서

외부뇌 볼트에 모듈을 넣고, 처음 설정으로 폰을 붙이는 순서다. **1 → 4 순서대로.**

## 미리 있어야 할 것

| 무엇 | 어디 | 비고 |
|---|---|---|
| 외부뇌 볼트 + Claude Code | PC (Windows) | [외부뇌](https://github.com/aalkka/Claude_Brain) 배포판 |
| Python 3 · git | PC | 외부뇌가 이미 쓴다 |
| Tailscale (로그인 · MagicDNS · HTTPS 인증서) | PC · 폰 · 태블릿 | 같은 계정(tailnet) |
| 옵시디언 앱 | 폰 · 태블릿 | 폰에서 볼트를 볼 때 |
| Android 폰 | — | 폰 앱(알림·공유·위젯)은 Android 만 |

## 1. 넣는다

외부뇌 볼트 루트에서:

```bash
git clone https://github.com/aalkka/Mobility-Brain_Module.git .claude/skills/mobility
```

git 이 없으면 ZIP 을 받아 `.claude/skills/mobility/` 에 푼다. 그 안에 `module.json` 이 바로 보여야 한다. 새 세션을 연다(새 스킬 폴더는 재시작 후 활성).

## 2. 처음 설정 — «모바일 연결 설정»

Claude 에게 «모바일 연결 설정» 이라고 하면 `/mobility:setup` 이 한 단계씩 묻고 채운다.

1. 개인 값 — 서버 문 번호 · 집 Wi-Fi 이름 · 민감 노트를 폰에 보일지 · 폰에서 적는 일정 파일 · 알림을 울릴 일정 파일 · 기본 울림 · 방해 금지. 재서 ✦ 추천과 함께 묻는다. 쓰는 곳 = `3_시스템/_index/server/config.json`(git 밖)과 설정 노트 둘(`2_지식/modules/mobility/`).
2. 바깥 설정 — «바깥 설정 점검»의 «[모바일 연결(mobility)]» 줄. Tailscale 설치·로그인·MagicDNS·HTTPS 는 사람이 한다. serve(`/` → 이 볼트 서버) · 예약 «외부뇌 서버» 는 승인 뒤 Claude 가 등록 대본을 돌린다.
3. 폰 출시물 — `release.py install` 이 이 저장소의 최신 출시 첨부를 받아 서버 자리에 둔다(인증 없음 · sha256 확인). 폰 보기(원본 보기 · 약 31MB)는 기본으로 받는다 — 안 쓰려면 설정 › 기능 단계 «폰 보기(원본 보기 플러그인) 받기»를 끈다.
4. 기기 붙이기 — PC 옵시디언 «모바일 연결» 화면 › «QR 보이기» → 폰 카메라로 찍기 → 쪽에서 «손발 앱 받기»(처음만 · 설치) → «손발 앱에 넣기» → 앱에서 «붙이기» 확인. 10분 · 4번(폰 앱·폰 옵시디언·탭 앱·탭 옵시디언).
   - 폰 옵시디언은 이어서 앱이 준비한다: «볼트 만들기» → 폴더 창 «이 폴더 사용»·«허용»(처음 자리 = `Documents`) → 앱이 `Documents/Brain` 에 볼트·brain-server 플러그인·주소·열쇠를 넣는다 → «옵시디언 열기» → 옵시디언 «Use my existing vault» › «On this device» › «Choose folder» › «Allow file access»(모든 파일 접근 켬) › `Documents/Brain` › «이 폴더 사용»·«허용» › «Trust author and enable plugins». 그 뒤 플러그인이 캘린더·폰 보기를 스스로 받는다. 나중에 하려면 앱 «연결» › «폰 옵시디언 준비».
   - 옵시디언이 앱 저장소(기본 «Create a vault»)에 만든 볼트는 다른 앱이 못 쓴다 — 플러그인을 손으로 넣을 때만 쪽의 «옵시디언 플러그인 받기»(zip → 볼트 `.obsidian/plugins/` 에 풀고 커뮤니티 플러그인 켜기) · «옵시디언에 넣기»를 쓴다.
5. 폰 준비 — 손발 앱 «준비»를 한 장씩(상시 VPN · 알림 허용 · 정확한 알람 · 배터리 예외 · 권한 회수 끔 · 설치 허용 등). 앱이 재서 PC 에 보고하고 바깥 설정 점검의 폰 줄이 따라 바뀐다.

## 3. 확인

```bash
py -3 .claude/skills/dist-sync/scripts/external.py check     # 바깥 설정 — PC·폰 줄
py -3 .claude/skills/mobility/scripts/pair.py status          # 붙은 기기
py -3 .claude/skills/mobility/scripts/release.py check        # 폰 출시물
```

(선택) «모듈 충돌 검사» 라고 하면 외부뇌 `module-forge:check` 가 경계 위반을 본다.

## 4. 끄기 · 빼기

- 끄기: 모듈 스위치를 끄면 데스크톱의 폰 관련 칸(수집 창 «알림» 칸 · 캘린더 종)이 사라진다. 서버는 예약 «외부뇌 서버»라 따로 돈다 — 멈추려면 예약을 끈다.
- 빼기: 등록 대본에 `-Remove`(예약·serve 지움) → `.claude/skills/mobility/` 폴더를 지운다. 개인 값·상태(`3_시스템/_index/server/`)는 남는다.

## 하지 않는 것

- 열쇠(token)·서명 키를 묻거나 보이지 않는다. 열쇠는 서버가 만들고 짝짓기가 넘긴다.
- 다른 볼트가 맡은 예약·serve 를 덮지 않는다.
- 폰 앱·폰 플러그인 소스는 이 저장소에 없다(출시물만 · Releases).
