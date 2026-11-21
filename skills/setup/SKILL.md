---
name: setup
description: 모바일 연결(mobility · 옛 이름 «폰 연결») 처음 설정 — 조리법대로 개인 값(서버 문 번호·집 Wi-Fi·민감 노트·일정 파일·알림 기본)을 재서 ✦ 추천과 함께 묻고 채운 뒤, 바깥 설정(Tailscale·serve·예약)·서버 등록까지 한 줄로 잇는다. "모바일 연결 설정"·"모바일 연결 설정 다시"·"폰 연결 설정"·"폰 앱 처음 설정"·모듈 건강 줄 «모바일 연결 설정 안 됨»·setup-interview 의 모듈 설정 차례에 발동. ⛔ 폰 화면·앱 고장 고치기는 아님 · 열쇠(비밀)는 다루지 않음.
---
# /mobility:setup — 모바일 연결 처음 설정

조리법 원본 = 모듈 `setup.json`(물음 · 기본값 · 재는 법 · 쓰는 곳 · 묻기). 재고 쓰는 것은 대본이 하고, Claude 는 묻고 고르게만 한다. 꼴은 `dist-sync:outside` 와 같다 — 한 번에 하나씩.

## 1. 잰다

```bash
py -3 .claude/skills/mobility/scripts/setup.py plan          # 다시(재보정)면 --again
```

`?` 줄만 묻는다(`·` 줄은 재서 정했거나 이미 있음). 줄마다 ✦ 추천이 대본이 잰 값이다.

## 2. 묻는다 — 한 번에 하나

- 물음 글을 그대로 쓰고, ✦ 추천을 첫 답으로 둔다. 사람이 «그대로» 하면 추천을 쓴다.
- 일정 파일(알림 파일)은 목록을 보이고 **뺄 것만** 고르게 한다(다 울리는 것이 기본).
- 집 Wi-Fi 는 잰 이름을 보이고 «맞나 · 더 있나»만 묻는다. 유선이면 빈 목록.
- 이미 있는 값은 묻지 않는다(«다시»일 때만 · 바뀐 값은 4의 diff 로).
- 답을 임시 파일 하나에 모은다(`{id: 값}` JSON · 묻지 않은 id 는 빼면 추천이 들어간다). 작업 자리 = 이 세션의 scratchpad.

## 3. 쓴다

```bash
py -3 .claude/skills/mobility/scripts/setup.py apply --answers <답 파일>
```

- 빈 config 칸만 쓴다(`3_시스템/_index/server/config.json` · git 밖). 설정 노트 둘이 어디에도 없으면 모듈 틀로 모듈 홈(`2_지식/modules/mobility/`)에 만든다. 있는 노트는 고치지 않는다 — 바꿀 값은 노트에서 고친다.
- 꼴이 틀리면 아무것도 안 쓰고 종료 2 — 틀린 칸을 다시 묻는다.

## 4. 다시(재보정)

`plan --again` → 묻기 → `apply --answers <파일> --again --dry` 로 바뀔 칸 diff 를 보이고 **확인을 받은 뒤** `--again` 으로 쓴다. 문 번호를 바꿨으면 서버를 다시 켜야 하고(예약 다시 돌림) serve 도 새 문으로 잇는다(5).

## 5. 이어서 — 바깥 설정 · 서버 등록

- `dist-sync:outside` 절차 — `py -3 .claude/skills/dist-sync/scripts/external.py check` 의 «[모바일 연결(mobility)]» 줄. Tailscale 설치·로그인·MagicDNS·HTTPS 는 사람 단계 · serve·예약은 «하기»(승인 뒤 Claude 가 돌림 · 다른 볼트가 맡았으면 대본이 멈춘다).
- 폰 출시물 깔기(새 볼트 · 짝짓기 전에): `py -3 .claude/skills/mobility/scripts/release.py check` 가 1 이면 `release.py install`(바깥 설정 «폰 출시물» 하기와 같음) — 모듈 `release/` 또는 모듈 저장소 최신 출시 첨부를 받아 폰 앱·폰 플러그인·폰 캘린더·폰 보기를 서버 출시 자리에 둔다(sha256 확인 · 깐 판이 같거나 새로우면 건너뜀). 없으면 짝 쪽에 «받기» 단추가 안 나온다.
- 폰 짝짓기: PC 옵시디언 «모바일 연결» 화면 › «QR 보이기» → 폰 카메라로 찍기 → 쪽에서 앱·옵시디언을 받고 «넣기» → 기기에서 «붙이기» 확인. 옵시디언을 안 켰으면 `py -3 .claude/skills/mobility/scripts/pair.py new --open`(사람 앞 브라우저 · 승인 뒤). 붙었는지 = `pair.py status`.
- 폰 «준비»: 손발 앱 «준비» 한 장씩(앱이 재서 PC 에 보고) → 바깥 설정 점검의 폰 줄이 따라 바뀐다(`ready.py show`).
- 끝에 다시 재서 한 줄: `setup.py status` + 바깥 설정 남은 것.

## 하지 않는 것

- 열쇠(token)·서명 키를 묻거나 보이지 않는다. 등록 대본도 `-ShowKey` 없이는 열쇠를 안 보인다.
- 다른 볼트가 맡은 예약·serve 를 덮지 않는다.
- 묻지 않고 config 값을 바꾸지 않는다(«다시»는 diff → 확인 → 씀).
