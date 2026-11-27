"""외부뇌 서버 모듈 v0 — 폰·탭이 PC 볼트에 닿는 문(큰 그림 5단계). 제공·검색·폰 기록 받기 + 폰 단추로 Remote Control 켜기(ADR-037 · 고정 명령만)만 한다(LLM 0).

127.0.0.1 에만 연다 — 밖에서는 Tailscale(`tailscale serve`)로만 들어온다(포트를 열지 않는다). 모든 요청은 열쇠(토큰)를 본다.
폰에 남는 것은 캐시와 보낼 함뿐이고 원본은 PC 에만 있다. 수정 충돌은 PC 우선: 폰이 본 판(base)과 지금 판이 다르면 409 — 폰 수정은 버리고 알린다.
민감 노트(sensitive: true)는 폰에도 다른 노트처럼 나온다(config phone_sensitive «show» 기본 · 사용자 11-16 C선택 · «hide» = 찾기·목록·읽기 어디에도 안 나옴). 민감 표시는 git 밖에 두는 표시라 서버는 떼지 않는다(폰 고치기도 못 뗌). 쓰기는 2_지식·0_작업의 md 와 받은함 메모·폰이 만든 받은함 노트·내 일정 · 폰 보기에서 사람이 보호를 풀고 고친 원본(PUT /v1/file · 1_수집 포함 · 옛 판은 휴지통)뿐이다.

  py -3 .claude/skills/mobility/scripts/server.py              # 실행(예약 작업은 pyw)
  py -3 .claude/skills/mobility/scripts/server.py token        # 폰 설정에 넣을 열쇠
  GET  /open?file=<볼트 경로>[&to=pc|phone]   # 열쇠 없음 · Claude 앱 대화의 볼트 링크(https) → 누른 기기 옵시디언으로 넘기는 쪽(3_시스템/vaultlink.py 가 만듦 · 11-20)
  GET  /v1/ping                        # 살아 있나 · 전원 · 집/밖 · Remote Control(읽기만) · 폰 알림 앱 마지막 당김(app)
  GET  /v1/search?q=&k=&mode=           # 찾기(hybrid | lexical)
  GET  /v1/list?dir=                    # 폴더 목록(md 는 속성 title · 뿌리 목록엔 desk = 데스크톱 «파일» 탭 규칙 값 — 폰 «파일» 서랍이 데스크톱과 같게 그린다)
  GET  /v1/home                         # 폰 홈 — 받은함(제안) · 작업 · 주제 · 수집(brain.py home 과 같은 부품 · 무거운 칸은 안 잰다 · 1분 캐시)
  GET  /v1/topic?name=|path=            # 폰 «주제» 패널 — 주제 카드의 마감·할 일·최근(지난 대화·장부는 PC에서만 · 30초 캐시)
  GET  /v1/find?sha256=                # 원본 해시 → 지금 경로(필기 바탕 PDF 가 옮겨졌을 때 · 1_수집/_색인 머리의 sha256 · 없으면 404)
  GET  /v1/resolve?name=                # 노트·원본 이름 → 경로(폰에서 [[링크]]를 누를 때 · 못 찾으면 404 = 볼트에도 없음(이름을 로그에) · 403 = 있는데 폰에 안 줌)
  GET  /v1/file?path=                   # 파일(ETag · If-None-Match → 304 · Range 한 구간 → 206 · 메모리에 다 올리지 않고 흘려 보낸다)
  GET  /v1/schedule?days=               # 오늘부터 N일 일정 줄
  GET  /v1/views                        # 데스크톱 모듈 화면·파일 형식 화면 목록(views.json + 켜진 모듈 module.json · brain-base moduleViews 와 같은 규칙)
  GET  /v1/view?module=&id=             # 그 화면 = {html, data}(선언된 자료 명령을 PC 에서 돌린 마지막 JSON 줄 · 폰은 보기 전용으로 그린다 · 20초 캐시)
  GET  /v1/format?path=                 # 파일 형식 화면(.moa 등) = {html, data} · {file} = 그 파일(폰 범위 안 · 민감 아님)
  POST /v1/format/set {path, field, id, value} | {path, cols}   # 형식 화면 쓰기(11-17) — 내 칸·칸 너비를 그 파일에(brain-base formatview setMine·setCols 와 같은 규칙 · 2_지식·0_작업)
  POST /v1/view/act {module, id, act, args}   # 모듈 화면 행위(11-17) — 그 모듈 행위만 brain.py run --by phone(--yes 없음 = 위험 행위는 멈춤) → {ok, err}
  GET  /v1/alarms                       # 폰이 울릴 목록(알림-설정.md 를 요청 때마다 읽음 · ETag → 304)
  GET  /v1/plugin/<id>                  # 폰 플러그인이 올라온 판(version.json 그대로 · 해시는 올릴 때 적은 값 — 깨진 파일을 폰이 잡는다)
  GET  /v1/plugin/<id>/core.js|styles.css   # 그 판의 파일
  GET  /v1/plugin/brain-server/brain-server.zip   # 폰 옵시디언 처음 설치 묶음(손발 앱 «볼트 만들기» · /pair/plugin 과 같은 파일 · 열쇠로)
  GET  /v1/app/brain-phone              # 폰 앱 자기 갱신: 올라온 판(version·name·sha256·size — 올릴 때 적은 값 그대로 · 폰은 내려받은 파일의 해시를 이 값과 맞춘 뒤에만 깐다)
  GET  /v1/app/brain-phone/brain-phone.apk   # 그 판의 APK(조각 받기 됨) — 개인용 APK 라 서버 열쇠가 들어 있다: 자리는 _index/server/app/ 하나뿐
  POST /v1/memo     {text, at, name}    # 받은함에 메모(at = 폰에서 적은 때 · name = 폰 새 노트 이름 · 덮어쓰지 않는다 · 같은 글을 또 보내면 한 벌)
  POST /v1/note     {path, base, text}  # 있는 노트 고치기(base = 폰이 본 ETag · 다르면 409)
  PUT  /v1/file?path=  (본문 = 파일 바이트 · If-Match = 폰이 본 ETag)   # 폰 보기가 고친 원본(docx·xlsx·hwp·글자 등 · 있는 파일만) — 다르면 409 · 옛 판은 휴지통(fileops) → {etag, batch}
  POST /v1/new      {path, text}        # 새 노트(이미 있으면 409)
  POST /v1/upload?name=&sha256=&size=&offset=  (본문 = 파일 바이트)   # 폰·탭 안드로이드 공유로 받은 파일 → 받은함 새 파일(종류 안 가림 · 같은 이름이면 «이름 (2)» · 덮지 않음 · 받은 바이트 그대로 · 장부) → {path, sha256}
                                        #   흘려 받음(메모리 고정 · 크기 상한 없음 · PC 에 2GB 는 남김 → 507) · 끊기면 받은 앞부분을 남기고 offset 부터 이어 받는다 · 다 안 왔으면 {have}
  POST /v1/pdf?name=<이름>.pdf&to=0_작업/<영역>/<주제>/…   # 본문 = 폰이 그린 HTML → PC 헤드리스 브라우저 인쇄(pdfprint) → 그 자리(덮음) → {path} · 폰 «PDF 로 볼트에 저장»·«PDF 로 공유»
  POST /v1/upload?…&to=0_작업/<영역>/<주제>/…/  # 폰 «PDF 로 볼트에 저장»·«PDF 로 내보내기»(옛 0_작업/필기/ 도) — 그 폴더의 같은 이름은 옛 판을 휴지통 거쳐 덮음(데스크톱과 같게) · to=2_지식/필기/_첨부/… = 필기에 넣는 사진·PDF(덮지 않음)
  GET  /v1/upload?sha256=&size=&name=   # 이어 보낼 자리 {have} · 다 받아 둔 것이면 {path, same} · 받을 자리가 없으면 507
  POST /v1/notechat {note?, chip?, text?, resume?, kind?, view?} → {job} · {note, chips:true} → {kind, why, chips}   # 탭 곁창(볼트 클로드 · 노트 특화 · notechat_route.py)
  GET  /v1/notechat?job=&from=N  → {events, next, done} · POST /v1/notechat/stop {job} · GET /v1/notechat/past[?id=]
  POST /v1/tabwork/ask {session, why} · GET /v1/tabwork?session= · POST /v1/tabwork/end {session}   # 탭 곁창 작업 모드 = 폰 명령 승인 길(tabwork.py · 켜는 근거 = 적용기 장부)
  POST /v1/ink      {path, lines}       # 필기 노트(.note) 덧붙이기 — 줄 이름(머리·쪽·획·기록)이 없는 줄만 끝에 · 없으면 머리 줄부터 새로 → {etag, lines, took}
  GET  /v1/marks?path=&dev=             # 책갈피(11-18) — 그 문서의 손 책갈피(모든 기기 합 − 지운 표) + 기기마다 마지막 본 곳 · 장부 옮김을 따라감 · 민감(숨김 설정)·폰 범위 밖은 403
  POST /v1/marks    {dev, op: add|del|last, path, id?, name?, pos?}   # 그 기기 파일(_index/work/책갈피/<dev>.json)에만 씀 · PC(pc.json)는 brain-base 몫이라 안 받음
  POST /v1/schedule {date, time, end, text}   # 내 일정에 한 줄
  POST /v1/schedule/check {file, line, done}  # 일정 줄 체크
  POST /v1/schedule/merge {path, base, text}  # 폰 캘린더 고침 — 폰이 본 글(base)에서 바뀐 줄만 PC 판에 얹는다 · 같은 줄을 PC 가 먼저 바꿨으면 PC 판(데스크톱 우선)
  POST /v1/alarms/fired {items}         # 폰이 보고한 늦음(_index/alarms 장부에만)
  POST /v1/alarms/act {items:[{id, act, key, date, title, at, value?}]}   # 폰 알림 단추 — 완료(done) = 그 열린 일정 줄을 [x] · 넘김(skip) = 그 회차만 안 울림(alarms.skip) · 둘 다 _index/alarms/acts.jsonl 에
                                        #   두 기기(앱 판 25~ · ring·ring_at·again·snooze): 그 울림을 먼저 판정한 기기가 이긴다 — 뒤에 온 다른 기기 것은 하지 않고 got = already
  POST /v1/rings    {items:[{id, at}], wait}   # 카드의 울림 가운데 판정된 것(없으면 wait 초까지 기다림 · 다른 기기가 판정하면 바로) — _index/alarms/rings.json
  POST /v1/push     {since, wait, holder, …상태}   # 즉시 알림(11-18 시험판) — since 뒤의 사건을 바로 · 없으면 wait 초(정책 push.wait 상한)까지 붙잡음 →
                                        #   {seq, events:[{id, seq, kind: alert(item 내용째)|list(신호)|ping(승인)|probe(시험)}], hold, holder, wait, why}
                                        #   붙잡을지는 PC 가 정함(설정 config.json «push» · GET /v1/alarms 의 push 칸도 같은 값) · since 없음(0) = 지금 seq 만
  POST /v1/push/ack {kind: ack|beat|cut, id, …상태}   # 폰이 사건을 받자마자(왕복 = PC 시계) · 박마다 배터리 · 붙잡던 물음이 끊긴 길이 → _index/alarms/push.jsonl
  POST /v1/push/emit {kind: alert|probe|list, events}   # PC 안에서만(알림 도구 alert.py · 시험) — 버스에 싣는다 · tailnet 에서 오면 403
  GET  /v1/push/state                   # PC 안에서만 — seq · 붙잡힌 물음 · 기기마다 마지막 물음 · 정책
  (머리 X-Brain-Device = 보낸 기기 이름 · 앱 판 25~ · 없으면 «기기 미상» — 당김·보고·진단·단추 기록이 기기마다)
  POST /v1/alarms/power {on}            # 알림-설정 «켬»(모든 기기 전부 끔·켬) — 폰 종은 0.7.26 부터 이 길을 안 쓴다(전부 끄기는 PC 에서 · 옛 플러그인만)
  GET  /v1/settings                     # 앱 안 볼트 설정(11-27) — 잘 시간·당김·미리 알림·울릴 일정·바로(알림-설정 블록) · 집 Wi-Fi·민감 노트·일정 쓸 곳(config)
  POST /v1/settings {set, value}        # 칸 하나 바꿈(set = quiet·pull·before·file·now·wifi·sensitive(hide 만)·write) → GET 과 같은 값 · 노트·config 는 fileops 바꾸기(장부·되돌리기)
  POST /v1/alarms/mute {mute}           # «이 기기만 끄기»(11-17) — 폰·탭 종과 손발 앱 스위치가 같은 값 · 기기 = 앱 머리 또는 같은 tailnet 주소의 앱 · GET /v1/alarms 에 mute · ping app 에 here·mute·me
  POST /v1/work/finish {path}          # 홈 «작업» 체크 = 끝냄(데스크톱과 같은 work.finish · 장부 by=phone) → {batch}
  POST /v1/inbox/do {name}             # 홈 «받은함» 줄 단추 = 제안대로(inbox.execute 한 항목)
  POST /v1/undo     {batch}            # 폰이 받은 묶음만 되돌림(work/finish·fileop 이 준 것)
  POST /v1/fileop   {op, src, dst, base}   # 폰 탐색기 이름 바꾸기·옮기기(op=mv · dst = 새 경로 또는 폴더) · 휴지통으로(op=rm) — fileops(장부·휴지통·링크 고침) · base = 폰이 본 ETag(다르면 409 · 파일만) · 파일 이름 바꾸기는 원래 확장자를 언제나 지킴(빠지거나 바뀌면 붙임 · 11-23)
  POST /v1/fileop   {op: "mkdir", dst}   # 폰 «새 폴더»(11-23) — 폰 범위 안(/v1/folders 와 같은 거름)에만 · 이름 검사(빈 이름·/·\·..·윈도 금지 글자·끝 점/공백) · 이미 있으면 409 · fileops mkdir(장부 by=phone) → {batch, dst}(/v1/undo = 빈 폴더면 치움)
  POST /v1/fileops  {op, items:[{src, base}], dst}   # 여러 개 고르기(11-16) — 한 묶음(되돌리기 한 번)으로 옮기기(op=mv · dst = 폴더)·휴지통으로(op=rm) · 50개까지
                                        #   줄마다 {src, ok, dst | followed(앞 줄이 옮긴 폴더 안·짝 메모라 함께 감) | error} · 안 된 줄이 있어도 나머지는 한다
  GET  /v1/manual                       # 사용자설명서 ```brain-manual``` — 켜진 모듈 설명서 장(데스크톱 brain-base manualChapters 와 같음)
  GET  /v1/folders                      # 옮길 자리 고르기 — 폰 범위 안 폴더 경로(숨김·민감 자리 뺌 · 폰이 나무로 그린다)
  GET  /v1/trash?limit=                 # 휴지통(fileops 가 넣은 것 · 아직 있음 · 원래 자리가 폰 범위) — 최근부터 · age = 지난 날 · n = 모두 몇 개 · limit 기본 50 · 500까지
  POST /v1/trash/restore {id} | {ids}   # 되살리기 — 여럿이면 한 묶음(되돌리기 한 번) · 줄마다 결과
  POST /v1/diag     {lines}             # 폰 진단 줄 → 서버 로그(노트 이름·글 없음 · 한 번·하루 상한)
  POST /v1/lock     {path, on, id, label}   # 폰·탭이 노트에 입력 중(심장박동 · 마지막 입력 뒤 lock_ttl 초 = 풀림 · on=false = 풂) — 다른 기기가 먼저면 {ok:false, held} · locks.json(훅·데스크톱)
  GET  /v1/locks                        # 지금 걸린 잠금 [{path, label, left}] — Claude Edit·Write 훅이 locks.json 에 걸린 뒤 다시 묻는다(서버가 없으면 막지 않음)
  POST /v1/watch    {items:[{path, etag}], id, sig, wait}   # 열어 둔 노트의 PC 판·잠금 지켜보기 — 바뀌면 바로 · 아니면 wait 초(25 상한)까지 붙잡음 → {items, locks, sig} · 없어진 노트 = {gone, moved?}(옮긴 자리)
  POST /v1/changes  {since, wait}      # 볼트 바뀜 버스(11-23 · vaultwatch.py) — 누가 바꿨든 폰 범위 안의 바뀜을 since 뒤로 · 없으면 wait 초(25 상한) 붙잡음 → {seq, dirs, moves:[{src,dst,dir}], reset?}
                                       #   since 0 = 지금 seq 만 · reset = 폰이 받아 둔 목록을 다 버리고 다시 받는다 · GET /v1/file 404 의 moved = 옮긴 자리(옛 경로로 열 때)
  GET  /v1/approve                      # 폰 승인(11-17): 대기 수·가장 오래·run 별·동결·키 수(묶음 json 을 서버가 셈 · ping 의 approve 칸도 같은 셈)
                                        #   순서(11-28): run 별 items[{kind,nn,order,blocked_by}] · cmds[].order·blocked_by = 적용기 status(있을 때만)
  GET  /v1/approve/bundle?run=          # 폰에 보낼 볼트 묶음 + 도전값 = 게이트 코어 적용기 approve.py challenge(부를 때마다 새 도전값)
                                        #   &form=bin(앱 판 36~) = 머리 JSON 한 줄 + diff 바이트(gzip) · &have=<폰 화면 all sha> 같으면 머리만(«same»)
  GET  /v1/approve/recent               # 최근 붙임·등록 기록(approve.py recent)
  GET  /v1/approve/command?run=&id=     # 명령 승인(11-20 · 사용자 권한 한 줄) 요청 바이트 + 이름 나온 파일 + 도전값 = approve.py challenge-cmd
  GET  /v1/approve/result?run=&id=      # 명령 승인의 상태·결과(approve.py result) · 폰이 승인 뒤 끝날 때까지 본다
  POST /v1/approve/sign {message, sig}  # 폰 지문 서명 → approve.py apply-signed(서버는 나르기만 · 재고 붙이는 것은 적용기)
  POST /v1/approve/reject {run, all | id, why} · /v1/approve/freeze {why} · /v1/approve/enroll {spki, label}   # 거절 기록 · «내가 안 시킴» 동결 · 키 등록 «요청»(등록·풀기는 PC 콘솔만)
  POST /v1/rc                           # Remote Control 켜기(고정 명령 · 폰이 준 값은 안 쓴다 · 이미돌면 안 띄움 · 간격·하루 상한)
  (5분 순찰 = Claude 데스크톱 앱 로그인이 풀리면 폰에 «Claude 다시 로그인 필요» 한 번 · 11-20 · 기록 = _index/server/login-alert.json)
  (새벽 5시 순찰 = RC 다시 켜기 · 11-18 — 서버가 띄운 RC 이고 2시간 활동 없고 자식 세션이 안 일할 때만 자식째 끄고 다시 띄움 · 결과 = _index/server/rc-night.json)
  (시작 때 한 번 = RC 되살리기 · 11-27 — 서버가 띄운 RC 가 서버와 함께 사라졌으면(재부팅·로그오프·충돌) 다시 띄움 · 서버가 RC 죽음을 봤으면 안 함)
  (5분 순찰 = 망 끊김 뒤 RC 다시 켜기 · 11-27 — 서버 몫 RC 가 망이 10분 넘게 끊겨 스스로 내려갔으면(rc.log «giving up») 망이 돌아온 순찰에 다시 띄움 · 하루 RC_NET_DAY 번)
"""
import _socket
import datetime
import difflib
import hashlib
import http.server
import json
import mimetypes
import os
import posixpath
import re
import secrets
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse

MOD = os.path.dirname(os.path.abspath(__file__))     # mobility 모듈 scripts(11-16 · 옛 자리 3_시스템/server.py)
# HERE = 볼트의 3_시스템(코어 대본·_index) — 시험 사본은 임시 볼트의 3_시스템 안(옆에 roles.py)에 두므로 그 자리
HERE = MOD if os.path.isfile(os.path.join(MOD, 'roles.py')) else os.path.normpath(os.path.join(MOD, '..', '..', '..', '..', '3_시스템'))
VAULT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, MOD)                             # alarms 는 같은 모듈 자리
import fileops  # noqa: E402 — 볼트에 쓰는 것은 장부에(by = phone)
import roles  # noqa: E402
import schedule  # noqa: E402 — 일정 줄 문법은 한 곳
import alarms  # noqa: E402 — 무엇을 언제 울릴지는 알림 모듈이 정한다
import core_api  # noqa: E402 — 계약 밖 코어(찾기·주제·기록 보존·RC 상태)는 이 감싸개 한 곳(계획서 §6.1)
import pair as pairing  # noqa: E402 — 짝짓기·붙은 기기·열쇠 바꾸기(M2)
import ready  # noqa: E402 — 폰 «준비 목록» 보고(M7)
import notechat_route  # noqa: E402 — 탭 곁창(볼트 클로드 · 노트 특화 · 11-21)
try:
    import tabwork  # noqa: E402 — 탭 곁창 작업 모드(폰 지문 승인 · 11-22)
except ImportError:                 # 작업 모드 대본이 안 실린 판 — 길은 남기고 «묻기»로만 답한다
    tabwork = None
import pdfprint  # noqa: E402 — 폰 «PDF 로 볼트에 저장»·«PDF 로 공유»: 폰이 그린 HTML → 이 PC 헤드리스 브라우저 인쇄(11-23)
try:
    import vaultwatch  # noqa: E402 — 볼트 바뀜 버스(11-23 · PC 쪽 바뀜을 폰이 몇 초 안에)
except ImportError:     # 대본을 골라 복사하는 옛 시험·배포 — 버스 없이 뜬다(폰은 옛 길 = 5분 목록)
    vaultwatch = None
core_api.init(HERE)

STATE = os.path.join(HERE, '_index', 'server')
TOKEN = os.path.join(STATE, 'token')
CONFIG = os.path.join(STATE, 'config.json')
LOG = os.path.join(STATE, 'server.log')
READ_ROOTS = ('0_작업/', '1_수집/', '2_지식/')  # mf:allow-path  (폰이 원본을 보고 고친 원본을 휴지통 거쳐 덮음 · 사용자 결정 · mobility 작업 F)
DOC_ROOTS = ('3_시스템/설명서/',)                    # 읽기만(파일·링크) — 폰 «설명서»의 장 링크가 열리게(모바일볼트 1-5 · 목록·찾기·쓰기·폰 손에는 안 든다)
WRITE_ROOTS = ('0_작업/', '2_지식/')  # mf:allow-path  (폰 사람 쓰기 — 데스크톱 편집기 노릇 · fileops 장부 by=phone · 모듈 산출물 아님)
BIN_ROOTS = ('0_작업/', '1_수집/', '2_지식/')       # 폰 보기가 고친 원본(PUT /v1/file) — 데스크톱 brain-source 처럼 사람이 보호를 풀고 고친 것 · 1_수집 은 옛 판을 휴지통에 두고 덮는다  # mf:allow-path  (폰이 원본을 보고 고친 원본을 휴지통 거쳐 덮음 · 사용자 결정 · mobility 작업 F)
BIN_EXTS = {'docx', 'pptx', 'xlsx', 'csv', 'tsv', 'hwp', 'hwpx', 'sheet', 'html', 'htm', 'txt', 'log', 'v', 'sv', 'vhd', 'py', 'c', 'h', 'cpp', 'm', 'tex', 'typ', 'sdocx'}   # 폰 보기가 고칠 수 있는 형식(md 는 /v1/note · sdocx = 삼성노트 그 자리 필기 11-23)
BIN_MAX = 64 * 2 ** 20                              # 폰이 고쳐 올리는 원본 한 벌 상한(폰 보기 상한 docx 30 · pptx 60 MB)
UP_DIR = os.path.join(STATE, 'upload')              # 공유로 받는 중인 조각(볼트와 같은 드라이브 · git 밖) — 다 받으면 받은함으로 이름만 바꿔 옮긴다
UP_MARGIN = 2 * 2 ** 30                             # 공유 받기 상한 = PC 남은 자리 — 받고 나서 이보다 적게 남으면 507(사용자 11-16 «64mb 제한 없애기»)
UP_IDLE = 60                                        # 본문이 이만큼(초) 멈추면 끊는다 — 받은 앞부분은 남기고 폰이 이어 보낸다
UP_KEEP = 3 * 86400                                 # 이어 보내지 않고 이만큼 멈춘 조각은 지운다(서버 상태 자리 · 볼트 노트 아님)
UP_CHECK = 64 * 2 ** 20                             # 받는 동안 이만큼마다 남은 자리를 다시 잰다(다른 것이 PC 를 채울 수 있다)
BAD_PART = re.compile(r'[<>:"|?*\x00-\x1f]')
HIDE_PART = {'_lms', '_색인'}          # 목록에는 안 보인다(색인 글자는 찾기 결과로 읽을 수 있다)
SENSITIVE = re.compile(r'^sensitive:[ \t]*true[ \t]*$', re.M)     # pre-commit 과 같은 판정
TITLE = re.compile(r'^title:[ \t]*(.*?)[ \t]*\r?$', re.M)          # 데스크톱 «파일» 탭 이름(brain-base tree.ts — 속성 title 이 글일 때만)
NOT_TEXT = re.compile(r'[-+]?(\d+(\.\d*)?|\.\d+)|true|false|null|~|\[.*\]|\{.*\}', re.I)    # 옵시디언이 글로 안 읽는 값(숫자·참거짓·빈 값·목록)
HOME_TTL, TOPIC_TTL, DESK_TTL = 60, 30, 10
MAX_BODY = 4 * 2 ** 20
SEND_STEP = 2 ** 20                                 # 파일을 이만큼씩 읽어 보낸다(큰 원본도 서버 메모리 고정)
BYTE_RANGE = re.compile(r'bytes=(\d*)-(\d*)')       # 한 구간만 — 여러 구간은 없는 셈 친다(전체 200)
LOG_MAX = 2 ** 20                                   # 넘으면 server.log.1 로 밀고 새로 쓴다
DIAG_BODY, DIAG_LINES, DIAG_CHARS, DIAG_DAY = 64 * 2 ** 10, 50, 240, 1000     # 폰이 고장 나도 로그가 안 불어나게
RESERVED = re.compile(r'(con|prn|aux|nul|com\d|lpt\d)(\..*)?', re.I)    # 윈도 예약 이름
PLUGIN_PATH = re.compile(r'/v1/plugin/([a-z0-9-]+)(?:/(core\.js|styles\.css|main\.js|manifest\.json|brain-server\.zip|hwp\.js|rhwp_bg\.wasm|sheet\.js|calc\.js|edit\.js|edit\.css|sheetedit\.js|hwpedit\.js|inkpdf\.js))?')    # 이 꼴 말고는 못 읽는다(위로 나가기 없음) · main·manifest = 폰 보기 플러그인 설치 · hwp·sheet·calc(.sheet 수식 계산 · 모바일볼트 4-5) = 그 형식을 처음 열 때 받는 큰 묶음 · edit·sheetedit·hwpedit(+edit.css) = 폰 편집(«고치기»를 처음 누를 때) · inkpdf = 필기를 PDF 로(처음 내보낼 때) · brain-server.zip = 손발 앱이 폰 옵시디언 볼트를 만들 때(M2 · 11-26 · 열쇠로 · 짝 코드 없이)
APP_PATH = re.compile(r'/v1/app/(brain-phone)(?:/(brain-phone\.apk))?')    # 폰 앱 자기 갱신 — 이 꼴 말고는 못 읽는다 · 파일은 STATE/app/<id>/ 의 version.json 과 APK 뿐(빌더 build.py --publish 가 올린다)
CTRL = re.compile(r'[\x00-\x1f\x7f]+')
LOG_LOCK = threading.Lock()
RC_ARGS = ('remote-control', '--permission-mode', 'auto')     # 사용자 결정(11-05) — 이 명령 말고는 안 띄운다(권한 꼴만 config «rc_mode»)
RC_MODES = ('auto', 'default', 'acceptEdits', 'plan')    # 조리법 rc_mode 가 고를 수 있는 꼴(11-21) — 그 밖(권한 건너뛰기 등)은 auto 로
RC_GAP, RC_DAY = 60, 10                             # 켜기 요청 상한(초 · 하루)
RC_WATCH = 30                                       # 켠 뒤 지켜보는 초
RC_NET_DAY = 6                                      # 망 끊김으로 내려간 RC 를 순찰이 다시 켜는 하루 상한(망이 «닿는데» RC 만 계속 내려가는 고리를 끊음)
RC_NET_HOST = ('api.anthropic.com', 443)            # 망이 돌아왔나 — RC 가 붙는 곳에 TCP 만 열어 봄(보내는 것 없음)
RC_GIVEUP = re.compile(r'Persistent errors for .{1,40}giving up')    # RC 가 망 끊김에 스스로 내려갈 때 rc.log 끝에 남기는 줄(11-27 17:29 잼)
RC_LOG = os.path.join(STATE, 'rc.log')
RC_LOG_MARK = os.path.join(STATE, 'rc-log.json')    # 지금 rc.log 를 «끝에만 쓰는 손잡이»로 열어 넘겼다는 표시 — 그때만 앞을 자른다(옛 손잡이면 자른 자리에 구멍이 생김)
RC_LOG_MAX, RC_LOG_KEEP = 4 * 2 ** 20, 256 * 2 ** 10    # 넘으면 끝 256KB 만 남긴다(11-17 · RC 화면 다시 그리기로 115MB 까지 불었음)
RC_OWN = os.path.join(STATE, 'rc-own.json')         # 서버가 띄운 RC {pid, start} — 손으로 띄운 RC 와 가른다(새벽 다시 켜기는 서버 몫만)
LOGIN_ALERT = os.path.join(STATE, 'login-alert.json')   # Claude 앱 로그인 풀림 알림 — 알린 풀림(episode) · 같은 만료에 한 번(11-20 사고)
RC_NIGHT = os.path.join(STATE, 'rc-night.json')     # 새벽 다시 켜기 상태 — 그날 결과·까닭 · rc.log 마지막 화면이 바뀐 때(frame_at)
RC_NIGHT_H, RC_IDLE = 5, 2 * 3600                   # 새벽 5시 순찰에 한 번 · RC 활동(폰 세션 기록 · rc.log 화면 바뀜)이 2시간 없을 때만(11-18)
RC_BUSY_CPU, RC_BUSY_WAIT = 0.5, 10                 # 자식 세션이 10초에 CPU 0.5초를 넘게 쓰면 «일하는 중»(쉬는 자식 = 0.02~0.14초 · 11-18 잼)
RC_FRAME = re.compile(rb'\x1b\[\d+A\x1b\[J')        # RC 화면 다시 그리기 머리 — RC 는 1초마다 같은 화면을 다시 써서(1.1KB/초) 쓰기 시각으론 활동을 못 가른다
TOOL_SHELLS = {'bash.exe', 'sh.exe', 'pwsh.exe', 'powershell.exe', 'cmd.exe'}     # 자식 세션 아래 이것이 돌면 도구(Bash·PowerShell)를 돌리는 중
WRITE = threading.Lock()                            # 볼트 쓰기는 한 번에 하나
WD = '월화수목금토일'


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def log(msg):
    try:
        with LOG_LOCK:
            os.makedirs(STATE, exist_ok=True)
            if os.path.exists(LOG) and os.path.getsize(LOG) > LOG_MAX:
                os.replace(LOG, LOG + '.1')
            with open(LOG, 'a', encoding='utf-8', newline='\n') as f:
                f.write(f'{now()} {msg}\n')
    except OSError:
        pass


def token():
    if not os.path.exists(TOKEN):
        os.makedirs(STATE, exist_ok=True)
        with open(TOKEN, 'w', encoding='utf-8') as f:
            f.write(secrets.token_urlsafe(32))
    with open(TOKEN, encoding='utf-8') as f:
        return f.read().strip()


_tok = {'mt': None, 'v': ''}


def cur_token():
    """지금 열쇠 — 열쇠 파일 판이 바뀌면 다시 읽는다(«폰 연결» 열쇠 바꾸기 = pair.py rotate · 옛 열쇠는 바로 401). 파일이 없어지면 마지막 값."""
    try:
        mt = os.stat(TOKEN).st_mtime_ns
    except OSError:
        return _tok['v'] or TOKEN_VALUE
    if mt != _tok['mt']:
        try:
            with open(TOKEN, encoding='utf-8') as f:
                v = f.read().strip()
        except OSError:
            v = ''
        if v:
            if _tok['mt'] is not None and v != _tok['v']:
                log('열쇠 바뀜 — 옛 열쇠는 401')
            _tok.update(mt=mt, v=v)
    return _tok['v'] or TOKEN_VALUE


def config():
    try:
        with open(CONFIG, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class Bad(Exception):
    def __init__(self, code, msg, **extra):
        super().__init__(msg)
        self.code, self.msg, self.extra = code, msg, extra


# ───────── 경로 ─────────
def clean(rel, roots=READ_ROOTS):
    """볼트 상대 경로만 — 위로 나가기·드라이브·숨은 스트림·끝 점/공백(윈도가 지워 다른 파일이 된다)·점 폴더를 막고 실제 경로까지 확인한다."""
    rel = (rel or '').replace('\\', '/').strip('/')
    parts = rel.split('/')
    if not rel or any(not p or p in ('.', '..') or p.startswith('.') or p != p.rstrip(' .') or BAD_PART.search(p) for p in parts):
        raise Bad(400, '경로가 잘못됨')
    if not (rel + '/').startswith(roots):
        raise Bad(403, '이 자리는 안 됨')
    a = os.path.join(VAULT, *parts)
    real, base = os.path.realpath(a), os.path.realpath(VAULT)
    if real != base and not real.startswith(base + os.sep):
        raise Bad(403, '볼트 밖')
    return rel, a


def front(a):
    """md 머리(앞 4KB)의 속성 칸 글 — 없으면 ''. 민감 판정과 이름(title)을 한 번 읽기로."""
    if not a.lower().endswith('.md'):
        return ''
    try:
        with open(a, encoding='utf-8', errors='replace') as f:
            head = f.read(4096)
    except OSError:
        return ''
    return fm_of(head)


def fm_of(head):
    """글 머리의 속성 칸 — front 와 같은 자르기(폰이 보낸 글을 파일에 쓰기 전에 같은 잣대로 본다)."""
    if not head.startswith('---'):
        return ''
    end = head.find('\n---', 3)
    return head[:end] if end > 0 else head


def sensitive(a):
    return bool(SENSITIVE.search(front(a)))


_ps = {'key': (), 'hide': False}


def hide_sensitive():
    """폰에 민감 노트를 숨기나 — config.json «phone_sensitive»: «show»(없을 때 기본 · 사용자 11-16 C선택) | «hide»(옛 동작) · 모르는 값 = 숨김(안전 쪽).
    폰 보기 길(목록·읽기·찾기·링크·홈·주제·할 일·고치기·옮기기·휴지통 목록)만 이 값을 따른다. git 쪽(pre-commit·pre-push · 자동 커밋 순찰 =
    stop-check.py --commit-only)은 서버 밖에서 같은 표시를 따로 읽으므로 이 값과 무관하다 — «show» 에서도 민감 노트는 커밋되지 않는다.
    설정 파일이 바뀔 때만 다시 읽고(재시작 없이 바뀜), 값이 바뀌면 홈·주제·데스크 캐시를 비운다."""
    try:
        st = os.stat(CONFIG)
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        key = None
    if key != _ps['key']:
        v = config().get('phone_sensitive', 'show')
        hide = v != 'show'
        if v not in ('show', 'hide'):
            log(f'phone_sensitive 모르는 값 → 숨김: {CTRL.sub(" ", str(v))[:40]}')
        if hide != _ps['hide']:
            _home['v'] = _desk['v'] = None
            _cards.clear()
        _ps.update(key=key, hide=hide)
    return _ps['hide']


def phone_hidden(a):
    """폰 보기에서 뺄 파일 — 민감이고 «hide» 일 때만."""
    return hide_sensitive() and sensitive(a)


def title_of(fm):
    """속성 title 이 글이면 그 글(따옴표 뗌) — 데스크톱 «파일» 탭(brain-base)이 줄 이름으로 쓰는 값 · 숫자·참거짓·빈 값·목록은 없음."""
    m = TITLE.search(fm or '')
    s = m.group(1) if m else ''
    if len(s) >= 2 and s[0] == s[-1] and s[0] in '\'"':
        s = s[1:-1]
    elif NOT_TEXT.fullmatch(s):
        return None
    return s.strip() or None


def etag_of(a):
    """md 는 내용으로(수정 충돌 판정) · 그 밖은 크기·시각(큰 파일을 읽지 않게)."""
    st = os.stat(a)
    if a.lower().endswith('.md') and st.st_size < MAX_BODY * 4:
        with open(a, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()[:16]
    return f'{st.st_size:x}-{st.st_mtime_ns:x}'


def byte_range(value, size):
    """Range 머리글 → (시작, 길이). 없거나 못 읽는 꼴·여러 구간·빈 파일이면 None(전체를 준다 · HTTP 가 허락) · 파일 밖이면 416."""
    m = BYTE_RANGE.fullmatch((value or '').strip())
    if not m or not (m.group(1) or m.group(2)) or not size:
        return None
    if not m.group(1):                                  # bytes=-N = 끝에서 N
        n = min(int(m.group(2)), size)
        if not n:
            raise Bad(416, '범위 밖', size=size)
        return size - n, n
    start = int(m.group(1))
    end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
    if m.group(2) and int(m.group(2)) < start:
        return None
    if start >= size:
        raise Bad(416, '범위 밖', size=size)
    return start, end - start + 1


# ───────── 찾기 — 처음 부를 때 올리고 한동안 쓰지 않으면 내린다(메모리) ─────────
class Finder:
    IDLE = 30 * 60

    def __init__(self):
        self.lock = threading.Lock()
        self.mod = self.idx = self.model = self.name = None
        self.mtime = self.used = 0

    def load(self):
        if self.mod is None:
            self.mod = core_api.search_module()     # 게이트 코어 search.py — 불러오기는 감싸개 한 곳
        mt = os.path.getmtime(self.mod.INDEX_PATH) if os.path.exists(self.mod.INDEX_PATH) else 0
        if self.idx is None or mt != self.mtime:
            self.idx, self.mtime = self.mod.load_index(), mt

    def search(self, q, k, mode):
        with self.lock:
            self.load()
            if mode != 'lexical' and self.model is None:
                self.model, self.name = self.mod.load_query_model()
            self.used = time.time()
            rows = self.mod.ranked(q, self.idx, mode, self.model, self.name)
            notes = self.mod.notes(self.idx)
            out = fresh_hits(q, self.idx, k)    # 색인이 아직 모르는 새 노트·고친 노트(버스가 본 것 · 11-23)
            seen = {x['path'] for x in out}
            for score, rp in rows:
                if len(out) >= k:
                    break
                if '/_lms/' in rp or not (rp + '/').startswith(READ_ROOTS):
                    continue                    # 원시 JSON 색인은 찾기를 어지럽힌다(10-25 실측)
                a = os.path.join(VAULT, *rp.split('/'))
                gist = (notes.get(rp) or {}).get('gist', '')
                if not os.path.exists(a):
                    rp = moved_to(rp)           # 옮긴 노트 = 새 자리(색인을 다시 만들 때까지 · 11-23)
                    if not rp:
                        continue
                    a = os.path.join(VAULT, *rp.split('/'))
                if rp in seen or phone_hidden(a):
                    continue
                seen.add(rp)
                out.append({'path': rp, 'score': round(float(score), 4), 'gist': gist})
            return out

    def unload_if_idle(self):
        with self.lock:
            if self.idx is not None and time.time() - self.used > self.IDLE:
                self.idx = self.model = None
                import gc
                gc.collect()


FIND = Finder()


# ───────── 상태 ─────────
_net = {'at': 0, 'ssid': '', 'job': None}


def read_ssid():
    out = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, timeout=30,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.decode('utf-8', 'replace')
    m = re.search(r'^\s*SSID\s*:\s*(.+?)\s*$', out, re.M)
    return m.group(1) if m else ''


def refresh_ssid():
    try:
        _net['ssid'] = read_ssid()
    except (OSError, subprocess.SubprocessError):
        pass                                        # 못 읽었다고 «모름»으로 바꾸지 않는다 — 폰이 «잠듦·PC 밖»을 가리는 값이다
    _net.update(at=time.time(), job=None)


SSID_FRESH = 600       # 이만큼 안에 읽은 값이면 핑이 기다리지 않는다(sweep 이 5분마다 읽어 둔다)


def ssid():
    """지금 Wi-Fi 이름 — netsh 는 평소 0.3~0.6초지만 깨어난 직후 5초를 넘긴다(11-04 실측). 10분 안에 읽은 값이 있으면 기다리지 않고 그 값 · 뒤에서 새로 읽는다
    (11-12 앱을 켤 때 첫 핑 1~1.6초가 이 기다림). 값이 없거나 10분을 넘겼으면(잠들었다 옮겨졌을 수 있다) 전처럼 잠깐 기다리고 늦으면 전 값으로 답한다. 처음 한 번은 더 기다린다."""
    age = time.time() - _net['at']
    if _net['job'] is None and age > 60:
        _net['job'] = threading.Thread(target=refresh_ssid, daemon=True)
        _net['job'].start()
    job = _net['job']
    if job is not None and (not _net['at'] or age > SSID_FRESH):
        job.join(1.5 if _net['at'] else 6)
    return _net['ssid']


def power():
    import ctypes

    class S(ctypes.Structure):
        _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte), ('sys', ctypes.c_ubyte),
                    ('life', ctypes.c_ulong), ('full', ctypes.c_ulong)]
    s = S()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
        return {'ac': None, 'pct': None}
    return {'ac': s.ac == 1, 'pct': s.pct if s.pct <= 100 else None}


def proc_start(pid):
    """살아 있는 프로세스의 시작 시각(FILETIME) · 없으면 None."""
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    h = wintypes.HANDLE(k.OpenProcess(0x1000, False, int(pid)))      # PROCESS_QUERY_LIMITED_INFORMATION
    if not h.value:
        return None
    try:
        t = (wintypes.FILETIME * 4)()
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:     # STILL_ACTIVE
            return None
        if not k.GetProcessTimes(h, *[ctypes.byref(x) for x in t]):
            return None
        return (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime
    finally:
        k.CloseHandle(h)


def rc_dir():
    """이 볼트의 Claude 프로젝트 자리 — RC 기록(bridge-pointer.json)과 대화 기록(jsonl)"""
    home = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    return os.path.join(home, 'projects', re.sub(r'[^A-Za-z0-9]', '-', VAULT))


def rc_pointer():
    """`claude remote-control` 이 이 볼트에 남긴 기록(pid · 시작 시각 · 환경) — 그 pid 가 살아 있고 시작 시각이 같을 때만 · 아니면 None."""
    try:
        with open(os.path.join(rc_dir(), 'bridge-pointer.json'), encoding='utf-8') as f:
            d = json.load(f)
        start = proc_start(d['pid'])
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None
    if start is None or ('procStart' in d and str(d['procStart']) != str(start)):      # pid 는 다시 쓰인다
        return None
    return d


def rc_state():
    """`claude remote-control` 이 이 볼트에서 도는가 — 그 서버가 남긴 기록(pid · 시작 시각 · 환경)을 프로세스와 맞춰 본다."""
    d = rc_pointer()
    if not d:
        return {'up': False}
    env = str(d.get('environmentId') or '')
    return {'up': True, **({'url': 'https://claude.ai/code?environment=' + env} if re.fullmatch(r'env_[A-Za-z0-9]+', env) else {})}


_rc = {'day': '', 'n': 0, 'at': 0}
_T0 = time.time()                                   # 서버 시작 — rc.log 화면을 아직 못 봤으면 RC 활동을 이때로 친다
RC_LOCK = threading.Lock()


def rc_watch(p):
    """켠 뒤 첫 시간을 지켜본다 — 진짜 RC 가 창 없이 도는지는 폰 단추 첫 사용 때 이 로그로 판정한다(ADR-037)."""
    try:
        code = p.wait(RC_WATCH)
    except subprocess.TimeoutExpired:
        return log(f'RC {RC_WATCH}초 살아 있음 기록={"있음" if rc_state()["up"] else "없음"}')
    core_api.rc_set('failed')                   # 폰 단추 = 회색 «켜기 실패 — PC rc.log»(계정이 auto 모드를 못 쓰는 등 · 10분 뒤 다시 잼)
    rc_seen_tick()                              # 죽은 것을 봄 = 다음 시작 때 되살리지 않음
    log(f'RC 일찍 끝남 코드={code} · rc.log 를 볼 것')


def rc_log_open():
    """rc.log 를 새로 연다 — 윈도는 FILE_APPEND_DATA 만 든 손잡이(받은 RC 가 어디에 쓰든 늘 파일 끝 · 나눠 쓰기 허용)라 서버가 앞을 잘라도 구멍이 안 생긴다.
    그렇게 열었으면 표시 파일(RC_LOG_MARK)을 남긴다 · 다른 OS·실패 = 옛 길(통째로 새로 · 자르지 않음)."""
    try:
        os.remove(RC_LOG_MARK)
    except OSError:
        pass
    if os.name == 'nt':
        try:
            import _winapi
            import msvcrt
            access = 0x4 | 0x80 | 0x100000          # FILE_APPEND_DATA · FILE_READ_ATTRIBUTES · SYNCHRONIZE (FILE_WRITE_DATA 없음 = 끝에만)
            h = _winapi.CreateFile(RC_LOG, access, 0x7, 0, 2, 0x80, 0)     # 나눠 쓰기 읽기·쓰기·지우기 · CREATE_ALWAYS · NORMAL
            out = os.fdopen(msvcrt.open_osfhandle(h, os.O_WRONLY | os.O_APPEND), 'ab', buffering=0)
            with open(RC_LOG_MARK, 'w', encoding='utf-8') as f:
                json.dump({'append': True, 'at': int(time.time())}, f)
            return out
        except OSError as e:
            log(f'rc.log 끝 손잡이 못 엶 {type(e).__name__} — 옛 길')
    return open(RC_LOG, 'wb')


def trim_rc_log():
    """rc.log 가 RC_LOG_MAX 를 넘으면 끝 RC_LOG_KEEP 만 남긴다(줄 머리에서 자름) — 끝에만 쓰는 손잡이로 넘긴 때(표시 파일)만. 자른 사이 RC 가 쓴 몇 줄은 잃을 수 있다."""
    try:
        if os.path.getsize(RC_LOG) <= RC_LOG_MAX or not os.path.isfile(RC_LOG_MARK):
            return False
        with open(RC_LOG, 'r+b') as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - RC_LOG_KEEP))
            tail = f.read(RC_LOG_KEEP)
            cut = tail.find(b'\n')
            tail = tail[cut + 1:] if 0 <= cut < len(tail) - 1 else tail
            head = f'… 앞 {(size - len(tail)) // 2 ** 20}MB 잘림 {now()}\n'.encode('utf-8')
            f.seek(0)
            f.write(head + tail)
            f.truncate()
        log(f'rc.log {size // 2 ** 20}MB → {(len(head) + len(tail)) // 2 ** 10}KB')
        return True
    except OSError:
        return False


def rc_start(_b):
    """폰 단추 → Remote Control 켜기. 고정 명령 · 작업 폴더 = 볼트 · 창 없음 · 이미 돌면 안 띄움(ADR-037). 폰이 준 값은 안 읽는다."""
    with RC_LOCK:
        own = rc_own_load()
        if rc_state()['up'] or (own and rc_own_alive(own)):     # 서버가 막 띄워 RC 기록(bridge-pointer)이 아직 없을 때도(시작 때 되살리기 · 재시작 뒤 rc_up 과 겹침)
            return {'ok': True, 'started': False}
        day = time.strftime('%Y-%m-%d')
        if _rc['day'] != day:
            _rc.update(day=day, n=0)
        if _rc['n'] >= RC_DAY or time.time() - _rc['at'] < RC_GAP:
            log('RC 켜기 상한')
            raise Bad(429, '너무 자주')
        _rc.update(n=_rc['n'] + 1, at=time.time())
        env = rc_env()
        rc_launch(rc_cmd(env), env)
        return {'ok': True, 'started': True}


def rc_env():
    return {k: v for k, v in os.environ.items() if not re.match(r'CLAUDECODE|CLAUDE_CODE|CLAUDE_AGENT|ANTHROPIC_', k)}


def rc_cmd(env):
    """띄울 명령 — 구독 해지·로그인 끊김이면 Bad(409)로 안 띄운다(11-11 · RC 는 구독으로만 돈다)."""
    test = os.environ.get('BRAIN_RC_BIN')           # 시험 = 가짜 실행 파일
    if test:
        cmd = json.loads(test)
    else:
        import claude_bin
        cmd = [claude_bin.newest()]
    if not test or os.environ.get('BRAIN_CLAUDE_BIN'):
        import claude_bin
        st = claude_bin.check(env)
        if not st['ok']:
            if st['kind'] in (claude_bin.LAPSED, claude_bin.LOGIN):
                claude_bin.alert()
            core_api.rc_set(core_api.code_of(st['kind']))     # 다음 ping 부터 폰 단추 = 회색 + 까닭
            log(f"RC 켜기 멈춤: {st['kind']}")
            raise Bad(409, claude_bin.TITLE.get(st['kind'], st['kind']), kind=st['kind'])
    return cmd


VIEWER_ID = 'brain-source-mobile'


def viewer_off():
    """기능 단계 «폰 보기 받기»(mobility.viewer · 기본 켬) — 끔이면 폰에 폰 보기를 안 내준다. 못 읽으면 켬."""
    try:
        import options
        return options.level('mobility.viewer', VAULT) == 'off'
    except Exception:  # noqa: BLE001
        return False


def rc_args():
    """RC 고정 명령 — 권한 꼴만 config «rc_mode»(조리법 · 기본 auto · RC_MODES 밖이면 auto) · 폰이 준 값은 안 씀"""
    m = config().get('rc_mode')
    return RC_ARGS[:2] + ((m if m in RC_MODES else RC_ARGS[2]),)


def rc_launch(cmd, env):
    """RC 를 띄운다(고정 명령 · 작업 폴더 = 볼트 · 창 없음) — 띄운 pid 를 RC_OWN 에 남겨 새벽 다시 켜기가 서버 몫으로 안다."""
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    with rc_log_open() as out:                      # 안 뜨면 까닭이 남게 — 켤 때마다 새로 · 끝에만 쓰는 손잡이라 서버가 앞을 잘라 크기를 묶는다(trim_rc_log)
        args = dict(cwd=VAULT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
        try:
            p = subprocess.Popen(cmd + list(rc_args()), creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **args)     # 서버가 다시 떠도 살아 있게
        except PermissionError:
            p = subprocess.Popen(cmd + list(rc_args()), creationflags=flags, **args)
    try:
        with open(RC_OWN, 'w', encoding='utf-8') as f:
            json.dump({'pid': p.pid, 'start': proc_start(p.pid), 'at': int(time.time())}, f)
    except OSError:
        pass
    log(f'RC 켬 pid={p.pid}')
    _rc_seen['pid'] = p.pid                     # 이 서버가 띄움 = 살아 있는 것을 봄(죽으면 순찰·rc_watch 가 gone 을 적는다)
    threading.Thread(target=rc_watch, args=(p,), daemon=True).start()
    return p


# ───────── RC 되살리기(11-27) ─────────
# 11-26 23:43 윈도우 업데이트(Dism.exe)가 PC 를 다시 켰다. 재시작 뒤 다시 세팅(restart.py after)은 제가 건 재시작(before.json)만 보므로
# 서버가 띄운 RC 가 돌아오지 않았다(incident-2026-11-27). 서버가 «RC 가 죽는 것을 봤나»를 RC_OWN 의 gone 으로 남기고,
# 시작 때 gone 이 없는데 RC 가 없으면 = 서버와 함께 사라짐(재부팅·로그오프·충돌) → 다시 띄운다. gone 이 있으면 = 서버가 돌던 중에 끝남(끔·실패) → 안 띄운다.
_rc_seen = {'pid': None}                            # 이 서버가 살아 있는 것을 본 서버 몫 RC pid — 본 적 없으면 죽어도 gone 을 안 적는다(재부팅 뒤 새 서버)


def rc_own_load():
    try:
        with open(RC_OWN, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) and d.get('pid') else None
    except (OSError, ValueError):
        return None


def rc_own_alive(d):
    """RC_OWN 의 RC 가 지금 살아 있나 — pid 와 시작 시각이 같을 때만(pid 는 다시 쓰인다)"""
    try:
        st = proc_start(int(d['pid']))
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return st is not None and str(st) == str(d.get('start'))


def rc_seen_tick():
    """순찰(5분)·RC 일찍 끝남 — 서버 몫 RC 가 살아 있으면 «봄», 이 서버가 살아 있는 것을 봤는데 이제 없으면 RC_OWN 에 gone 을 적는다.
    돌려줌 = 'alive' | 'gone'(이번에 적음) | None(기록 없음 · 이미 gone · 본 적 없음)"""
    d = rc_own_load()
    if not d or d.get('gone'):
        return None
    if rc_own_alive(d):
        _rc_seen['pid'] = d['pid']
        return 'alive'
    if _rc_seen['pid'] != d['pid']:
        return None
    d['gone'] = int(time.time())
    if rc_gave_up():
        d['why'] = 'net'                        # 망 끊김으로 스스로 내려감 = 끈 것이 아님 → 순찰이 망을 보고 다시 켬(rc_net_tick)
    try:
        with open(RC_OWN, 'w', encoding='utf-8') as f:
            json.dump(d, f)
    except OSError:
        return None
    if d.get('why') == 'net':
        log(f"RC 끝남 봄 pid={d['pid']} — 망이 10분 넘게 끊겨 RC 가 스스로 내려감 · 망이 돌아오면 순찰이 다시 켬")
    else:
        log(f"RC 끝남 봄 pid={d['pid']} — 다음 시작 때 되살리지 않음")
    return 'gone'


def rc_gave_up():
    """지금 rc.log(이 RC 가 켤 때 새로 연 파일)의 끝이 «망 끊김에 스스로 내려감»인가 — 끝 8KB 만 읽고 화면 제어 문자를 지운다."""
    try:
        with open(RC_LOG, 'rb') as f:
            f.seek(max(0, f.seek(0, 2) - 8192))
            tail = f.read().decode('utf-8', 'replace')
    except OSError:
        return False
    return bool(RC_GIVEUP.search(re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', tail)))


def rc_resume_why(own, up, session):
    """순수 판정 — 시작 때 RC 를 되살릴까. own = RC_OWN 기록 · up = 이 볼트 RC 가 돎 · session = 이 서버의 세션 번호(모르면 None).
    돌려줌 = '' (되살림) | 안 하는 까닭"""
    if session == 0:
        return '세션 0(로그인 전 서버) — 로그인 뒤 서버가 함'
    if up:
        return 'RC 돎'
    if not own:
        return '서버가 띄운 RC 기록 없음'
    if own.get('gone') and own.get('why') == 'net':
        return '망 끊김으로 내려간 RC — 순찰이 망을 보고 다시 켬'
    if own.get('gone'):
        return '서버가 돌던 중에 RC 가 끝남(끔·실패) — 안 띄움'
    if rc_own_alive(own):
        return 'RC 돎'
    return ''


def rc_resume():
    """서버 시작 때 한 번(뒤 스레드) — 서버가 띄운 RC 가 서버와 함께 사라졌으면 rc_start 와 같은 길(구독·로그인 확인 → 띄움)로 다시 띄운다. 결과는 서버 로그 한 줄."""
    try:
        import server_swap
        session = server_swap.session_of(os.getpid())
    except Exception:  # noqa: BLE001 — 세션을 모르면 사용자 세션으로 친다
        session = None
    with RC_LOCK:
        why = rc_resume_why(rc_own_load(), rc_state()['up'], session)
        if not why:
            env = rc_env()
            try:
                p = rc_launch(rc_cmd(env), env)
                why = f'다시 켬 pid={p.pid}'
            except Bad as e:
                why = f'못 켬 — {e.msg}'
            except OSError as e:
                why = f'못 켬 — {type(e).__name__}: {e}'
    if session != 0:
        rc_seen_tick()                          # 손 RC·이미 도는 RC 도 «봄»에 넣어 둔다
    log(f'RC 되살리기 {why}')
    return why


# ───────── 망 끊김 뒤 RC 다시 켜기(11-27) ─────────
# 11-27 17:02 Wi-Fi 가 끊기자 RC 는 10분 뒤 «Persistent errors for 10 minutes, giving up» 을 남기고 폰 세션 셋(빅보스 포함)째 내려갔다.
# 서버는 이것을 «끈 것»과 같은 gone 으로 적어 23:33 망이 돌아온 뒤에도 RC 가 꺼진 채였다. 이 경우만 why=net 으로 갈라 순찰이 다시 띄운다.
# 내려간 폰 세션은 돌아오지 않는다(새 RC 는 새 세션) — 망이 없던 동안 폰에서 PC 를 다시 잡을 길을 되돌릴 뿐이다.
_rc_net = {'day': '', 'n': 0}


def rc_net_up():
    """망이 돌아왔나 — RC_NET_HOST 에 TCP 연결만 열어 본다(5초)"""
    try:
        socket.create_connection(RC_NET_HOST, timeout=5).close()
        return True
    except OSError:
        return False


def rc_net_why(own, up, net, n):
    """순수 판정 — 순찰이 망 끊김으로 내려간 서버 몫 RC 를 다시 켤까. net = 망이 닿나(부르는 쪽이 잼 · 해당 없으면 안 잼 → None) · n = 오늘 다시 켠 수.
    돌려줌 = None(해당 없음) | '' (다시 켬) | 안 하는 까닭"""
    if not own or not own.get('gone') or own.get('why') != 'net' or up or rc_own_alive(own):
        return None
    if net is None:
        return None
    if not net:
        return '망 아직 없음'
    if n >= RC_NET_DAY:
        return f'오늘 {RC_NET_DAY}번 다 씀 — 손으로 켤 것(폰 «Claude 켜기»)'
    return ''


def rc_net_tick(net=None):
    """5분 순찰 — 망 끊김으로 내려간 서버 몫 RC 를 망이 돌아오면 rc_resume 과 같은 길(구독·로그인 확인 → 띄움)로 다시 띄운다. 세션 0 은 안 함.
    net = 시험용(참/거짓) · 없으면 해당될 때만 RC_NET_HOST 를 잼. 돌려줌 = None(해당 없음) | 결과 한 줄(로그는 다시 켬·못 켬·상한 처음만)"""
    own = rc_own_load()
    if rc_net_why(own, False, True, 0) is None:        # 망을 재기 전에 — 해당 없는 순찰(거의 전부)은 아무것도 안 함
        return None
    try:
        import server_swap
        if server_swap.session_of(os.getpid()) == 0:
            return None
    except Exception:  # noqa: BLE001 — 세션을 모르면 사용자 세션으로 친다
        pass
    day = time.strftime('%Y-%m-%d')
    if _rc_net['day'] != day:
        _rc_net.update(day=day, n=0)
    with RC_LOCK:
        own, up = rc_own_load(), rc_state()['up']
        if up and own and own.get('why') == 'net':     # 다른 RC(터미널에서 손으로)가 돎 = 그만 — 그 RC 를 나중에 끄면 끈 것으로 둔다(다시 켜지 않음)
            own.pop('why', None)
            try:
                with open(RC_OWN, 'w', encoding='utf-8') as f:
                    json.dump(own, f)
            except OSError:
                return None
            log('RC 망 끊김 뒤 다시 켜기 그만 — 다른 RC 가 돎')
            return '다른 RC 가 돎'
        why = rc_net_why(own, up, rc_net_up() if net is None else net, _rc_net['n'])
        if why is None or why == '망 아직 없음':
            return why
        if why:
            if _rc_net.get('told') != day:
                _rc_net['told'] = day
                log(f'RC 망 끊김 뒤 다시 켜기 {why}')
            return why
        _rc_net['n'] += 1
        env = rc_env()
        try:
            p = rc_launch(rc_cmd(env), env)
            why = f'다시 켬 pid={p.pid} · 오늘 {_rc_net["n"]}번째'
        except Bad as e:
            why = f'못 켬 — {e.msg}'
        except OSError as e:
            why = f'못 켬 — {type(e).__name__}: {e}'
    log(f'RC 망 끊김 뒤 다시 켜기 {why}')
    return why


def rc_info():
    """RC 상태 + 쓸 수 있나(M9 · 11-17) — can = ok · lapsed · login · notsub · limit · none · failed · unknown(core_api.CAN) · why = 폰 단추 아래 한 줄.
    돌고 있으면 ok · 아니면 claude_bin.check 를 10분 담아 둔 값(처음은 뒤에서 재고 unknown) — 단추는 숨기지 않고 회색 + 까닭."""
    st = rc_state()
    if st.get('up'):
        return {**st, 'can': 'ok'}
    can = core_api.rc_can(rc_env(), wait=0.3, test=bool(os.environ.get('BRAIN_RC_BIN')) and not os.environ.get('BRAIN_CLAUDE_BIN'))   # 시험 = rc_start 와 같은 판정
    return {**st, 'can': can, **({'why': core_api.CAN[can]} if core_api.CAN.get(can) else {})}


# ───────── RC 새벽 다시 켜기(11-18) ─────────
# 폰에서 연 RC 세션(`claude --print --sdk-url` · 부모 = RC)은 폰 앱에서 안 쓰게 돼도 PC 에 남아 사흘에 6개 3.3GB 가 됐다(램 13.9GB · 커밋 29/36GB).
# 새벽 5시 순찰에 한 번 — RC 가 서버 몫이고 2시간 활동이 없고 자식 세션이 일하지 않을 때만 RC 를 자식째 끄고 다시 띄운다.
# 아니면 그날은 건너뛰고 까닭을 RC_NIGHT 에 적는다. 손으로 띄운 RC(부모가 살아 있는 셸·터미널 · 부모가 죽었는데 서버가 띄운 기록 없음)는 끄지 않는다.
def proc_tree():
    """{pid: (부모 pid, 실행 파일 이름)} — 지금 도는 프로세스 전부(Toolhelp 한 번 · psutil 없이)"""
    import ctypes
    from ctypes import wintypes

    class PE(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD), ('pid', wintypes.DWORD), ('heap', ctypes.c_size_t),
                    ('mod', wintypes.DWORD), ('threads', wintypes.DWORD), ('ppid', wintypes.DWORD), ('pri', ctypes.c_long),
                    ('flags', wintypes.DWORD), ('exe', ctypes.c_wchar * 260)]
    k = ctypes.windll.kernel32
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    h = k.CreateToolhelp32Snapshot(2, 0)                # TH32CS_SNAPPROCESS
    if not h or h == ctypes.c_void_p(-1).value:
        return {}
    out, e = {}, PE()
    e.size = ctypes.sizeof(PE)
    try:
        more = k.Process32FirstW(wintypes.HANDLE(h), ctypes.byref(e))
        while more:
            out[e.pid] = (e.ppid, e.exe)
            more = k.Process32NextW(wintypes.HANDLE(h), ctypes.byref(e))
    finally:
        k.CloseHandle(wintypes.HANDLE(h))
    return out


def proc_cpu(pid):
    """살아 있는 프로세스가 지금까지 쓴 CPU 초(사용자+커널) · 못 열면 None"""
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    h = wintypes.HANDLE(k.OpenProcess(0x1000, False, int(pid)))
    if not h.value:
        return None
    try:
        t = (wintypes.FILETIME * 4)()
        if not k.GetProcessTimes(h, *[ctypes.byref(x) for x in t]):
            return None
        return sum((x.dwHighDateTime << 32) | x.dwLowDateTime for x in t[2:]) / 1e7
    finally:
        k.CloseHandle(h)


def rc_night_load():
    try:
        with open(RC_NIGHT, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def rc_night_save(d):
    try:
        tmp = RC_NIGHT + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, RC_NIGHT)
    except OSError:
        pass


def rc_frame_tick(now=None):
    """rc.log 의 마지막 온 화면이 바뀌었으면 그 때를 frame_at 에 — 세션 열림·닫힘·이름·다시 붙음이 화면을 바꾼다(순찰마다 · 끝 64KB 만 읽음)."""
    try:
        with open(RC_LOG, 'rb') as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - 64 * 2 ** 10))
            parts = RC_FRAME.split(f.read())
    except OSError:
        return False
    if len(parts) < 3:                              # 앞 조각(잘린 것)·끝 조각(쓰는 중) 말고 온 화면이 없음
        return False
    h = hashlib.sha1(parts[-2]).hexdigest()[:16]
    d = rc_night_load()
    if d.get('frame') == h:
        return False
    d.update(frame=h, frame_at=int(now or time.time()))
    rc_night_save(d)
    return True


def rc_owner(pid, tree):
    """('server' | 'hand', 까닭) — 부모가 살아 있으면 부모로(이 서버 = 서버 몫 · 셸·터미널 = 손으로 띄움).
    부모가 죽었으면(서버가 다시 뜸 · BREAKAWAY 라 RC 는 남는다) 띄운 기록으로 — RC_OWN, 그 전에 켠 RC 는 server.log «RC 켬 pid=N» 이 시작 2분 안."""
    start = proc_start(pid)
    ppid = (tree.get(pid) or (0, ''))[0]
    pstart = proc_start(ppid) if ppid in tree else None
    if pstart is not None and start is not None and pstart <= start:      # 부모 pid 가 다시 쓰였으면(나중에 뜬 것) 죽은 셈
        return ('server', '') if ppid == os.getpid() else ('hand', f'부모 {tree[ppid][1]} {ppid}')
    try:
        with open(RC_OWN, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('pid') == pid and str(d.get('start')) == str(start):
            return 'server', ''
    except (OSError, ValueError, AttributeError):
        pass
    t0 = ((start or 0) - 116444736000000000) / 1e7          # FILETIME → 유닉스 초
    for p in (LOG + '.1', LOG):
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError:
            continue
        for m in re.finditer(rf'^(\d{{4}}-\d\d-\d\d \d\d:\d\d:\d\d) RC 켬 pid={pid}$', text, re.M):
            if abs(time.mktime(time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')) - t0) < 120:
                return 'server', ''
    return 'hand', '부모 없음 · 서버가 띄운 기록 없음'


def rc_activity():
    """마지막 RC 활동 시각 — rc.log 화면이 바뀐 때(없으면 서버 시작) · 폰 RC 세션의 대화 기록(첫 줄 session-owner 인 jsonl)을 쓴 때 중 늦은 것"""
    last = rc_night_load().get('frame_at') or _T0
    try:
        for e in os.scandir(rc_dir()):
            if not e.name.endswith('.jsonl') or e.stat().st_mtime <= last:
                continue
            with open(e.path, 'rb') as f:
                if b'"session-owner"' in f.readline(4096):
                    last = e.stat().st_mtime
    except OSError:
        pass
    return last


def proc_family(pid, tree):
    """pid 와 그 아래 전부(손주까지) — 부모보다 먼저 뜬 것은 뺀다(죽은 부모의 pid 가 다시 쓰여 남의 고아가 섞이지 않게 · taskkill /T 는 이것을 안 가린다)"""
    sub = {}
    for p, (pp, _n) in tree.items():
        if p != pp:
            sub.setdefault(pp, []).append(p)
    out, todo = [], [pid]
    while todo:
        q = todo.pop()
        if q in out:
            continue
        out.append(q)
        sq = proc_start(q)
        for c in sub.get(q, []):
            sc = proc_start(c)
            if sq is not None and sc is not None and sc >= sq:
                todo.append(c)
    return out


def rc_busy(kids, tree):
    """자식 세션이 일하는 중이면 까닭 — 도구를 돌리는 중(아래에 셸) · CPU 를 쓰는 중(RC_BUSY_WAIT 초에 RC_BUSY_CPU 초 넘게 · 손주 포함). 아니면 ''"""
    fam = {}
    for k in kids:
        fam[k] = proc_family(k, tree)
        sh = [tree[q][1] for q in fam[k] if q != k and q in tree and tree[q][1].lower() in TOOL_SHELLS]
        if sh:
            return f'도구 도는 중({sh[0]})'
    use = lambda: {k: sum(proc_cpu(q) or 0 for q in fam[k]) for k in kids}
    a = use()
    time.sleep(RC_BUSY_WAIT)
    b = use()
    most = max((b[k] - a[k] for k in kids), default=0)
    return f'CPU {most:.1f}초/{RC_BUSY_WAIT}초' if most >= RC_BUSY_CPU else ''


def rc_kill(pid, start=None):
    """RC 를 자식(폰 세션)째 끈다 — 끄기 직전 pid 의 시작 시각이 start 와 다르면(다른 프로세스) 안 끔 · 꺼질 때까지 15초 기다림 · 꺼졌으면 True"""
    if start is not None and proc_start(pid) != start:
        return proc_start(pid) is None
    fam = proc_family(pid, proc_tree())
    try:
        subprocess.run(['taskkill', '/F'] + [x for q in fam for x in ('/PID', str(q))], capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        pass
    for _ in range(30):
        if proc_start(pid) is None:
            return True
        time.sleep(0.5)
    return False


def login_tick(st=None, send=None):
    """순찰(5분) — Claude 데스크톱 앱 로그인이 풀렸으면(3_시스템/claude_login.py) 폰에 «Claude 다시 로그인 필요»를 그 풀림에 한 번.
    11-20: 07:11 «sign-in is too old» 로 Code 탭·원격 제어가 멈췄는데 13:00 까지 아무도 몰랐다. 수명은 서버가 정해 막을 수 없고 알리기만 한다.
    보낸 풀림(since)을 LOGIN_ALERT 에 적는다 — 되찾았다 다시 풀리면 since 가 바뀌어 다시 한 번. 보내기 실패면 안 적고 다음 순찰에 다시.
    돌려줌 = 'sent' | 'same' | 'ok' | 'fail' | 'unknown'. send = 시험용(제목, 글, 대상) → 참/거짓."""
    if st is None:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import claude_login
        st = claude_login.state()
    if st.get('state') != 'stale':
        return st.get('state') or 'unknown'
    try:
        with open(LOGIN_ALERT, encoding='utf-8') as f:
            done = json.load(f)
    except (OSError, ValueError):
        done = {}
    if done.get('since') == st['since']:
        return 'same'
    title = 'Claude 다시 로그인 필요'
    text = f"PC 의 Claude 앱 로그인이 풀렸어요({st['since'][5:16]}) — Code 탭 세션·원격 제어가 멈춰 있어요. PC 에서 앱을 열고 다시 로그인하세요."
    if send is None:
        def send(t, x, target):
            r = subprocess.run([sys.executable, os.path.join(MOD, 'alert.py'), 'now', t, '--text', x, '--system', 'claude-login', '--target', target],
                               capture_output=True, timeout=60, creationflags=0x08000000 if os.name == 'nt' else 0)
            return r.returncode == 0
    ok = bool(send(title, text, st['since']))
    log(f"Claude 로그인 풀림 {st['since']} · 폰 알림 {'보냄' if ok else '못 보냄'}")
    if not ok:
        return 'fail'
    tmp = LOGIN_ALERT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'since': st['since'], 'sent_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'src': st.get('src')}, f, ensure_ascii=False)
    os.replace(tmp, LOGIN_ALERT)
    return 'sent'


def rc_nightly(now=None, force=False):
    """새벽 순찰 — 그날 RC_NIGHT_H 시 첫 순찰에 한 번(force = 시험). 결과(다시 켬 · 건너뜀 · 없음 · 못 끔)와 까닭을 RC_NIGHT 와 서버 로그에."""
    now = now or time.time()
    lt = time.localtime(now)
    day = time.strftime('%Y-%m-%d', lt)
    d = rc_night_load()
    if not force and (lt.tm_hour != RC_NIGHT_H or d.get('day') == day):
        return None
    res, why, extra = '건너뜀', '', {}
    with RC_LOCK:                                   # 폰 단추 켜기와 겹치지 않게
        ptr = rc_pointer()
        if not ptr:
            res, why = '없음', 'RC 안 돎'
        else:
            pid = int(ptr['pid'])
            start = proc_start(pid)
            tree = proc_tree()
            own, why = rc_owner(pid, tree)
            kids = [p for p, (pp, n) in tree.items() if pp == pid and p != pid and n.lower() != 'conhost.exe']
            extra = {'pid': pid, 'kids': len(kids), 'own': own}
            idle = now - rc_activity()
            if own != 'server':
                why = '손으로 띄운 RC — 끄지 않음' + (f'({why})' if why else '')
            elif idle < RC_IDLE:
                why = f'RC 활동 {int(idle // 60)}분 전'
            else:
                busy = rc_busy(kids, tree)
                if busy:
                    why = '자식 세션 일하는 중 — ' + busy
                else:
                    env = rc_env()
                    try:
                        cmd = rc_cmd(env)                       # 구독·로그인을 끄기 전에 — 끄고 못 켜는 일이 없게
                    except Bad as e:
                        why = f'못 켤 것이라 안 끔 — {e.msg}'
                    else:
                        try:
                            size = os.path.getsize(RC_LOG)
                        except OSError:
                            size = 0
                        if not rc_kill(pid, start):
                            res, why = '못 끔', f'pid {pid} 이 15초 안에 안 꺼짐'
                        else:
                            p = rc_launch(cmd, env)
                            res, why = '다시 켬', f'자식 세션 {len(kids)}개 끔 · 쉰 지 {int(idle // 60)}분 · rc.log {size / 2 ** 20:.0f}MB → 새로(끝 손잡이)'
                            extra['new'] = p.pid
    d = rc_night_load()                             # 다시 켜는 사이 화면 줄이 바뀌었을 수 있다
    d.update(day=day, at=int(now), result=res, why=why, **extra)
    rc_night_save(d)
    log(f'RC 새벽 {res}: {why}')
    return d


def ping():
    home = config().get('home_wifi') or []
    name = ssid()       # 없으면(유선 등) 집인지 모른다 — «밖»으로 치면 폰이 «PC 밖»을 잘못 띄운다
    return {'ok': True, 'at': now(), **power(), 'home': name in home if home and name else None, 'rc': rc_info(), 'app': app_state(),
            'approve': approve_brief(),     # 폰 승인 대기 {n, oldest, frozen} — 손발 앱 알림 · 폰 홈 단추 배지(11-17)
            'modules': phone_modules()}     # 손발 앱 모듈 켜기 {id: bool}(11-18 · 판 35~ · 옛 앱은 이 칸을 안 읽음)


# ───────── 폰 알림 앱(brain-phone) — 마지막 당김 · 단추(넘김·완료) ─────────
# 11-08~12 폰 Tailscale 이 4일 끊겼는데 아무도 몰랐다(앱 알림은 3일 뒤 조용한 한 줄). 당김을 서버가 적어 두고 ping 에 실어 볼트 상태 줄이 본다.
APP_SEEN = os.path.join(STATE, 'phone-app.json')
APP_LOCK = threading.Lock()
_app = {}
DONE_LOG = os.path.join(HERE, '_index', 'alarms', 'acts.jsonl')
DONE_MAX = 100                                      # 한 번에 받는 «끝냄»(폰이 못 닿는 동안 모은 것)


UNKNOWN_DEVICE = '기기 미상'                         # 기기 머리가 없는 요청(판 24 까지의 앱 · 다른 손님)
_req = threading.local()                            # 지금 요청의 기기(handle_one 이 채운다)


def device_of(raw):
    """X-Brain-Device 머리(앱 판 25~ · 퍼센트 부호 UTF-8 — 폰 이름 «Galaxy S25» 등) → 기록에 쓸 이름. 없거나 꼴이 아니면 «기기 미상»."""
    try:
        name = CTRL.sub(' ', urllib.parse.unquote(raw or '', errors='strict')).strip()[:40]
    except UnicodeDecodeError:
        name = ''
    return name or UNKNOWN_DEVICE


def req_device():
    return getattr(_req, 'device', UNKNOWN_DEVICE)


def ip_of(peer, xff):
    """요청을 보낸 기기의 주소 — 문은 127.0.0.1 에만 열려 있어 밖의 요청은 tailscale serve 가 넘긴다: 그때는 X-Forwarded-For(serve 가 보낸 기기의
    tailnet 주소로 덮어 씀 · tailscale ipn/ipnlocal/serve.go addProxyForwardedHeaders) · 머리가 없으면(시험 대역·PC 안) 맞닿은 주소."""
    if peer in ('127.0.0.1', '::1') and xff:
        first = xff.split(',')[0].strip()
        if re.fullmatch(r'[0-9A-Fa-f.:]{2,45}', first):
            return first
    return peer or ''


def req_ip():
    return getattr(_req, 'ip', '')


def device_here():
    """이 요청의 기기 이름 — 앱은 머리(X-Brain-Device) · 폰 플러그인은 머리가 없어 같은 주소에서 마지막으로 당긴 앱의 기기(한 폰·탭의 앱과 옵시디언 = 같은 tailnet 주소).
    모르면 None(그 기기에 앱이 없거나 이 서버가 켜진 뒤 앱이 아직 안 당김)."""
    d = req_device()
    if d != UNKNOWN_DEVICE:
        return d
    ip = req_ip()
    if not ip:
        return None
    with APP_LOCK:
        if not _app:
            try:
                with open(APP_SEEN, encoding='utf-8') as f:
                    _app.update(json.load(f))
            except (OSError, ValueError):
                pass
        devs = dict(_app.get('devices') or {}) if isinstance(_app.get('devices'), dict) else {}
    got = [(v.get('at') or 0, k) for k, v in devs.items() if isinstance(v, dict) and v.get('ip') == ip and k != UNKNOWN_DEVICE]
    return max(got)[1] if got else None


def app_seen(ver, device=None):
    """앱이 알림 목록을 당겨 간 때·판(X-Brain-App 머리 · 옛 앱은 없음). 재시작해도 남게 파일에도.
    두 기기(폰·탭 · 11-16)는 서로 덮지 않게 기기마다(devices) — 맨 위 at·ver 는 가장 최근 당긴 기기(상태 줄이 읽던 꼴 그대로)."""
    one = {'at': int(time.time() * 1000), 'ver': int(ver) if ver and ver.isdigit() and len(ver) < 8 else None}
    if req_ip():
        one['ip'] = req_ip()                        # 같은 기기의 폰 플러그인을 이 앱과 잇는다(device_here · «이 기기만 끄기»)
    with APP_LOCK:
        if not _app:
            try:
                with open(APP_SEEN, encoding='utf-8') as f:
                    _app.update(json.load(f))
            except (OSError, ValueError):
                pass
        devices = dict(_app['devices']) if isinstance(_app.get('devices'), dict) else {}
        devices[device or UNKNOWN_DEVICE] = one
        rec = {**one, 'device': device or UNKNOWN_DEVICE, 'devices': devices}
        _app.clear()
        _app.update(rec)
        try:
            os.makedirs(STATE, exist_ok=True)
            with open(APP_SEEN + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False)
            os.replace(APP_SEEN + '.tmp', APP_SEEN)
        except OSError:
            pass


def awake_minutes(t0, t1, quiet):
    """t0~t1(ms) 중 잘 시간 밖의 분 — 잘 시간엔 앱이 일부러 안 깨므로 늦음으로 안 센다. 5분 단위 · 14일까지만 센다."""
    q0, q1 = alarms.minutes(quiet[0]), alarms.minutes(quiet[1])
    t, end, n = t0, min(t1, t0 + 14 * 86400000), 0
    while t < end:
        d = datetime.datetime.fromtimestamp(t / 1000, schedule.KST)
        m = d.hour * 60 + d.minute
        if q0 == q1 or not (m >= q0 or m < q1 if q0 > q1 else q0 <= m < q1):
            n += 5
        t += 300000
    return n


def app_state():
    """on = 알림-설정 «켬»(PC 의 «전부 끄기») · 마지막 당김(ms · 한 번도 안 당겼으면 None) · 판 · 그 뒤 깨어 있던 분 · late = 당김을 두 번 넘게 걸렀다(종이 경고 색).
    맨 위 at·ver·late = 가장 최근에 당긴 기기(옛 플러그인이 읽던 꼴 그대로) · here = 이 요청의 기기(device_here) · mute = 그 기기의 «이 기기만 끄기» ·
    me = 그 기기의 at·ver·late(11-17 · 폰 종·공유는 제 기기 앱을 본다)."""
    with APP_LOCK:
        rec = dict(_app)
    if not rec:
        try:
            with open(APP_SEEN, encoding='utf-8') as f:
                rec = json.load(f)
        except (OSError, ValueError):
            rec = {}                                # 한 번도 안 당김 — 종(켬·끔)은 그래도 보여야 한다
        with APP_LOCK:
            _app.update(rec)
    s, _ = alarms.load_settings()
    here = device_here()
    mine = {'here': here, 'mute': muted(here)}

    def late_of(at):
        try:
            awake = awake_minutes(at, int(time.time() * 1000), alarms.quiet_of(s))
        except (TypeError, ValueError):
            return None, False
        return awake, awake > 2 * s['당겨_오기_분'] + 15
    one = (rec.get('devices') or {}).get(here) if here and isinstance(rec.get('devices'), dict) else None
    if isinstance(one, dict):
        mine['me'] = {'at': one.get('at'), 'ver': one.get('ver'), 'late': late_of(one.get('at'))[1]}
    if not rec:
        return {'on': s['켬'], 'at': None, 'ver': None, 'awake_min': None, 'late': False, **mine}
    if 'at' not in rec:
        return {**rec, 'on': s['켬'], 'awake_min': None, 'late': False, **mine}
    awake, late = late_of(rec['at'])
    return {**rec, 'on': s['켬'], 'awake_min': awake, 'late': late, **mine}


MUTE = os.path.join(STATE, 'mute.json')             # 기기별 «이 기기만 끄기»(11-17) — {기기 이름: {"mute": 참거짓, "at": ms}} · 서버 상태 자리(볼트 노트 아님)
MUTE_LOCK = threading.Lock()


def mutes():
    try:
        with open(MUTE, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def muted(device):
    m = mutes().get(device) if device else None
    return bool(isinstance(m, dict) and m.get('mute') is True)


def alarm_mute(b):
    """«이 기기만 끄기»(사용자 11-17 «이 기기만 끄기로, 전부 끄는 것은 컴퓨터에서 할 수 있게.») — 폰·탭 홈 종과 손발 앱 스위치가 같은 값을 읽고 쓴다.
    기기 = 앱은 머리 · 폰 플러그인은 같은 주소의 앱(device_here) · 모르면 409. 끈 기기는 울림만 안 울리고 상태 알림(PC 끊김·설정 틀림·수집 막힘)은 그대로(앱이 가른다).
    «전부 끄기»(알림-설정 «켬»)는 PC 에서 — 이 길은 그 값을 안 건드린다."""
    mute = b.get('mute')
    if not isinstance(mute, bool):
        raise Bad(400, 'mute 는 참거짓')
    dev = device_here()
    if not dev:
        raise Bad(409, '이 기기를 모름 — 이 기기의 외부뇌 앱이 한 번 당긴 뒤')
    with MUTE_LOCK:
        d = mutes()
        d[dev] = {'mute': mute, 'at': int(time.time() * 1000)}
        os.makedirs(STATE, exist_ok=True)
        with open(MUTE + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(MUTE + '.tmp', MUTE)
    log(f'알림 이 기기만 {"끔" if mute else "켬"} · {dev}')
    return {'ok': True, 'mute': mute, 'device': dev, 'on': alarms.load_settings()[0]['켬']}


def alarm_power(b):
    """상태 줄 종(사용자 11-13 안 A · 묻지 않음) — 폰 알림 전부 끔·켬 = 알림-설정 json 의 «켬». 폰은 플러그인이 곧 당기게 한다(brainphone://wake?pull=1)."""
    on = b.get('on')
    if not isinstance(on, bool):
        raise Bad(400, 'on 은 참거짓')
    rel = os.path.relpath(alarms.SETTINGS, VAULT).replace('\\', '/')
    with WRITE:
        try:
            with open(alarms.SETTINGS, encoding='utf-8', newline='') as f:
                text = f.read()
        except OSError:
            raise Bad(404, '알림 설정 노트 없음')
        m = re.search(r'```json[ \t]*\r?\n(.*?)\r?\n```', text, re.S)
        if not m:
            raise Bad(409, '설정 블록 없음')
        block, val = m.group(1), 'true' if on else 'false'
        if re.search(r'"켬"\s*:\s*(true|false)', block):
            new = re.sub(r'("켬"\s*:\s*)(true|false)', lambda x: x.group(1) + val, block, count=1)
        else:
            new = re.sub(r'^\s*\{', lambda x: x.group(0) + f'\n "켬": {val},', block, count=1)
        if new != block:
            write_md(rel, text[:m.start(1)] + new + text[m.end(1):], '폰 상태 줄 종: 알림 ' + ('켬' if on else '끔'), True)
    return {'ok': True, 'on': alarms.load_settings()[0]['켬']}


# ── 앱 안 볼트 설정(11-27 사용자 «볼트의 ui없는 설정파일로 넘어가서 고쳐야하는 것들을 앱 내에서 자체 ui로») ──
# 알림-설정 노트 json 블록의 칸 몇(잘 시간·당김·미리 알림·울릴 일정·바로)과 config.json 의 칸 셋(집 Wi-Fi·민감 노트·일정 쓸 곳).
# 안 다루는 것(사용자 11-27 ✦ 그대로): «켬»(전부 끄기는 PC 에서 · 11-17) · 문 번호·rc_mode·lock_ttl·alarms·push(Claude 몫·보안) · 과목·글자 · 일정별 알림(캘린더).
# 쓰기는 write_md(fileops 바꾸기 = 장부·옛 판 휴지통·되돌리기) · 노트는 블록만 같은 꼴로 다시 씀(글 나머지 그대로) · 값 검사는 alarms.parse_settings 와 같은 규칙.
SETTING_NOW = ('막힘', '옮겨짐', '늦게_앎', '새_공지')
HHMM_RE = re.compile(r'([01]\d|2[0-3]):[0-5]\d')


def _block_dump(d):
    """알림-설정 json 블록 꼴 — 맨 바깥 칸은 한 줄씩 · «파일»만 펼침 · 나머지는 한 줄(사람이 쓴 꼴과 같음 · 11-27 실제 노트 왕복 일치)."""
    out = []
    for k, v in d.items():
        kk = json.dumps(k, ensure_ascii=False)
        if k == '파일' and isinstance(v, dict) and v:
            inner = ',\n'.join(f'  {json.dumps(a, ensure_ascii=False)}: {json.dumps(c, ensure_ascii=False, separators=(", ", ": "))}' for a, c in v.items())
            out.append(f' {kk}: {{\n{inner}\n }}')
        else:
            out.append(f' {kk}: {json.dumps(v, ensure_ascii=False, separators=(", ", ": "))}')
    return '{\n' + ',\n'.join(out) + '\n}'


def _settings_note():
    """(글, 블록 match, 블록 dict) — 노트가 없거나 블록이 깨졌으면 Bad(앱은 «PC 에서»로 보임)."""
    try:
        with open(alarms.SETTINGS, encoding='utf-8', newline='') as f:
            text = f.read()
    except OSError:
        raise Bad(404, '알림 설정 노트 없음')
    m = re.search(r'```json[ \t]*\r?\n(.*?)\r?\n```', text, re.S)
    if not m:
        raise Bad(409, '설정 블록 없음')
    try:
        d = json.loads(m.group(1))
    except ValueError:
        raise Bad(409, '설정 블록이 깨짐 — PC 에서 고침')
    if not isinstance(d, dict):
        raise Bad(409, '설정 블록이 깨짐 — PC 에서 고침')
    return text, m, d


def _sched_files():
    try:
        return sorted(n for n in os.listdir(roles.abs('schedule')) if n.lower().endswith('.md'))
    except OSError:
        return []


def settings_view():
    """GET /v1/settings — 앱 «이 기기 알림»·«연결» 칸이 그리는 값(블록의 날 값 · 잘 시간이 꺼져도 부터·까지는 노트 그대로)."""
    try:
        _, _, d = _settings_note()
        note = None
    except Bad as e:
        d, note = {}, e.msg
    q = d.get('잘_시간') if isinstance(d.get('잘_시간'), dict) else {}
    df = alarms.DEFAULTS
    base = d.get('기본') if isinstance(d.get('기본'), dict) else {}
    files = d.get('파일') if isinstance(d.get('파일'), dict) else {}
    now = d.get('바로') if isinstance(d.get('바로'), dict) else {}
    names = _sched_files()
    rows = []
    for n in names + [n for n in files if n != alarms.ALL_FILES and n not in names]:
        r = files.get(n) if isinstance(files.get(n), dict) else None
        on = (r is not None and not r.get('끔')) or (r is None and alarms.ALL_FILES in files and not (files[alarms.ALL_FILES] or {}).get('끔'))
        rows.append({'name': n, 'on': bool(on), 'days': (r or {}).get('며칠_전'), 'here': n in names})
    c = config()
    home = c.get('home_wifi') if isinstance(c.get('home_wifi'), list) else []
    return {'ok': note is None, 'why': note,
            'quiet': {'on': q.get('켬', True) is not False, 'from': q.get('부터', df['잘_시간']['부터']), 'to': q.get('까지', df['잘_시간']['까지'])},
            'pull': d.get('당겨_오기_분', df['당겨_오기_분']),
            'before': {'days': base.get('며칠_전', df['기본']['며칠_전']), 'times': base.get('시각', df['기본']['시각'])},
            'files': rows,
            'now': {k: now.get(k, df['바로'][k]) is not False for k in SETTING_NOW},
            'wifi': {'list': [str(x) for x in home], 'here': _net.get('ssid') or None if time.time() - _net.get('at', 0) < 600 else None},
            'sensitive': 'hide' if hide_sensitive() else 'show',
            'write': c.get('write_schedule') or '내-일정.md', 'schedules': names}


def _note_set(change, why):
    """블록 dict 를 change(d) 로 고쳐 같은 꼴로 씀 — 새 문제(parse_settings)가 생기면 400 · 같으면 안 씀."""
    with WRITE:
        text, m, d = _settings_note()
        before = alarms.parse_settings(text)[1]
        change(d)
        block = _block_dump(d)
        nl = '\r\n' if '\r\n' in m.group(1) else '\n'
        new_text = text[:m.start(1)] + block.replace('\n', nl) + text[m.end(1):]
        bad = [p for p in alarms.parse_settings(new_text)[1] if p not in before]
        if bad:
            raise Bad(400, bad[0])
        if new_text != text:
            write_md(os.path.relpath(alarms.SETTINGS, VAULT).replace('\\', '/'), new_text, '폰 설정: ' + why, True)


def _conf_set(key, val, why):
    with WRITE:
        try:
            with open(CONFIG, encoding='utf-8') as f:
                c = json.load(f)
        except (OSError, ValueError):
            raise Bad(409, '서버 설정 파일이 깨짐 — PC 에서 고침')
        if c.get(key) == val:
            return
        c[key] = val
        write_md(os.path.relpath(CONFIG, VAULT).replace('\\', '/'), json.dumps(c, ensure_ascii=False, indent=1) + '\n', '폰 설정: ' + why, True)


def settings_post(b):
    """POST /v1/settings {set, value} — 칸 하나를 바꾸고 GET 과 같은 값을 돌려준다."""
    k, v = b.get('set'), b.get('value')
    if k == 'quiet':
        if not isinstance(v, dict) or not all(a in ('on', 'from', 'to') for a in v):
            raise Bad(400, 'quiet = {on, from, to}')
        if 'on' in v and not isinstance(v['on'], bool) or any(a in v and not (isinstance(v[a], str) and HHMM_RE.fullmatch(v[a])) for a in ('from', 'to')):
            raise Bad(400, '잘 시간 값이 잘못됨')

        def ch(d):
            q = d.get('잘_시간') if isinstance(d.get('잘_시간'), dict) else dict(alarms.DEFAULTS['잘_시간'])
            for a, n in (('on', '켬'), ('from', '부터'), ('to', '까지')):
                if a in v:
                    q[n] = v[a]
            d['잘_시간'] = q
        _note_set(ch, '잘 시간 ' + json.dumps(v, ensure_ascii=False))
    elif k == 'pull':
        if type(v) is not int or not 15 <= v <= 1440:
            raise Bad(400, '당김 = 15~1440 분')
        _note_set(lambda d: d.__setitem__('당겨_오기_분', v), f'당김 {v}분')
    elif k == 'before':
        days, times = (v or {}).get('days'), (v or {}).get('times')
        if not (isinstance(days, list) and days and all(type(x) is int and 0 <= x <= 365 for x in days)
                and isinstance(times, list) and times and all(isinstance(x, str) and HHMM_RE.fullmatch(x) for x in times)):
            raise Bad(400, '미리 알림 값이 잘못됨')
        days = sorted(set(days), reverse=True)
        times = sorted(set(times))

        def ch(d):
            base = d.get('기본') if isinstance(d.get('기본'), dict) else {}
            base.update({'며칠_전': days, '시각': times})
            d['기본'] = base
        _note_set(ch, f'미리 알림 {days} {times}')
    elif k == 'file':
        name, on = (v or {}).get('name'), (v or {}).get('on')
        if not isinstance(name, str) or name not in _sched_files() or not isinstance(on, bool):
            raise Bad(400, '일정 파일 값이 잘못됨')

        def ch(d):
            files = d.get('파일') if isinstance(d.get('파일'), dict) else {}
            if alarms.ALL_FILES in files:           # «*» = 전부 → 하나를 바꾸려면 지금 울리는 파일을 낱낱이 적는다
                star = files.pop(alarms.ALL_FILES) or {}
                for n in _sched_files():
                    files.setdefault(n, dict(star))
            r = files.get(name) if isinstance(files.get(name), dict) else {}
            if on:
                r.pop('끔', None)
            else:
                r['끔'] = True
            files[name] = r
            d['파일'] = files
        _note_set(ch, f'울릴 일정 {name} ' + ('켬' if on else '끔'))
    elif k == 'now':
        if not isinstance(v, dict) or not v or not all(a in SETTING_NOW and isinstance(x, bool) for a, x in v.items()):
            raise Bad(400, '바로 알림 값이 잘못됨')

        def ch(d):
            now = d.get('바로') if isinstance(d.get('바로'), dict) else dict(alarms.DEFAULTS['바로'])
            now.update(v)
            d['바로'] = now
        _note_set(ch, '바로 알림 ' + json.dumps(v, ensure_ascii=False))
    elif k == 'wifi':
        c = config()
        home = [str(x) for x in c.get('home_wifi')] if isinstance(c.get('home_wifi'), list) else []
        if v == 'here':
            name = ssid()
            if not name:
                raise Bad(409, 'PC Wi-Fi 를 모름')
            if name not in home:
                home.append(name)
        elif isinstance(v, dict) and isinstance(v.get('remove'), str) and v['remove'] in home:
            home.remove(v['remove'])
        else:
            raise Bad(400, 'wifi = "here" | {remove}')
        _conf_set('home_wifi', home, '집 Wi-Fi')
    elif k == 'sensitive':
        if v != 'hide':                             # 폰에서는 숨기는 쪽만(사용자 11-27 ✦) — 폰을 잃었을 때 숨김을 풀 수 없게. 보이기는 PC 에서
            raise Bad(403, '민감 노트 보이기는 PC 에서')
        _conf_set('phone_sensitive', 'hide', '민감 노트 숨김')
    elif k == 'write':
        if not isinstance(v, str) or v not in _sched_files():
            raise Bad(400, '일정 파일이 아님')
        _conf_set('write_schedule', v, '일정 쓸 곳 ' + v)
    else:
        raise Bad(400, '모르는 설정')
    log(f'설정 {k} ← {json.dumps(v, ensure_ascii=False)[:80]} ({req_device()})')
    return settings_view()


def alarm_act(b):
    """폰 알림 단추(사용자 11-13) — 알림 id(<열쇠>@<마감 날짜>@<종류>) 또는 항목의 key·date 칸으로 그 마감을 찾는다. 못 닿는 동안 폰이 모은 것도 한 번에 온다.
    act = done(완료): 열린 일정 줄을 [x] · skip(넘김): 줄은 그대로, 그 회차만 앞으로 안 울림(alarms.skip · 폰도 스스로 다시 안 건다).
    got = done · skipped · gone(이미 닫혔거나 없음) · bad(꼴이 아님) — 넷 다 폰은 그만 보낸다. 생성 파일 줄도 블록 id 로 체크가 이어진다.
    두 기기(11-16 · 앱 판 25~): ring = 그 울림 id(없으면 id) · ring_at = 울린 때 · act 에 again(다시 · snooze = 새 울림 항목)과 사건 울림의 넘김(줄 없음 → noted)도.
    다른 기기가 그 울림을 먼저 판정했으면 하지 않고 got = already(+ by · act · text «이미 판정됨 · 기기 · 결과» · 그것이 다시였으면 그 새 울림) —
    폰은 카드에서 빼고 제 쪽에서 한 것(넘김 장부·제 «다시»)을 되돌린다. 단추마다 처음 닿은 쪽 = 판정(alarms.ring_claim)."""
    out, rows = [], []
    by = req_device()
    for it in (b.get('items') or [])[:DONE_MAX]:
        it = it if isinstance(it, dict) else {}
        aid = str(it.get('id') or '')[:300]
        ring = str(it.get('ring') or aid)[:300]
        act = it.get('act') or 'done'
        p = aid.split('@')
        key, date = str(it.get('key') or (p[0] if len(p) >= 3 else ''))[:200], str(it.get('date') or (p[1] if len(p) >= 3 else ''))      # 항목의 key·date 칸이 있으면 그것(캘린더 세션이 더함) · 없으면 id 에서
        line_ok = bool(key) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', date))
        ring_at = it.get('ring_at') if isinstance(it.get('ring_at'), int) else None
        ans = {}
        if act not in ('done', 'skip', 'again', 'pick', 'open') or not aid or (act == 'done' and not line_ok):
            got, where = 'bad', None
        else:
            first, rec = alarms.ring_claim(ring, act, by, f'{key}@{date}' if line_ok else None, ring_at, it.get('snooze') if act == 'again' else None)
            act = rec['act'] if first and rec.get('act') in ('done', 'skip', 'again') else act     # 같은 기기의 되풀이 = 처음 한 것을 다시(답을 못 받은 것)
            if not first:                               # 다른 기기가 먼저 — 하지 않는다
                got, where = 'already', None
                ans = {k: v for k, v in alarms.ring_answer(ring, rec, alarms.load_rings()).items() if k in ('by', 'act', 'text', 'snooze')}
            elif act in ('pick', 'open'):               # 폰 앱 판 35~(11-19): 알림 자체 단추 글(답 = value) · 누르면 사라지기 — 판정만(alert.py answer 가 읽음)
                got, where = ('picked' if act == 'pick' else 'opened'), None
            elif act == 'done' and not line_ok:         # 사건 울림에 줄 완료가 남은 경우(같은 기기) — 할 일 없음
                got, where = 'noted', None
            elif act == 'again':                        # 다시 = 판정만(새 울림은 ring_claim 이 장부에 · 목록에 두 기기 같이)
                got, where = 'again', None
            elif act == 'skip' and not line_ok:         # 사건 울림의 넘김 = 판정만(줄이 없다)
                got, where = 'noted', None
            elif act == 'skip':                         # 그 회차만 앞으로 안 울림 — 장부는 알림 모듈 몫(_index/alarms/skips.json · 캘린더가 읽음)
                r = alarms.skip(key, date, str(it.get('title') or '')[:40])
                got, where = ('skipped' if r.get('ok') else 'bad'), None
            else:
                got, where = close_line(key, date)
        out.append({'id': aid, 'ring': ring, 'got': got, **ans})
        rows.append({'at': now(), 'id': aid, 'act': act, 'got': got, 'tapped': it.get('at') if isinstance(it.get('at'), int) else None, 'file': where, 'device': by,
                     **({'ring': ring} if ring != aid else {}), **({'first': ans.get('by'), 'first_act': ans.get('act')} if got == 'already' else {}),
                     **({'value': str(it.get('value') or '')[:500 if it.get('input') else 40]} if act == 'pick' else {}),
                     **({'input': True} if act == 'pick' and it.get('input') is True else {})})
    if rows:
        try:
            os.makedirs(os.path.dirname(DONE_LOG), exist_ok=True)
            with open(DONE_LOG, 'a', encoding='utf-8', newline='\n') as f:
                f.writelines(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows)
        except OSError:
            pass
    return {'ok': True, 'items': out}


def rings_check(b):
    """카드에 떠 있는 울림 가운데 판정된 것(앱 판 25~ · 두 기기) — {items: [{id, at}], wait: 초} → {items: [{id, act, by, at, text, snooze?}]}.
    없으면 wait 초(상한 alarms.RING_WAIT_MAX)까지 붙잡고 있다가 다른 기기가 판정하면 바로 답한다 — 카드가 떠 있는 동안 폰이 «바로» 지우는 길."""
    asked = []
    for it in (b.get('items') or [])[:DONE_MAX]:
        if isinstance(it, dict) and it.get('id'):
            asked.append((str(it['id'])[:300], it.get('at') if isinstance(it.get('at'), int) else None))
    wait = b.get('wait') if isinstance(b.get('wait'), int) else 0
    return {'ok': True, 'items': alarms.rings_wait(asked, wait if asked else 0)}


# ───────── 즉시 알림(11-18 시험판 · 연구 제작자 작업 노트 · 제작 알림-즉시-제작.md) ─────────
# 폰이 POST /v1/push 로 물음을 붙잡아 두면 사건이 나는 순간 답한다. 붙잡을지는 PC 가 정한다(push_policy) — config.json «push»:
#   hold   = off(기본 · 옛 길 그대로) | auto(급함 쓰는 분류 체계가 켜짐 · 승인 적용기와 키가 있음) | always(시험 «늘 붙잡기»)
#   holder = fgs(포그라운드 서비스 · 방식 F) | nls(알림 접근 리스너 · 방식 L) | alt(날짜로 번갈아) | {기기 이름: 방식, "*": 기본}
#   wait   = 붙잡는 초(기본 300 · alarms.PUSH_WAIT_MAX 상한) · probe = {"day": 분, "night": 분}(시험 사건 · 없으면 안 냄) · tick = 살피기 초(기본 5)
# 서버 안 살피기(push_watch): 일정이 바뀌어 울릴 목록이 바뀌면 list · 승인 대기가 늘면 ping · 정책이 바뀌면 깨움 · probe 시각이면 probe.
PUSH_WAIT, PUSH_TICK, PUSH_LIST_EVERY = 300, 5, 10
_push_seen = {}                                     # {기기: {at, holder, st}} — 마지막 /v1/push(살피기를 켤지 · state)
_push_urgent = {"at": (), "v": None}                 # at = 체계 파일 지문


def urgent_systems():
    """켜진 분류 체계 가운데 알림 동작에 «급함»을 쓰는 것(id 들) — 체계 파일(이름·고친 때)이 그대로면 담아 둔 값(켬을 바꾸면 바로 따라감)."""
    out, d = [], os.path.join(HERE, 'sort')
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith('.json'))
        sig = tuple((n, os.stat(os.path.join(d, n)).st_mtime_ns) for n in names)
    except OSError:
        names, sig = [], ()
    if _push_urgent['v'] is not None and _push_urgent['at'] == sig:
        return _push_urgent['v']
    for n in names:
        try:
            with open(os.path.join(d, n), encoding='utf-8') as f:
                s = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(s, dict) or s.get('켬', True) is False:
            continue
        acts = [a for b in (s.get('갈래') or {}).values() if isinstance(b, dict) for a in b.get('동작') or []]
        if any(isinstance(a, dict) and isinstance(a.get('알림'), dict) and a['알림'].get('급함') for a in acts):
            out.append(str(s.get('id') or n[:-5]))
    _push_urgent.update(at=sig, v=out)
    return out


def push_holder(c, dev, today=None):
    h = c.get('holder')
    if isinstance(h, dict):
        h = h.get(dev) or h.get('*')
    if h == 'alt':                                  # 하루씩 번갈아(측정 계획 §6 1단계) — 짝수 날 fgs · 홀수 날 nls
        h = 'fgs' if (today or datetime.date.today()).toordinal() % 2 == 0 else 'nls'
    return h if h in ('fgs', 'nls') else 'fgs'


def push_policy(dev=None):
    """{hold, holder, wait, why} — 이 기기가 지금 물음을 붙잡아 둘지(폰은 이 값대로 방식 F·L 을 켜고 끈다)."""
    c = config().get('push')
    c = c if isinstance(c, dict) else {}
    mode = c.get('hold') if c.get('hold') in ('off', 'auto', 'always') else 'off'
    try:
        wait = max(1, min(int(c.get('wait') or PUSH_WAIT), alarms.PUSH_WAIT_MAX))
    except (TypeError, ValueError):
        wait = PUSH_WAIT
    why = []
    if mode == 'always':
        why = ['늘 붙잡기(시험)']
    elif mode == 'auto':
        u = urgent_systems()
        if u:
            why.append('급함 체계 ' + '·'.join(u[:3]))
        if os.path.isfile(APPROVER) and approve_keys() > 0:
            why.append('승인')
    if not alarms.load_settings()[0]['켬']:
        why = []                                    # 알림 다 끔 = 붙잡을 것 없음
    return {'hold': bool(why), 'holder': push_holder(c, dev or req_device()), 'wait': wait, 'why': ' · '.join(why) or ('끔' if mode == 'off' else '까닭 없음')}


def push_tag(p):
    return f'-p{int(p["hold"])}{p["holder"][0]}{p["wait"]}'


def push_out(e):
    """버스의 사건 → 폰이 받는 꼴(alert = item 내용째 · ping = approve·modules)."""
    return {k: e[k] for k in ('id', 'seq', 'kind', 'at', 'item', 'approve', 'modules') if k in e}


def push_hold(b):
    """POST /v1/push — since 뒤 사건을 바로, 없으면 붙잡음. since 없음 = 지금 seq 만(처음 · 목록을 막 당긴 폰은 /v1/alarms 의 push.seq 를 씀)."""
    dev = req_device()
    since = b.get('since') if type(b.get('since')) is int else 0
    pol = push_policy(dev)
    _push_seen[dev] = {'at': time.time(), 'holder': str(b.get('holder') or '')[:8], 'st': alarms._st(b)}
    if since <= 0:
        return {'ok': True, 'seq': alarms.push_seq(), 'events': [], **pol}
    if not pol['hold']:
        evs, seq = alarms.push_since(since)
        return {'ok': True, 'seq': seq, 'events': [push_out(e) for e in evs], **pol}
    want = b.get('wait') if type(b.get('wait')) is int and b['wait'] > 0 else pol['wait']
    evs, seq = alarms.push_wait(since, min(want, pol['wait']), dev)
    _push_seen[dev] = {**_push_seen.get(dev, {}), 'at': time.time()}
    return {'ok': True, 'seq': seq, 'events': [push_out(e) for e in evs], **push_policy(dev)}


def pc_only():
    if req_ip() not in ('127.0.0.1', '::1'):
        raise Bad(403, 'PC 안에서만')


def push_emit_post(b):
    """POST /v1/push/emit — 알림 도구(alert.py)·시험이 버스에 싣는다. alert = events [{id ev-…, at, title, text?, open?, buttons?, clear_on_open?}] (50개까지)."""
    pc_only()
    kind = b.get('kind')
    held = alarms.push_held()                       # 내기 전 — 이 사건을 바로 받을 기기
    if kind == 'alert':
        evs = b.get('events') if isinstance(b.get('events'), list) else []
        good = [e for e in evs[:50] if isinstance(e, dict) and isinstance(e.get('id'), str) and e['id'].startswith('ev-') and len(e['id']) <= 300
                and type(e.get('at')) is int and isinstance(e.get('title'), str) and isinstance(e.get('text', ''), str) and isinstance(e.get('open', ''), str)
                and alarms.extras_ok(e)]
        if len(good) != len(evs):
            raise Bad(400, '사건 꼴이 틀림(id ev-… · at 정수 ms · title 글)')
        if not alarms.load_settings()[0]['켬']:
            return {'ok': True, 'n': 0, 'why': '알림 다 끔'}
        out = [alarms.push_emit('alert', {'item': {k: str(e[k])[:300] if isinstance(e[k], str) else e[k] for k in ('id', 'at', 'title', 'text', 'open') + alarms.EXTRA_KEYS if k in e}}) for e in good]
    elif kind in ('probe', 'list'):
        out = [alarms.push_emit(kind)]
    else:
        raise Bad(400, 'kind 는 alert · probe · list')
    return {'ok': True, 'n': len(out), 'ids': [e['id'] for e in out], 'seq': alarms.push_seq(), 'held': held}


def push_ack_post(b):
    return alarms.push_ack(b, req_device())


def push_state(_q=None):
    pc_only()
    return {'ok': True, 'seq': alarms.push_seq(), 'held': alarms.push_held(),
            'seen': {k: {**v, 'ago_s': int(time.time() - v.get('at', 0))} for k, v in _push_seen.items()}, 'policy': push_policy('*')}


def push_list_sig():
    """울릴 목록(시각 울림 · 다시 · 판정 뺌)의 지문 — 일정·설정·일정별·넘김이 바뀌면 바뀐다(재기 probe 와 사건은 뺌 · 사건은 alert 가 따로)."""
    got = alarms.build(config().get('alarms'))
    items = [a for a in got['items'] if not str(a.get('id', '')).startswith('probe-')]
    return hashlib.sha1(json.dumps([items, got.get('quiet'), got.get('pull_minutes')], ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def push_probe_next(c, now_t, rnd):
    """다음 probe 시각(초) — 잘 시간이면 night 분 · 아니면 day 분 · 0.5~1.5배로 흩음(아무 분 · 계획 §6). 없으면 None."""
    p = c.get('probe') if isinstance(c.get('probe'), dict) else None
    if not p:
        return None
    s = alarms.load_settings()[0]
    d = datetime.datetime.fromtimestamp(now_t, schedule.KST)
    q0, q1, m = alarms.minutes(s['잘_시간']['부터']), alarms.minutes(s['잘_시간']['까지']), d.hour * 60 + d.minute
    night = q0 != q1 and ((m >= q0 or m < q1) if q0 > q1 else (q0 <= m < q1))
    try:
        every = float(p.get('night' if night else 'day') or 0)
    except (TypeError, ValueError):
        every = 0
    return now_t + every * 60 * (0.5 + rnd()) if every > 0 else None


def push_watch(stop=None):
    """서버 안 살피기(PUSH_TICK 초마다) — 붙잡는 기기가 있을 때만 목록 지문·승인 수를 잰다(없으면 거의 0)."""
    import random
    last = {'sig': None, 'list': None, 'appr': None, 'list_at': 0.0, 'probe': None}
    while not (stop and stop.is_set()):
        c = config().get('push')
        c = c if isinstance(c, dict) else {}
        try:
            tick = max(0.5, float(c.get('tick') or PUSH_TICK))
        except (TypeError, ValueError):
            tick = PUSH_TICK
        time.sleep(tick)
        if c.get('hold', 'off') == 'off' and not _push_seen and not c.get('probe'):
            continue                                # 즉시 알림을 안 씀 — 아무것도 안 잰다
        try:
            pol = push_policy('*')
            sig = (pol['hold'], pol['wait'], tuple(sorted((k, push_holder(c, k)) for k in _push_seen)))
            if last['sig'] is not None and sig != last['sig']:
                alarms.push_kick()                  # 붙잡힌 물음이 새 정책을 바로 받는다
            last['sig'] = sig
            t = time.time()
            active = bool(alarms.push_held()) or any(t - v.get('at', 0) < 900 for v in _push_seen.values())
            if not active:
                last.update(list=None, appr=None)   # 다시 붙잡을 때 새로 잰다(그 폰은 목록을 막 당겼다)
            elif t - last['list_at'] >= min(PUSH_LIST_EVERY, max(tick, 1)):
                last['list_at'] = t
                h = push_list_sig()
                if last['list'] is not None and h != last['list']:
                    alarms.push_emit('list')
                    log('즉시 알림: 목록 바뀜 → list')
                last['list'] = h
                n = approve_count()[0]
                if last['appr'] is not None and n != last['appr']:   # 줄 때도(PC 붙임·만료·거둠·다른 기기 승인 · 11-21)
                    approve_forget()
                    alarms.push_emit('ping', {'approve': approve_brief(), 'modules': phone_modules()})
                last['appr'] = n
            if last['probe'] is None:
                last['probe'] = push_probe_next(c, t, random.random)
            elif t >= last['probe']:
                alarms.push_emit('probe')
                last['probe'] = push_probe_next(c, t, random.random)
            elif not c.get('probe'):
                last['probe'] = None
        except Exception as e:  # noqa: BLE001 — 살피기가 서버를 멈추지 않게
            log(f'즉시 알림 살피기 오류 {type(e).__name__}: {e}')


def close_line(key, date):
    """열쇠(alarms.key_of)가 같은 열린 줄 — 마감 날짜도 같은 줄 먼저, 없으면 열쇠만 같은 줄이 하나일 때(그 사이 날짜가 옮겨진 줄)."""
    with WRITE:
        rows = [(f, ln, m) for f, _, ln, m in schedule.parse_all() if m and m.group(1) == ' ' and alarms.key_of(m) == key]
        pick = [r for r in rows if r[2].group(2) == date] or (rows if len(rows) == 1 else [])
        if not pick:
            return 'gone', None
        f, ln, _ = pick[0]
        with open(f, encoding='utf-8', newline='') as fh:
            ls = fh.read().splitlines(keepends=True)      # 줄마다 제 줄끝 그대로(LF·CRLF 섞여도)
        i = next((i for i, x in enumerate(ls) if x.rstrip('\r\n') == ln), -1)
        if i < 0:
            return 'gone', None
        ls[i] = re.sub(r'^(\s*- \[) (\])', r'\g<1>x\g<2>', ls[i], count=1)
        write_atomic(f, ''.join(ls))
        return 'done', os.path.relpath(f, VAULT).replace('\\', '/')


# ───────── 일정 ─────────
def schedule_rows(days):
    today = datetime.date.today()
    until = today + datetime.timedelta(days=days)
    out = []
    for f, _, ln, m in schedule.parse_all():
        if not m:
            continue
        try:
            d = datetime.date.fromisoformat(m.group(2))
        except ValueError:
            continue
        if d < today or d > until:
            continue
        out.append({'date': m.group(2), 'time': m.group(3), 'end': m.group(4), 'done': m.group(1) in 'xX', 'text': schedule.clean(m.group(5)),
                    'file': os.path.relpath(f, VAULT).replace('\\', '/'), 'line': ln, 'id': m.group(6)})
    out.sort(key=lambda r: (r['date'], r['time'] or '99:99', r['text']))
    return out


def insert_sorted(text, line, key):
    """calendar 플러그인의 insertSorted 와 같은 자리 — 첫 일정 묶음(다음 «#» 머리 전까지) 안에서 날짜·시각 순."""
    nl = '\r\n' if '\r\n' in text else '\n'
    ls = text.split(nl)
    first = next((i for i, x in enumerate(ls) if schedule.LINE.match(x)), -1)
    if first < 0:
        return text.rstrip() + nl + nl + line + nl
    end, i = first, first
    while i < len(ls) and not re.match(r'#{1,6} ', ls[i]):
        if schedule.LINE.match(ls[i]):
            end = i
        i += 1
    at = end + 1
    for i in range(first, end + 1):
        m = schedule.LINE.match(ls[i])
        if m and f'{m.group(2)} {m.group(3) or "99:99"}' > key:
            at = i
            break
    ls.insert(at, line)
    return nl.join(ls)


def write_atomic(a, text):
    tmp = a + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    os.replace(tmp, a)


# ───────── 책갈피(11-18 · 계획 제작자 작업 노트 §4.4·§4.5) ─────────
# 기기마다 파일 하나 — PC = brain-base(pc.json) · 폰·탭 = 이 문이 그 기기 이름으로 · 한 파일을 둘이 안 쓰니 잠금이 없다(이 문 안의 차례만 지킨다).
# 손 책갈피 = 모든 기기 파일의 marks 합 − gone(지운 때가 더한 때보다 뒤) · 마지막 본 곳 = 기기마다 칸 · 옮김 = 장부 mv·rename(적은 때 뒤의 것만).
MARKS = os.path.join(HERE, '_index', 'work', '책갈피')
MARK_DEV = re.compile(r'[A-Za-z0-9_-]{1,24}')
MARK_POS_MAX = 4096
MARK_KEEP_MS = 90 * 864e5
_marks_lock = threading.Lock()
_mk_ledger = {'key': None, 'moves': []}


def marks_dev(raw):
    d = str(raw or '').strip()
    if not MARK_DEV.fullmatch(d) or d.lower() == 'pc':
        raise Bad(400, '기기 이름이 잘못됨')
    return d


def marks_read(a):
    try:
        with open(a, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or d.get('v') != 1:
        return None
    return {'v': 1, 'dev': str(d.get('dev') or ''), 'marks': [m for m in d.get('marks') or [] if isinstance(m, dict)],
            'gone': [g for g in d.get('gone') or [] if isinstance(g, dict)], 'last': d.get('last') if isinstance(d.get('last'), dict) else {}}


def mark_moves():
    """장부의 옮김(파일·폴더) — 바뀔 때만 다시 읽는다"""
    a = os.path.join(HERE, 'ledger', 'ops.jsonl')
    try:
        st = os.stat(a)
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        return []
    if key == _mk_ledger['key']:
        return _mk_ledger['moves']
    out = []
    with open(a, encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('op') not in ('mv', 'rename', 'rm', 'restore', 'rmdir') or not isinstance(r.get('src'), str) or not isinstance(r.get('dst'), str):
                continue
            try:
                ts = datetime.datetime.fromisoformat(r.get('ts')).timestamp() * 1000
            except (TypeError, ValueError):
                ts = 0
            out.append((ts, r['src'].replace('\\', '/'), r['dst'].replace('\\', '/'), r.get('kind') == 'folder' or r.get('op') == 'rmdir'))
    _mk_ledger.update(key=key, moves=out)
    return out


def mark_follow(p, since):
    cur = p
    for ts, src, dst, folder in mark_moves():
        if ts and ts + 1000 < since:
            continue
        if cur == src:
            cur = dst
        elif folder and cur.startswith(src + '/'):
            cur = dst + cur[len(src):]
    return cur


def marks_doc(q):
    rel, a = clean(q.get('path'))
    if phone_hidden(a):
        raise Bad(403, '이 자리는 안 됨')
    dev = marks_dev(q.get('dev'))
    files = []
    try:
        names = sorted(n for n in os.listdir(MARKS) if n.endswith('.json'))
    except OSError:
        names = []
    for n in names:
        d = marks_read(os.path.join(MARKS, n))
        if d:
            files.append(d)
    gone = {}
    for d in files:
        for g in d['gone']:
            gone[g.get('id')] = max(gone.get(g.get('id'), 0), g.get('at') or 0)
    marks, seen, last = [], set(), []
    for d in files:
        for m in d['marks']:
            mid, at = m.get('id'), m.get('at') or 0
            if not mid or mid in seen or gone.get(mid, -1) >= at or not isinstance(m.get('path'), str):
                continue
            if mark_follow(m['path'], at) == rel:
                seen.add(mid)
                marks.append({'id': mid, 'at': at, 'name': str(m.get('name') or ''), 'pos': m.get('pos') or {'k': 'none'}, 'dev': d['dev']})
        for p, l in d['last'].items():
            if isinstance(l, dict) and l.get('pos') and mark_follow(p, l.get('at') or 0) == rel:
                last.append({'dev': d['dev'], 'at': l.get('at') or 0, 'name': str(l.get('name') or ''), 'pos': l['pos'], 'mine': d['dev'] == dev})
    return {'path': rel, 'dev': dev, 'marks': marks, 'last': sorted(last, key=lambda x: -x['at'])}


def marks_post(b):
    dev = marks_dev(b.get('dev'))
    op = b.get('op')
    rel, a = clean(b.get('path'))
    if phone_hidden(a):
        raise Bad(403, '이 자리는 안 됨')
    now_ms = int(time.time() * 1000)
    pos = b.get('pos')
    if op in ('add', 'last'):
        if not isinstance(pos, dict) or len(json.dumps(pos, ensure_ascii=False)) > MARK_POS_MAX:
            raise Bad(400, '자리가 잘못됨')
    name = CTRL.sub(' ', str(b.get('name') or ''))[:200]
    with _marks_lock:
        os.makedirs(MARKS, exist_ok=True)
        f = os.path.join(MARKS, f'{dev}.json')
        d = marks_read(f) or {'v': 1, 'dev': dev, 'marks': [], 'gone': [], 'last': {}}
        d['dev'] = dev
        out = {'ok': True}
        if op == 'add':
            mid = str(b.get('id') or '') or (format(now_ms, 'x') + secrets.token_hex(2))
            if not MARK_DEV.fullmatch(mid):
                raise Bad(400, 'id 가 잘못됨')
            if len(d['marks']) >= 5000:
                raise Bad(413, '책갈피가 너무 많음')
            d['marks'] = [m for m in d['marks'] if m.get('id') != mid] + [{'id': mid, 'path': rel, 'at': int(b.get('at') or now_ms), 'name': name, 'pos': pos}]
            out['id'] = mid
        elif op == 'del':
            mid = str(b.get('id') or '')
            if not mid:
                raise Bad(400, 'id 없음')
            d['marks'] = [m for m in d['marks'] if m.get('id') != mid]
            d['gone'] = [g for g in d['gone'] if now_ms - (g.get('at') or 0) < MARK_KEEP_MS] + [{'id': mid, 'at': now_ms}]
        elif op == 'last':
            d['last'][rel] = {'at': int(b.get('at') or now_ms), 'name': name, 'pos': pos}
            d['last'] = {k: v for k, v in d['last'].items() if isinstance(v, dict) and now_ms - (v.get('at') or 0) < MARK_KEEP_MS}
        else:
            raise Bad(400, 'op 가 잘못됨')
        write_atomic(f, json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    return out


def add_schedule(b):
    d, t, e, text = b.get('date') or '', b.get('time') or '', b.get('end') or '', ' '.join((b.get('text') or '').split())
    try:
        day = datetime.date.fromisoformat(d)
    except ValueError:
        raise Bad(400, '날짜가 잘못됨')
    if not text or (t and not re.fullmatch(r'\d{1,2}:\d{2}', t)) or (e and not re.fullmatch(r'\d{1,2}:\d{2}', e)) or (e and not t):
        raise Bad(400, '시각·내용이 잘못됨')
    line = f'- [ ] {d} ({WD[day.weekday()]})' + (f' {t}' + (f'~{e}' if e else '') if t else '') + f' {text}'
    if not schedule.LINE.match(line):
        raise Bad(400, '일정 줄이 안 됨')
    a = os.path.join(roles.abs('schedule'), config().get('write_schedule', '내-일정.md'))
    with WRITE:
        with open(a, encoding='utf-8', newline='') as f:
            old = f.read()
        if line not in old.splitlines():            # 응답을 못 받은 폰이 또 보내면 한 줄만
            write_atomic(a, insert_sorted(old, line, f'{d} {t or "99:99"}'))
    return {'ok': True, 'line': line}


def check_schedule(b):
    rel, a = clean(b.get('file'), (roles.path('schedule') + '/',))
    want = b.get('line')
    done = 'x' if b.get('done') else ' '
    if not want or not os.path.isfile(a):
        raise Bad(400, '일정 줄이 없음')
    with WRITE:
        with open(a, encoding='utf-8', newline='') as f:
            text = f.read()
        nl = '\r\n' if '\r\n' in text else '\n'
        ls = text.split(nl)
        if want not in ls:
            raise Bad(409, '그 줄이 바뀌었음')
        ls[ls.index(want)] = re.sub(r'^(\s*- \[)[ xX](\])', rf'\g<1>{done}\g<2>', want, count=1)
        write_atomic(a, nl.join(ls))
    return {'ok': True}


# ───────── 폰 캘린더 — 줄 병합(데스크톱 우선) ─────────
GEN_HEAD = re.compile(r'^tags:.*생성파일|^# .*\(생성 파일\)', re.M)     # 캘린더 read() 와 같은 판별 — 생성기가 다시 쓰는 파일
TICK = re.compile(r'^(\s*- \[)[ xX](\].*)$')


def tick_only(a, b):
    """두 줄이 체크 칸만 다른가."""
    ma, mb = TICK.match(a), TICK.match(b)
    return bool(ma and mb) and ma.group(1) == mb.group(1) and ma.group(2) == mb.group(2)


def find_block(ls, block, near):
    """ls 에서 block(이어진 줄 여럿)이 나오는 자리 — 여럿이면 near 에 가까운 것 · 없으면 -1."""
    n = len(block)
    hits = [i for i in range(len(ls) - n + 1) if ls[i:i + n] == block]
    return min(hits, key=lambda i: abs(i - near)) if hits else -1


def anchor(ls, base, i, near):
    """새 줄을 넣을 자리 — base 에서 바로 앞 줄 뒤(그 줄이 PC 에도 있으면) · 아니면 바로 뒤 줄 앞 · 둘 다 없으면 끝."""
    if i > 0:
        at = find_block(ls, [base[i - 1]], near - 1)
        if at >= 0:
            return at + 1
    if i < len(base):
        at = find_block(ls, [base[i]], near)
        if at >= 0:
            return at
    return len(ls) if i else 0


def merge_lines(base, mine, cur, ticks_only=False):
    """폰이 base → mine 으로 바꾼 줄 묶음만 cur(PC 지금 판)에 얹는다(diff3 꼴 · 줄 단위).
    폰이 고친 줄이 PC 에서도 바뀌었으면(그 줄이 cur 에 그대로 없으면) PC 판을 둔다 — 데스크톱 우선(사용자 11-13).
    PC 에도 이미 같은 고침이 있으면(응답을 못 받고 다시 보낸 글) 아무것도 안 한다.
    ticks_only = 생성 파일 — 체크 칸만 바꾼 묶음만 얹는다(생성기가 블록 id 로 체크를 이어받고 다른 손질은 다시 쓸 때 사라진다).
    → (줄들, 얹은 묶음 수, 버린 묶음 수)"""
    out = list(cur)
    took = dropped = shift = 0
    gone = {i for tag, i1, i2, _, _ in difflib.SequenceMatcher(None, base, cur, autojunk=False).get_opcodes() if tag == 'delete' for i in range(i1, i2)}   # PC 가 지운 줄
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, mine, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        # 같은 수의 줄을 바꾼 묶음은 줄마다 — 이웃한 두 줄 중 하나만 PC 와 겹치면 그 줄만 PC 판
        one = tag == 'replace' and i2 - i1 == j2 - j1
        for i, old, new in ([(i1 + k, base[i1 + k:i1 + k + 1], mine[j1 + k:j1 + k + 1]) for k in range(i2 - i1)] if one else [(i1, base[i1:i2], mine[j1:j2])]):
            near = i + shift
            if ticks_only and not (len(old) == len(new) and all(map(tick_only, old, new))):
                dropped += 1
                continue
            if old:
                at = find_block(out, old, near)
                if at < 0:
                    same = find_block(out, new, near) >= 0 if new else all(k in gone for k in range(i, i + len(old)))
                    dropped += not same             # PC 가 그 줄을 먼저 바꿈 — PC 판 · (same = PC 도 같은 고침)
                    continue
                out[at:at + len(old)] = new
            else:
                if find_block(out, new, near) >= 0 and find_block(base, new, 0) < 0:
                    continue                        # 다시 보낸 같은 넣기
                at = anchor(out, base, i, near)
                out[at:at] = new
            shift += len(new) - len(old)
            took += 1
    return out, took, dropped


def union_lines(mine, cur, ticks_only=False):
    """기준 판 없는 폰 글(mine)을 PC 지금 판(cur)에 얹는다 — PC 에 없는 «일정 줄»만 넣는다(폰 글에서 바로 앞에 있던 줄 뒤 · 없으면 마지막 일정 줄 뒤).
    기준 판이 없으면 폰이 무엇을 바꿨는지 알 수 없다. 그대로 merge_lines 에 넘기면 폰 글 전체가 «새 줄»이 되어 파일이 통째로 한 번 더 들어간다(11-24 내-일정 겹침).
    머리·설명 줄과 체크 칸만 다른 줄은 PC 판(데스크톱 우선) · 생성 파일(ticks_only)은 아무것도 안 넣는다.
    → (줄들, 넣은 줄 수, 버린 줄 수)"""
    out, have = list(cur), set(cur)
    took = dropped = 0
    prev = None                                     # 폰 글에서 바로 앞의 일정 줄 중 PC 판에도 있는 것
    for k, line in enumerate(mine):
        if not schedule.LINE.match(line):
            continue
        if line in have:
            prev = line
            continue
        twin = next((c for c in out if tick_only(line, c)), None)
        if ticks_only or twin is not None:
            dropped += 1
            prev = twin or prev
            continue
        if prev is not None:
            at = out.index(prev) + 1
        else:
            nxt = next((m for m in mine[k + 1:] if m in have and schedule.LINE.match(m)), None)   # 앞 줄이 없으면 폰 글의 뒤 줄 앞
            last = [i for i, c in enumerate(out) if schedule.LINE.match(c)]
            at = out.index(nxt) if nxt is not None else last[-1] + 1 if last else len(out) - (1 if out and not out[-1] else 0)
        out.insert(at, line)
        have.add(line)
        prev = line
        took += 1
    return out, took, dropped


def merge_schedule(b):
    """폰 캘린더의 고침 — {path, base, text}: 폰이 본 판(base 글)에서 폰 글(text)로 바뀐 줄만 PC 지금 판에 얹는다(merge_lines).
    폰은 일정 파일을 통째로 쓰지 않는다(그 사이 PC 의 새 줄·생성기 손질이 사라지지 않게). 반복 규칙이 바뀌면 반복 일정도 다시 편다(schedule.repeat).
    → {text = 얹은 뒤 PC 판, etag, took, dropped} · PC 에서 없어진 파일 = 404(폰이 버림 칸에 남긴다)."""
    folder = roles.path('schedule') + '/'
    rel, a = clean(b.get('path'), (folder,))
    name = rel[len(folder):]
    if not name or '/' in name or not name.lower().endswith('.md'):
        raise Bad(403, '이 자리는 안 됨')
    base, text = b.get('base'), b.get('text')
    if not isinstance(base, str) or not isinstance(text, str):
        raise Bad(400, '내용 없음')
    split = lambda s: s.replace('\r\n', '\n').split('\n')    # noqa: E731
    with WRITE:
        if os.path.isfile(a):
            with open(a, encoding='utf-8', newline='') as f:
                cur = f.read()
        elif base:
            raise Bad(404, 'PC 에 없음')
        else:
            cur = ''                                # 폰 캘린더가 처음 만든 파일(내-일정·반복-규칙)
        nl = '\r\n' if '\r\n' in cur else '\n'
        gen = bool(GEN_HEAD.search(cur[:800]))
        if cur.strip() and not base.strip():        # PC 에 파일이 있는데 폰에 기준 판이 없음(새 기기 · 옛 장부) — 통째로 끼워 넣지 않고 없는 일정 줄만
            ls, took, dropped = union_lines(split(text), split(cur), gen)
            log(f'폰 캘린더 {name} 기준 판 없음 — 없는 일정 줄만 넣음')
        else:
            ls, took, dropped = merge_lines(split(base), split(text), split(cur), gen)
        out = nl.join(ls)
        if out != cur:
            write_atomic(a, out)
            if name == schedule.RULE_FILE:
                try:
                    schedule.repeat()
                except Exception as e:              # 규칙 파일은 들어갔다 — 펼침은 다음 schedule.py 차례에
                    log(f'반복 펼침 실패 {type(e).__name__} {e}')
    log(f'폰 캘린더 {name} 얹음 {took} 버림 {dropped}')
    return {'ok': True, 'text': out, 'etag': etag_of(a) if os.path.isfile(a) else '', 'took': took, 'dropped': dropped}


# ───────── 쓰기 — 장부에 남는다 ─────────
def ctx():
    return fileops.Ctx(VAULT, by='phone')


def write_md(rel, text, why, replace, own=False):
    """own = 폰이 만든 받은함 md — fileops 는 1_수집 덮어쓰기를 지시 없이는 막으므로 사용자 결정(⑥)을 그 표시로 넘긴다. 옛 판은 휴지통."""
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, os.path.basename(rel))
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        c = ctx()
        if replace:
            fileops.op_replace(c, tmp, rel, why, user_asked=own)
        else:
            fileops.op_cp(c, tmp, rel, why, dup_ok=True, quiet=True)
        if c.events:
            fileops.write_view(c)


def new_stem(name):
    """폰 새 노트 이름 → 받은함 바로 아래 새 md 의 이름. 폴더·위로 나가기·숨은 스트림·예약 이름·너무 긴 이름은 막는다."""
    stem = name[:-3] if name.lower().endswith('.md') else name
    if not stem or '/' in stem or '\\' in stem or len(stem) > 120 or RESERVED.fullmatch(stem):
        raise Bad(400, '이름이 잘못됨')
    inbox = roles.path('inbox') + '/'
    clean(inbox + stem + '.md', (inbox,))
    return stem


def memo(b):
    text = (b.get('text') or '').strip()
    if not text:
        raise Bad(400, '빈 메모')
    name = b.get('name')
    if name is not None:
        if not isinstance(name, str):
            raise Bad(400, '이름이 잘못됨')
        if SENSITIVE.search(text[:4096]):
            raise Bad(403, '민감 노트는 폰에서 만들지 않음')
        stem, why = new_stem(name), '폰 새 노트'
    else:
        at = b.get('at') or ''                      # 보낼 함을 거치면 적은 때와 보낸 때가 다르다
        stem, why = '폰메모 ' + (at if re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{6}', at) else time.strftime('%Y-%m-%d %H%M%S')), '폰 메모'
    with WRITE:
        n = 1
        while True:                                 # 보낼 함을 비우면 한 초에 여러 개가 온다 · 있는 파일은 덮어쓰지 않는다
            rel = roles.path('inbox') + '/' + stem + (f' {n}' if n > 1 else '') + '.md'
            a = os.path.join(VAULT, *rel.split('/'))
            if not os.path.exists(a):
                break
            with open(a, encoding='utf-8', errors='replace') as f:
                if f.read() == text + '\n':         # 응답을 못 받은 폰이 또 보냄
                    return {'ok': True, 'path': rel}
            n += 1
        write_md(rel, text + '\n', why, False)
    return {'ok': True, 'path': rel}


_diag = {'day': '', 'n': 0}


def diag(b):
    """폰에서만 보이는 일(상태 전환 · 오류 · 망 종류)을 서버 로그로 — 폰 시험을 로그로 판정한다. 한 번 줄 수 · 한 줄 길이 · 하루 줄 수에 상한."""
    lines = b.get('lines')
    if not isinstance(lines, list):
        raise Bad(400, '줄 없음')
    day = time.strftime('%Y-%m-%d')
    if _diag['day'] != day:
        _diag.update(day=day, n=0)
    full = _diag['n'] >= DIAG_DAY
    kept = lines[:max(0, min(DIAG_LINES, DIAG_DAY - _diag['n']))]
    for x in kept:
        log('폰 ' + CTRL.sub(' ', str(x))[:DIAG_CHARS] + ('' if req_device() == UNKNOWN_DEVICE else f' · {req_device()}'))     # 두 기기(11-16): 줄 끝에 보낸 기기
    _diag['n'] += len(kept)
    if not full and _diag['n'] >= DIAG_DAY:
        log('폰 진단 하루 상한 — 나머지는 버림')
    return {'ok': True, 'kept': len(kept)}


def md_for_write(path):
    rel, a = clean(path, WRITE_ROOTS)
    if not rel.lower().endswith('.md'):
        raise Bad(400, 'md 만')
    if rel.startswith(roles.path('schedule') + '/'):
        raise Bad(403, '일정 파일은 일정 칸으로')     # 생성 파일은 다시 쓰이면 손질이 사라진다
    return rel, a


def phone_made(rel):
    """장부로 판별 — 폰이 들인 파일인가."""
    try:
        with open(os.path.join(HERE, 'ledger', 'ops.jsonl'), encoding='utf-8') as f:
            for ln in f:
                if '"phone"' in ln and rel in ln:
                    d = json.loads(ln)
                    if d.get('by') == 'phone' and d.get('dst') == rel:
                        return True
    except (OSError, ValueError):
        pass
    return False


def own_inbox(path):
    """받은함 바로 아래에서 폰이 만든 md 만 고친다 — 다른 받은함 파일은 폰에서 읽기 전용. 받은함이 아니면 None."""
    inbox = roles.path('inbox') + '/'
    if not ((path or '').replace('\\', '/').strip('/') + '/').startswith(inbox):
        return None
    rel, a = clean(path, (inbox,))
    if '/' in rel[len(inbox):] or not rel.lower().endswith('.md'):
        raise Bad(403, '이 자리는 안 됨')
    if os.path.isfile(a) and not phone_made(rel):
        raise Bad(403, '폰이 만든 노트만')
    return rel, a


def note(b):
    own = own_inbox(b.get('path'))
    rel, a = own or md_for_write(b.get('path'))
    if not os.path.isfile(a):
        raise Bad(404, '없음')
    if phone_hidden(a):
        raise Bad(403, '민감 노트')
    with WRITE:
        with open(a, 'rb') as f:
            try:
                f.read().decode('utf-8')
            except UnicodeDecodeError:
                raise Bad(403, 'UTF-8 아닌 노트')       # 폰은 깨진 글자로 받았으므로 그대로 돌아오면 본문이 상한다
        cur = etag_of(a)
        if cur != b.get('base'):
            raise Bad(409, 'PC 판이 바뀜', etag=cur)      # PC 우선 — 폰 수정은 버린다
        text = b.get('text')
        if not isinstance(text, str):
            raise Bad(400, '내용 없음')
        was = sensitive(a)                              # 판(etag)을 맞춘 뒤 잰다
        if was and not SENSITIVE.search(fm_of(re.sub(r'\r\n?', '\n', text[:4096]))):
            raise Bad(403, '민감 표시는 폰에서 못 뗌')     # 떼면 다음 자동 커밋이 그 노트를 git 에 넣는다 — 떼기는 PC 에서
        if not was and SENSITIVE.search(text[:4096]):
            raise Bad(403, '민감 노트는 폰에서 만들지 않음')
        write_md(rel, text, '폰에서 고침', True, own=bool(own))
        return {'ok': True, 'etag': etag_of(a)}


# ───────── 열린 노트 지켜보기 · 고치는 중 잠금(11-17 사용자 «모바일에서 수정 중이라면 다른 기기에서의 수정을 막고») ─────────
# 폰·탭이 노트에 입력하면 그 노트의 «고치는 중»을 올린다(심장박동 · 마지막 입력 뒤 lock_ttl 초에 저절로 풀림 · 닫음·뒤로 감은 바로 풂).
# 서버는 그 표를 locks.json 에도 둔다 — Claude 의 Edit·Write 훅이 그 파일을 먼저 보고(없으면 바로 통과) 걸릴 때만 /v1/locks 로 서버에 다시 묻는다
# (서버가 꺼졌으면 막지 않음). 데스크톱 옵시디언은 그 파일로 그 노트를 읽기 전용으로 둔다. 쓰기 길(/v1/note 등)은 막지 않는다 — 잠금은 표시·훅용.
LOCKS_FILE = os.path.join(STATE, 'locks.json')
LOCK_TTL = 120              # 기본 · config lock_ttl(30~600초)로 바꿈 — 폰 md 편집 간격 기록이 아직 없어 잰 값 아님(작업 노트 11-17)
LOCK_MAX = 50               # 한 번에 걸린 잠금 상한(기기 둘 · 넉넉히)
WATCH_MAX = 25              # 지켜보기 붙잡는 상한(초) — rings 20초처럼 tailscale serve 를 거쳐도 끊기지 않는 길이
WATCH_STEP = 0.5            # 붙잡는 동안 파일 판을 보는 간격
WATCH_FILES = 12            # 한 번에 지켜보는 노트 수(열린 탭)
_locks = {}                 # rel → {id, label, at, until}
_wgen = {}                  # 기기 id → 지켜보기 차례 — 같은 기기가 새로 걸면 옛 요청은 곧 끝낸다(열린 노트가 바뀔 때마다 붙잡힌 요청이 쌓여 연결을 잡아먹지 않게)
LOCKS_LOCK = threading.Lock()


def lock_ttl():
    v = config().get('lock_ttl')
    return v if isinstance(v, int) and 30 <= v <= 600 else LOCK_TTL


def _locks_save(now):
    """살아 있는 잠금만 파일로(임시 파일 → 바꿔 끼움) — 훅·데스크톱이 읽는다. 못 써도 서버는 그대로 돈다."""
    live = {k: v for k, v in _locks.items() if v['until'] > now}
    _locks.clear()
    _locks.update(live)
    try:
        os.makedirs(STATE, exist_ok=True)
        write_atomic(LOCKS_FILE, json.dumps({'v': 1, 'items': {k: {'label': v['label'], 'id': v['id'], 'at': int(v['at']), 'until': int(v['until'])} for k, v in live.items()}}, ensure_ascii=False))
    except OSError as e:
        log(f'잠금 표 못 씀 {type(e).__name__}')


def _locks_load():
    """서버를 다시 켜도 아직 안 풀린 잠금은 그대로(파일에서)."""
    try:
        with open(LOCKS_FILE, encoding='utf-8') as f:
            items = json.load(f).get('items') or {}
    except (OSError, ValueError, AttributeError):
        return
    now = time.time()
    for k, v in items.items():
        if isinstance(v, dict) and isinstance(v.get('until'), (int, float)) and v['until'] > now and v.get('id'):
            _locks[k] = {'id': str(v['id']), 'label': str(v.get('label') or '폰'), 'at': v.get('at') or now, 'until': v['until']}


def lock_target(path):
    own = own_inbox(path)
    return own or md_for_write(path)


def lock(b):
    """POST /v1/lock {path, on, id, label} — on = 입력 중(심장박동 · 마지막 입력 뒤 ttl 초 = 풀림) · off = 풂(닫음·뒤로 감).
    다른 기기가 먼저 잡았으면 {ok: false, held: {label, left}} — 먼저 고친 기기가 이긴다."""
    rel, _ = lock_target(b.get('path'))
    who = str(b.get('id') or '')[:64]
    if not who:
        raise Bad(400, '기기 id 없음')
    label = CTRL.sub(' ', str(b.get('label') or '')).strip()[:20] or '폰'
    now = time.time()
    ttl = lock_ttl()
    with LOCKS_LOCK:
        cur = _locks.get(rel)
        if cur and cur['until'] > now and cur['id'] != who:
            return {'ok': False, 'held': {'label': cur['label'], 'left': int(cur['until'] - now)}, 'ttl': ttl}
        if b.get('on'):
            if not cur or cur['until'] <= now:
                if sum(1 for v in _locks.values() if v['until'] > now) >= LOCK_MAX:
                    raise Bad(429, '잠금이 너무 많음')
                log(f'잠금 켬 · {label} · {ttl}초')
            _locks[rel] = {'id': who, 'label': label, 'at': cur['at'] if cur and cur['id'] == who and cur['until'] > now else now, 'until': now + ttl}
        elif cur:
            del _locks[rel]
            log(f'잠금 풂 · {label} · {int(now - cur["at"])}초 동안')
        _locks_save(now)
        until = _locks[rel]['until'] if rel in _locks else None
    return {'ok': True, 'ttl': ttl, 'until': int(until * 1000) if until else None}


def locks_now(rels=None, who=''):
    now = time.time()
    with LOCKS_LOCK:
        return [{'path': k, 'label': v['label'], 'left': max(0, int(v['until'] - now)), 'mine': bool(who) and v['id'] == who}
                for k, v in sorted(_locks.items()) if v['until'] > now and (rels is None or k in rels)]


def locks_get(q):
    """GET /v1/locks — 지금 걸린 잠금(훅이 묻는다 · 폰 C1 이 보일 수 있다)."""
    return {'items': locks_now(), 'ttl': lock_ttl()}


def watch(b):
    """POST /v1/watch {items: [{path, etag}], id, sig, wait} — 폰·탭이 열어 둔 노트의 PC 판·잠금을 지켜본다.
    판이 폰이 본 것(etag)과 다르거나 그 노트들의 잠금 꼴(sig)이 바뀌면 바로 · 아니면 wait 초(상한 WATCH_MAX)까지 붙잡는다.
    → {items: [{path, etag | gone}], locks: [{path, label, left, mine}], sig}. 노트 경로·글은 로그에 안 적는다."""
    asked = []
    for it in (b.get('items') or [])[:WATCH_FILES]:
        if not isinstance(it, dict):
            continue
        try:
            rel, a = clean(it.get('path'), READ_ROOTS)
        except Bad:
            continue
        asked.append((rel, a, str(it.get('etag') or '')))
    who = str(b.get('id') or '')[:64]
    seen = str(b.get('sig') or '')
    with LOCKS_LOCK:
        my = _wgen[who] = _wgen.get(who, 0) + 1 if who else 0
    wait = b.get('wait') if isinstance(b.get('wait'), int) else 0
    end = time.time() + max(0, min(wait, WATCH_MAX))
    rels = {r for r, _, _ in asked}
    while True:
        out = []
        for rel, a, tag in asked:
            try:
                cur = None if phone_hidden(a) else etag_of(a)
            except OSError:
                cur = None
            if cur != tag:
                to = moved_to(rel) if cur is None else None
                out.append({'path': rel, 'gone': True, **({'moved': to} if to else {})} if cur is None else {'path': rel, 'etag': cur})
        locks = locks_now(rels, who)
        sig = '|'.join(f"{x['path']}:{x['label']}:{int(x['mine'])}" for x in locks)
        if who and _wgen.get(who) != my:
            return {'items': [], 'locks': locks, 'sig': seen, 'stale': True}     # 같은 기기가 새로 걸었다
        if out or sig != seen or time.time() >= end:
            return {'items': out, 'locks': locks, 'sig': sig}
        time.sleep(WATCH_STEP)


INK_MAX = 8 * 2**20                                # 한 번에 받는 필기 줄 글 상한


def ink_id(line):
    """필기 머리 줄의 정체(id) — 머리 줄이 아니거나 못 읽으면 None"""
    try:
        r = json.loads(line)
    except ValueError:
        return None
    return str(r.get('id', '')) if isinstance(r, dict) and r.get('note') == 1 else None


def ink_key(line):
    """필기 줄의 이름 — 머리 note · page:<id> · s:<획> · o:<기록> · 못 읽으면 None(src/ink/format.ts keyOf 와 같음)."""
    try:
        r = json.loads(line)
    except ValueError:
        return None
    if not isinstance(r, dict):
        return None
    if r.get('note') == 1:
        return 'note'
    for k, pre in (('page', 'page:'), ('s', 's:'), ('o', 'o:')):
        if isinstance(r.get(k), str):
            return pre + r[k]
    return None


INK_PAIR = ('1_수집/',)  # mf:allow-path  (PDF 원본 위 필기의 짝 = 원본 옆 «<이름> (필기).note» · 본체 brain-source pairs.ts 규칙을 복사한 것 · 11-18 필기 13차 · 사용자 «짝메모처럼 같은 곳에»)
INK_PAIR_TAG = ' (필기).note'


def ink_path(p):
    """필기 덧붙이기 자리 — 쓰기 자리(WRITE_ROOTS) · 또는 원본 층 안 원본 옆 필기 짝(«<이름> (필기).note» · 옆에 «<이름>.pdf» 가 있을 때만 · 원본 파일은 못 씀)."""
    s = (p or '').replace('\\', '/').strip('/')
    if (s + '/').startswith(INK_PAIR) and s.endswith(INK_PAIR_TAG):
        rel, a = clean(s, INK_PAIR)
        stem = a[:-len(INK_PAIR_TAG)]
        d, base = os.path.split(stem)
        try:
            names = os.listdir(d)
        except OSError:
            names = []
        if not any(n.lower() == (base + '.pdf').lower() and os.path.isfile(os.path.join(d, n)) for n in names):
            raise Bad(403, '옆에 원본 PDF 가 없음')
        return rel, a
    return clean(p, WRITE_ROOTS)


def ink(b):
    """필기 노트 덧붙이기(필기 설계 §7) — 폰이 아직 안 보낸 줄만 온다. 이미 있는 이름은 건너뛴다(두 기기 합치기 · 같은 줄 두 번 와도 한 벌).
    바탕 PDF 원본은 읽지도 쓰지도 않는다. 없는 파일은 머리 줄부터 새로 만든다(장부 = 폰에서 새 필기).
    원본 위 필기의 짝(1_수집 안 «<이름> (필기).note» · 필기 13차)도 여기로 — ink_path."""
    rel, a = ink_path(b.get('path'))
    if not rel.lower().endswith('.note'):
        raise Bad(400, '.note 만')
    lines = b.get('lines')
    if not isinstance(lines, list) or not all(isinstance(x, str) and '\n' not in x and '\r' not in x for x in lines):
        raise Bad(400, '줄이 잘못됨')
    if sum(len(x) for x in lines) > INK_MAX:
        raise Bad(413, '너무 큼')
    # 보내온 노트 정체 — 요청의 id(탭 0.7.21~) · 없으면 보내온 머리 줄의 id
    nid = b.get('id') if isinstance(b.get('id'), str) else None
    if nid is None:
        nid = next((ink_id(x) for x in lines if ink_key(x) == 'note'), None)
    with WRITE:
        have, n, pid = set(), 0, None
        exists = os.path.isfile(a)
        if exists:
            with open(a, encoding='utf-8', errors='replace') as f:
                for ln in f:
                    if ln.strip():
                        n += 1
                        k = ink_key(ln)
                        if k:
                            have.add(k)
                        if k == 'note' and pid is None:
                            pid = ink_id(ln)
            if nid is not None and pid is not None and nid != pid:
                # 같은 자리에 다른 필기(지운 자리에 새로 만들었는데 PC 에 다른 필기가 남음 등) — 섞으면 되돌리기 어렵다 → 덧붙이지 않음 · 탭이 새 이름으로 다시(11-16 보스 결정)
                raise Bad(409, '같은 자리에 다른 필기', need='rename')
        add = []
        for ln in lines:
            k = ink_key(ln)
            if not k or k in have:
                continue
            have.add(k)
            add.append(ln)
        if not exists:
            if not add or ink_key(add[0]) != 'note':
                raise Bad(400, '새 필기는 머리 줄부터', need='all')   # 탭: 이 필기의 «보낸 줄» 기록을 비우고 머리 줄부터 다 다시(11-16 · 같은 자리에 새로 만든 필기가 머리 줄을 빼고 와 33번 막힘)
            write_md(rel, '\n'.join(add) + '\n', '폰에서 새 필기', False)
        elif add:
            with open(a, 'a', encoding='utf-8', newline='') as f:
                f.write('\n'.join(add) + '\n')
        return {'ok': True, 'etag': etag_of(a), 'lines': n + len(add), 'took': len(add)}


def bin_for_write(path):
    """폰 보기가 고친 원본의 자리 — 있는 파일만(새로 만들지 않는다) · 고칠 수 있는 형식만 · 숨은 자리(_lms·_색인) 안 됨."""
    rel, a = clean(path, BIN_ROOTS)
    if any(p.lower() in HIDE_PART for p in rel.split('/')):     # 윈도는 대소문자를 안 가린다(_LMS = _lms)
        raise Bad(403, '이 자리는 안 됨')
    if os.path.splitext(rel)[1][1:].lower() not in BIN_EXTS:
        raise Bad(400, '이 형식은 안 됨')
    if not os.path.isfile(a):
        raise Bad(404, '없음')
    return rel, a


def put_file(rel, a, base, data):
    """원본 덮기(PC 우선) — 폰이 본 판(base = ETag)과 지금 판이 다르면 409 · 옛 판은 휴지통(fileops · 장부 by=phone · 되돌리기)."""
    if not data:
        raise Bad(400, '빈 파일로 안 덮음')
    with WRITE:
        cur = etag_of(a)
        if cur != base:
            raise Bad(409, 'PC 판이 바뀜', etag=cur)
        with tempfile.TemporaryDirectory() as d:
            tmp = os.path.join(d, os.path.basename(rel))
            with open(tmp, 'wb') as f:
                f.write(data)
            c = ctx()
            try:
                fileops.op_replace(c, tmp, rel, '폰에서 고침', user_asked=rel.startswith('1_수집/'))  # mf:allow-path  (폰이 원본을 보고 고친 원본을 휴지통 거쳐 덮음 · 사용자 결정 · mobility 작업 F)
            except fileops.Stop as e:
                raise Bad(409, str(e))
            finally:
                if c.events:
                    fileops.write_view(c)
        if c.events:
            _undo.add(c.batch)
        log(f'폰 원본 고침 {len(data)}B 묶음 {c.batch if c.events else "같은 내용"}')
        return {'ok': True, 'etag': etag_of(a), **({'batch': c.batch} if c.events else {})}


def upload_name(name):
    """공유로 받은 파일 이름 → 받은함 바로 아래 이름. 폴더·위로 나가기·숨은 이름·예약 이름·끝 점/공백·너무 긴 이름은 막는다(확장자는 가리지 않음)."""
    if not isinstance(name, str):
        raise Bad(400, '이름이 잘못됨')
    name = unicodedata.normalize('NFC', name.strip())
    if (not name or '/' in name or '\\' in name or name.startswith('.') or name != name.rstrip(' .') or len(name) > 150
            or BAD_PART.search(name) or RESERVED.fullmatch(name)):
        raise Bad(400, '이름이 잘못됨')
    return name


_up = {}                                            # 조각 열쇠 → {lock, sock, h, n} — 한 조각엔 한 연결 · 해시를 이어 가서 이어 받을 때 다시 읽지 않는다
_up_lock = threading.Lock()
_up_done = {}                                       # (이름, sha256, 크기) → 받은함 경로 — 응답을 못 받은 폰이 다시 물으면 다시 안 보내게(서버가 도는 동안 · 최근 50)


def upload_args(q):
    """sha256 · size · offset. sha256 + size 가 조각 이름(같은 내용이면 같은 조각에 잇는다) — 없으면 이어 받기 없이 한 번에."""
    sha = (q.get('sha256') or '').lower()
    try:
        size = int(q['size']) if q.get('size') not in (None, '') else None
        off = int(q.get('offset') or 0)
    except ValueError:
        raise Bad(400, '크기가 잘못됨')
    if (size is not None and size < 0) or off < 0 or (sha and not SHA_HEX.fullmatch(sha)):
        raise Bad(400, '크기가 잘못됨')
    return sha, size, off


def up_room(need):
    """받을 자리 — 받고 나서 PC 에 UP_MARGIN 보다 적게 남으면 507(폰이 «PC 저장 공간 부족»을 띄우고 버린다)."""
    os.makedirs(UP_DIR, exist_ok=True)
    free = shutil.disk_usage(UP_DIR).free
    if free - max(need, 0) < UP_MARGIN:
        raise Bad(507, 'PC 저장 공간 부족', free=free, need=need, margin=UP_MARGIN)


def up_sweep():
    """이어 보내지 않고 UP_KEEP 넘게 멈춘 조각을 지운다(받는 중인 것은 두고)."""
    try:
        names = os.listdir(UP_DIR)
    except OSError:
        return
    for n in names:
        a = os.path.join(UP_DIR, n)
        e = _up.get(n[:-5])
        try:
            if time.time() - os.path.getmtime(a) > UP_KEEP and not (e and e['lock'].locked()):
                os.remove(a)
        except OSError:
            pass


def upload_status(q):
    """GET /v1/upload — 이어 보낼 자리 {have} · 이미 받은함에 넣은 것이면 {path, same} · 남은 것을 받을 자리가 없으면 507."""
    sha, size, _ = upload_args(q)
    if not sha or size is None:
        raise Bad(400, '해시·크기 없음')
    up_sweep()
    if q.get('name'):
        rel = _up_done.get((upload_name(q['name']), sha, size, q.get('to') or ''))
        a = rel and os.path.join(VAULT, *rel.split('/'))
        if a and os.path.isfile(a) and os.path.getsize(a) == size:
            return {'ok': True, 'path': rel, 'sha256': sha, 'same': True, 'have': size}
    key = f'{sha}-{size}'
    part = os.path.join(UP_DIR, key + '.part')
    e = _up.get(key)
    have = e['n'] if e and e['lock'].locked() and e['n'] >= 0 else (os.path.getsize(part) if os.path.isfile(part) else 0)   # 받는 중이면 쓴 만큼
    up_room(size - have)
    return {'ok': True, 'have': have}


INK_ATT = '2_지식/필기/_첨부/'                         # mf:allow-path  (필기 첨부 자리 = 본체 brain-source ink 규칙을 복사한 것 · 계약 목록 «복사한 규칙») · 필기에 넣는 사진·PDF 자리(11-16 · 탭 기기 파일) — 받은함은 Claude 가 비우는 정거장이라 안 씀
INK_OUT = '0_작업/필기/'                             # mf:allow-path  (옛 필기 «PDF 로 볼트에 저장» 자리 — brain-source 0.36.38 까지의 폰이 보냄 · 받기만 남김)
OUT_RE = re.compile(r'0_작업/(배움|일|생활|분야)/[^/]+/(?:[^/]+/)*')   # mf:allow-path  (내보낸 PDF 자리 = 본체 brain-source outdir.ts 규칙 «0_작업/<영역>/<주제>/…» 를 복사한 것 · 11-23 폰 PDF) · 같은 이름은 옛 판을 휴지통 거쳐 덮음


def upload_dir(to):
    """올릴 자리 — to 가 필기 첨부 자리 아래면 그 폴더(볼트 상대 · 끝 /) · 내보낸 PDF 자리(OUT_RE · 옛 INK_OUT) · 없으면 받은함. 그 밖은 403."""
    if not to:
        return roles.path('inbox') + '/'
    to = unicodedata.normalize('NFC', str(to)).strip('/') + '/'
    if to == INK_OUT:
        return to
    if OUT_RE.fullmatch(to):
        clean(to + 'x', ('0_작업/',))               # 위로 나가기·숨은 이름·끝 점 막음
        return to
    if not to.startswith(INK_ATT):
        raise Bad(403, '이 자리는 안 됨')
    clean(to + 'x', (INK_ATT,))                     # 위로 나가기·숨은 이름·끝 점 막음
    return to


def upload_finish(name, part, hx, want, to=None):
    """다 받은 조각 → 받은함 새 파일(사용자 11-16 «공유하기에서 볼트 선택하면 받은함으로»). 덮지 않는다 — 같은 이름이 있으면 «이름 (2).확장자».
    받은 바이트 그대로(장부 by=phone · 되돌리기 = 휴지통). want = 폰이 잰 sha256(다르면 400). 응답을 못 받은 폰이 또 보내면 한 벌(같은 이름 줄기 · 같은 내용).
    조각은 받은함과 같은 드라이브라 이름만 바꿔 옮긴다(큰 파일도 다시 쓰지 않는다)."""
    size = os.path.getsize(part)
    if not size or (want and want != hx):
        os.remove(part)
        raise Bad(400, '빈 파일' if not size else '받은 바이트가 다름(sha256)')
    inbox = upload_dir(to)
    if inbox == INK_OUT or OUT_RE.fullmatch(inbox):
        return upload_replace(name, part, hx, size, to, inbox)
    stem, ext = os.path.splitext(name)
    with WRITE:
        n = 1
        while True:
            rel, a = clean(inbox + (f'{stem} ({n}){ext}' if n > 1 else name), (inbox,))
            if not os.path.exists(a):
                break
            if os.path.isfile(a) and os.path.getsize(a) == size and fileops.sha256(a) == hx:
                os.remove(part)
                break
            n += 1
        same = os.path.exists(a)
        if not same:
            c = ctx()
            try:
                os.makedirs(os.path.dirname(a), exist_ok=True)
                fileops.op_cp(c, part, rel, '폰 공유 받음' if not to else '필기에 넣음(탭)', dup_ok=True, move=True, quiet=True, src_label='phone:' + name)
            except fileops.Stop as e:
                raise Bad(409, str(e))
            finally:
                if c.events:
                    fileops.write_view(c)
        _up_done[(name, hx, size, to or '')] = rel
        while len(_up_done) > 50:
            _up_done.pop(next(iter(_up_done)))
    if same:
        return {'ok': True, 'path': rel, 'sha256': hx, 'same': True}
    _home['v'] = None                               # 홈 «받은함» 칸이 새 파일을 바로 보게
    log(f'폰 공유 받음 {size}B → 받은함')
    return {'ok': True, 'path': rel, 'sha256': hx}


def upload_replace(name, part, hx, size, to, out=INK_OUT):
    """폰 «PDF 로 볼트에 저장»·«PDF 로 내보내기»(필기 11-18 · 노트·표 11-23) — out/<이름> 에 둔다. 같은 이름이 있으면 옛 판을 휴지통에 두고 덮는다
    (데스크톱이 같은 자리를 덮는 것과 같게 · 장부 by=phone · 되돌리기). 같은 내용이면 그대로(same) · 응답을 못 받은 폰이 또 보내도 한 벌."""
    rel, a = clean(out + name, (out,))
    with WRITE:
        if os.path.isfile(a) and os.path.getsize(a) == size and fileops.sha256(a) == hx:
            os.remove(part)
            _up_done[(name, hx, size, to)] = rel
            return {'ok': True, 'path': rel, 'sha256': hx, 'same': True}
        c = ctx()
        try:
            os.makedirs(os.path.dirname(a), exist_ok=True)
            if os.path.exists(a):
                fileops.op_rm(c, rel, '덮어쓰기 전 옛 판: PDF 로 볼트에(폰)', user_asked=True, quiet=True)
            fileops.op_cp(c, part, rel, 'PDF 로 볼트에(폰)', dup_ok=True, move=True, quiet=True, src_label='phone:' + name)
        except fileops.Stop as e:
            raise Bad(409, str(e))
        finally:
            if c.events:
                fileops.write_view(c)
        _up_done[(name, hx, size, to)] = rel
        while len(_up_done) > 50:
            _up_done.pop(next(iter(_up_done)))
    log(f'PDF 받음 {size}B → {out}')
    return {'ok': True, 'path': rel, 'sha256': hx}


PDF_MAX = 64 * 2 ** 20                              # 폰이 보내는 HTML 한 장 상한(그림은 data: 로 안에)
PDF_LOCK = threading.Lock()                         # 브라우저 한 번에 하나(메모리)


def make_pdf(q, raw):
    """POST /v1/pdf?name=<이름>.pdf&to=<0_작업/<영역>/<주제>/…> · 본문 = 폰이 그린 HTML(UTF-8) → 이 PC 가 PDF 로 인쇄(pdfprint · 창 없음)
    → 그 자리에 둔다(같은 이름은 옛 판을 휴지통 거쳐 덮음 · upload_replace 와 같음) → {path}. 폰은 받아 열거나 공유한다."""
    name = upload_name(q.get('name'))
    if not name.lower().endswith('.pdf'):
        raise Bad(400, '이름이 잘못됨')
    out = upload_dir(q.get('to'))
    if not OUT_RE.fullmatch(out):
        raise Bad(403, '이 자리는 안 됨')
    try:
        html = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise Bad(400, 'UTF-8 아님')
    if not html.strip():
        raise Bad(400, '빈 문서')
    os.makedirs(UP_DIR, exist_ok=True)
    part = os.path.join(UP_DIR, 'pdf-' + secrets.token_hex(8) + '.part')
    try:
        with PDF_LOCK:
            pdfprint.html_to_pdf(html, part)
    except subprocess.TimeoutExpired:
        raise Bad(504, 'PDF 만들기 시간 넘음')
    except RuntimeError as e:
        raise Bad(500, str(e))
    size = os.path.getsize(part)
    log(f'PDF 만듦 {len(raw)}B HTML → {size}B')
    return upload_replace(name, part, fileops.sha256(part), size, q.get('to'), out)


def new_note(b):
    rel, a = md_for_write(b.get('path'))
    text = b.get('text')
    if not isinstance(text, str):
        raise Bad(400, '내용 없음')
    with WRITE:
        if os.path.exists(a):
            raise Bad(409, '이미 있음')
        write_md(rel, text, '폰에서 새 노트', False)
        return {'ok': True, 'etag': etag_of(a)}


# ───────── 읽기 ─────────
def listing(path):
    if not path:
        return {'dir': '', 'items': [{'name': r.rstrip('/'), 'dir': True} for r in READ_ROOTS], 'desk': desk()}
    rel, a = clean(path)
    if not os.path.isdir(a):
        raise Bad(404, '폴더 아님')
    birth = desk()['sort'].startswith('ctime')     # 만듦 순일 때만 만든 때를 싣는다
    items = []
    with os.scandir(a) as it:
        for e in it:
            if e.name.startswith('.') or e.name in HIDE_PART or e.name.endswith('.tmp'):
                continue
            if e.is_dir(follow_symlinks=False):
                items.append({'name': e.name, 'dir': True})
            elif e.is_file(follow_symlinks=False):
                fm = front(e.path)
                if SENSITIVE.search(fm) and hide_sensitive():
                    continue
                st = e.stat()
                x = {'name': e.name, 'size': st.st_size, 'mtime': round(st.st_mtime, 3)}     # 소수 = 데스크톱 «수정 최근» 정렬과 같은 자리까지
                t = title_of(fm)
                if t:
                    x['title'] = t
                if birth:
                    x['ctime'] = round(getattr(st, 'st_birthtime', st.st_ctime), 3)
                items.append(x)
    items.sort(key=lambda x: (not x.get('dir'), x['name']))
    return {'dir': rel, 'items': items}


_desk = {'at': 0, 'v': None}
_reg = {'mt': -1.0}


def fresh_topics():
    """서버는 오래 돈다 — 주제 등록부(2_지식/주제.md)가 바뀌었으면 roles 의 기억을 비운다(topic.py 도 같은 기억을 쓴다 · 새 주제가 폰에 재시작 없이 보이게)."""
    try:
        mt = os.path.getmtime(roles.abs('topics'))
    except (OSError, KeyError):
        mt = None
    if mt != _reg['mt']:
        _reg['mt'] = mt
        core_api.topics_reset()


def obsidian_json(rel, default):
    try:
        with open(os.path.join(VAULT, '.obsidian', *rel.split('/')), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def pair_memo(name, files):
    """원본 옆 짝 메모(`이름.md` · `이름 (확장자).md`) — 데스크톱 «파일» 탭은 원본 줄이 대신해 숨긴다(brain-base tree.ts pairOf 와 같은 판정)."""
    if not name.endswith('.md'):
        return False
    m = re.fullmatch(r'(.*) \(([^()]+)\)', name[:-3])
    for c in files:
        cb, ce = c.rsplit('.', 1) if '.' in c else (c, '')
        if c != name and ce != 'md' and (cb == name[:-3] or (m and cb == m.group(1) and ce.lower() == m.group(2).lower())):
            return True
    return False


def inbox_count(rel):
    """데스크톱 «파일» 탭 맨 위 «받은함» 줄의 수 — `_`·점·짝 메모 뺌(민감은 «hide» 일 때만 뺀다 · 그때 폰에 안 보이므로)."""
    d = os.path.join(VAULT, *rel.split('/')) if rel else ''
    try:
        names = os.listdir(d) if d else []
    except OSError:
        return 0
    files = [n for n in names if os.path.isfile(os.path.join(d, n))]
    return sum(1 for n in names if not n.startswith(('_', '.')) and not n.endswith('.tmp') and not pair_memo(n, files) and not phone_hidden(os.path.join(d, n)))


def desk():
    """폰 «파일» 서랍이 데스크톱 «파일» 탭(brain-base tree.ts)과 같게 그리는 값 — 역할 자리 · 주제 자리·등록부 · 탐색기 설정(정렬·이름) · 캘린더 켜짐 · 받은함 수. 10초 캐시."""
    if _desk['v'] is not None and time.time() - _desk['at'] < DESK_TTL:
        return _desk['v']
    fresh_topics()
    cfg = roles.config()
    r = cfg.get('roles') or {}
    bb = obsidian_json('plugins/brain-base/data.json', {})
    v = {'roles': {k: r[k] for k in ('inbox', 'schedule', 'knowledge', 'sources', 'source_index', 'system', 'work', 'sessions', 'modules', 'open_loops', 'recent', 'profile', 'topics', 'retention') if r.get(k)},
         'topic_roots': cfg.get('topic_roots') or [],
         'topics': [{k: t[k] for k in ('이름', '별칭', '영역', '학기', '상태') if t.get(k)} for t in roles.topics()],
         'sort': bb.get('treeSort') or 'name',
         'titles': bb.get('treeTitles') is not False,
         'calendar': 'brain-calendar' in obsidian_json('community-plugins.json', []),
         'inbox_n': inbox_count(r.get('inbox'))}
    _desk.update(at=time.time(), v=v)
    return v


_home = {'at': 0, 'v': None}
_fly = {}                               # 도는 계산(열쇠 → 끝 신호·값)
_fly_lock = threading.Lock()
_warm = {'ping': 0.0, 'topics': [], 'busy': False}
WARM_GAP, WARM_TOPICS = 90, 3           # 핑 사이가 이보다 길면 앱을 켬·앞으로 옴(켜 둔 동안은 60초마다) · 미리 계산할 최근 주제 수


def once(key, fn):
    """같은 계산이 돌고 있으면 새로 시작하지 않고 그 결과를 기다린다(핑 때 미리 계산하던 것 · 폰 요청이 겹칠 때). 60초를 넘기면 따로 계산한다."""
    with _fly_lock:
        job = _fly.get(key)
        mine = job is None
        if mine:
            job = _fly[key] = {'done': threading.Event(), 'v': None, 'err': None}
    if not mine:
        if not job['done'].wait(60):
            return fn()
        if job['err'] is not None:
            raise job['err']
        return job['v']
    try:
        job['v'] = fn()
        return job['v']
    except Exception as e:
        job['err'] = e
        raise
    finally:
        with _fly_lock:
            _fly.pop(key, None)
        job['done'].set()


def warm_soon():
    """앱을 켬·앞으로 옴(앞 핑과 90초 넘게 떨어진 핑) → 곧 올 홈·최근 주제 카드 요청을 뒤에서 미리 계산한다(11-12 · 홈 0.5~2.6초 · 주제 0.2~6초를 폰이 기다렸다).
    캐시 시간은 그대로 — 더 낡은 값을 주지 않는다. 이미 돌면 안 띄운다. 켜 둔 동안의 60초 핑에는 안 한다."""
    now_, gap = time.time(), time.time() - _warm['ping']
    _warm['ping'] = now_
    if gap < WARM_GAP or _warm['busy']:
        return
    _warm['busy'] = True

    def run():
        try:
            fresh_topics()
            phone_home()
            for n in list(_warm['topics']):
                card_of(n)
        except Exception as e:  # noqa: BLE001 — 미리 계산은 멈춰도 된다(요청 때 다시 계산)
            log(f'미리 계산 {type(e).__name__}')
        finally:
            _warm['busy'] = False
    threading.Thread(target=run, daemon=True).start()


def phone_home():
    """폰 홈(안 3 · 사용자 11-06) — 데스크톱 홈(brain.py home_data) 가운데 폰이 그리는 칸(받은함·제안 · 작업 · 주제 · 수집)만 같은 부품으로 잰다.
    볼트 밖 · 사라짐 · 휴지통 · 장부는 PC 일이라 안 잰다(볼트 밖 파일 이름도 안 나간다 · 모바일볼트 분류표 ③) · 민감은 뺀다 · 1분 캐시."""
    if _home['v'] is not None and time.time() - _home['at'] < HOME_TTL:
        return _home['v']
    return once('home', build_home)


def build_home():
    fresh_topics()
    topic = core_api.topic()
    today = datetime.datetime.now(topic.KST).date()
    d = roles.abs('inbox')
    inbox = []
    for p in sorted(p for p in os.listdir(d) if not p.startswith(('.', '_'))) if os.path.isdir(d) else []:
        a = os.path.join(d, p)
        if p.endswith('.tmp') or phone_hidden(a):
            continue
        x = {'name': p, 'days': int((time.time() - os.path.getmtime(a)) / 86400)}
        if os.path.isdir(a):
            x['dir'] = True
        inbox.append(x)
    up = topic.upcoming(today)
    topics = []
    for t in roles.topics():
        nxt = next((x for x in up if x['topic'] == t['이름']), None)
        mt = max([os.path.getmtime(f) for _, p in topic.topic_dirs(t) for f in topic.walk_files(os.path.join(VAULT, *p.split('/')))] or [0])
        topics.append({'이름': t['이름'], '영역': t.get('영역'), '상태': t.get('상태'),
                       'next': {k: nxt[k] for k in ('date', 'wd', 'time', 'end', 'text', 'days')} if nxt else None, 'mtime': mt or None})
    try:
        import work
        wk = [{k: w.get(k) for k in ('path', 'topic', 'state', 'missing', 'idle')} for w in work.status()
              if (w['path'] + '/').startswith(READ_ROOTS) and not phone_hidden(os.path.join(VAULT, *w['path'].split('/')))]
    except Exception as e:  # noqa: BLE001 — 홈은 멈추지 않는다
        log(f'홈 작업 {type(e).__name__}')
        wk = None
    try:                                                # 받은함 제안(데스크톱 홈과 같은 부품 · 옮기지 않고 잼) — 폰 줄 단추
        import inbox as inbox_mod
        cx = fileops.Ctx(VAULT, by='phone', dry=True)
        for x in inbox[:8]:
            s = inbox_mod.classify_one(x['name'], cx)
            x.update({k: s[k] for k in ('act', 'dst', 'sure') if s.get(k)})
    except Exception as e:  # noqa: BLE001 — 제안이 깨져도 홈은 그린다
        log(f'홈 받은함 제안 {type(e).__name__}')
    v = {'today': today.isoformat(), 'inbox': {'path': roles.path('inbox'), 'count': len(inbox), 'items': inbox[:8]}, 'work': wk, 'topics': topics,
         'collect': collect_rows()}
    _home.update(at=time.time(), v=v)
    return v


def collect_rows():
    """홈 «수집» 칸 — 데스크톱 홈과 같은 줄(열린 대기열 빨강 + 출처별 마지막 실행 · brain.py) · 보기만. 못 읽으면 None(칸 안 그림)."""
    try:
        import brain
        acts = {x['id']: x for x, _ in brain.load_actions()[0]}
        runs = brain.last_runs()
        return brain.collect_alerts() + [{'name': acts.get(i, {}).get('name', i), 'ts': runs[i].get('ts'), 'code': runs[i].get('code')}
                                         for i in sorted(runs) if i.startswith('collect.')]
    except Exception as e:  # noqa: BLE001 — 홈은 멈추지 않는다
        log(f'홈 수집 {type(e).__name__}')
        return None


# ───────── 모듈 화면 · 파일 형식 화면(보기 전용 · 모바일볼트 ④ 4-1·4-2) ─────────
# 폰이 주는 것은 고를 화면(module·id)과 형식 파일 경로뿐 — 돌리는 명령은 볼트 선언(views.json · 켜진 모듈 module.json) 그대로다.
# 선언 규칙 = brain-base modview.ts·formatview.ts(코어 = .claude/skills/·3_시스템/ 안 · 모듈 = 제 폴더 안 · 형식 = 3_시스템/ 안 · {py} 로 시작).
VIEW_TTL = 20
VIEW_ID = re.compile(r'[A-Za-z0-9_-]{1,64}')
_views = {}


def decl_file(p, roots):
    return isinstance(p, str) and p.startswith(roots) and '\\' not in p and ':' not in p and '..' not in p.split('/') \
        and os.path.isfile(os.path.join(VAULT, *p.split('/')))


def decl_cmd(d, roots):
    return isinstance(d, list) and len(d) >= 2 and d[0] == '{py}' and all(isinstance(x, str) for x in d) and decl_file(d[1], roots)


def view_decls():
    """(모듈 화면 [{module,id,name,icon,html,data}], 형식 화면 [{ext,name,icon,html,data}]) — 코어 먼저 · 같은 module/id·ext 는 처음 것만."""
    try:
        with open(os.path.join(HERE, 'views.json'), encoding='utf-8') as f:
            j = json.load(f)
    except (OSError, ValueError):
        j = {}
    if not isinstance(j, dict) or j.get('schema') != 1:
        j = {}
    out, fmts = [], []
    core = ('.claude/skills/', '3_시스템/')  # mf:allow-path  (선언 파일이 코어 자리 안인지 가르는 접두 — 읽지 않음)

    def add(module, v, roots):
        if not isinstance(v, dict) or not VIEW_ID.fullmatch(module or '') or not VIEW_ID.fullmatch(v.get('id') or 'main'):
            return
        if v.get('phone') is False:                 # PC 에서만(«폰 연결» = 짝 코드가 폰에 실려 가지 않게 · 행위도 /v1/view/act 로 못 부름)
            return
        if not decl_file(v.get('html'), roots) or not decl_cmd(v.get('data'), roots):
            return
        vid = v.get('id') or 'main'
        if any(x['module'] == module and x['id'] == vid for x in out):
            return
        out.append({'module': module, 'id': vid, 'name': v.get('name') if isinstance(v.get('name'), str) else module,
                    'icon': v.get('icon') if isinstance(v.get('icon'), str) else 'layout-grid', 'html': v['html'], 'data': v['data']})
    for v in j.get('views') or []:
        add(v.get('owner') if isinstance(v, dict) else None, v, core)
    for v in j.get('formats') or []:
        if isinstance(v, dict) and isinstance(v.get('ext'), str) and re.fullmatch(r'[a-z0-9]{1,12}', v['ext']) and v['ext'] != 'md' \
                and not any(x['ext'] == v['ext'] for x in fmts) and decl_file(v.get('html'), ('3_시스템/',)) and decl_cmd(v.get('data'), ('3_시스템/',)):  # mf:allow-path  (같은 접두 가름)
            fmts.append({'ext': v['ext'], 'name': v.get('name') if isinstance(v.get('name'), str) else v['ext'],
                         'icon': v.get('icon') if isinstance(v.get('icon'), str) else 'layout-list', 'html': v['html'], 'data': v['data']})
    for m in roles.modules(on_only=True, vault=VAULT):
        add(m['id'], ((m.get('json') or {}).get('contributes') or {}).get('view'), (f".claude/skills/{m['id']}/",))
    return out, fmts


def view_list():
    vs, fs = view_decls()
    return {'views': [{k: v[k] for k in ('module', 'id', 'name', 'icon')} for v in vs], 'formats': [{k: f[k] for k in ('ext', 'name', 'icon')} for f in fs]}


def run_decl(cmd, fill):
    """선언된 자료 명령 → 마지막 줄 JSON. 데스크톱 brain-base door.brain.declared 와 같은 뜻(볼트를 작업 폴더로 · 창 없음)."""
    py = sys.executable
    if os.path.basename(py).lower() == 'pythonw.exe' and os.path.isfile(os.path.join(os.path.dirname(py), 'python.exe')):
        py = os.path.join(os.path.dirname(py), 'python.exe')
    argv = [py, os.path.join(VAULT, *cmd[1].split('/'))] + [fill.get(t, t) for t in cmd[2:]]
    env = {k: v for k, v in os.environ.items() if not k.startswith('CLAUDECODE')}
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        r = subprocess.run(argv, cwd=VAULT, capture_output=True, timeout=90, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        raise Bad(504, '자료 명령이 오래 걸림')
    lines = r.stdout.decode('utf-8', 'replace').strip().splitlines()
    try:
        return json.loads(lines[-1])
    except (IndexError, ValueError):
        log(f'화면 자료 못 읽음 {os.path.basename(cmd[1])} 종료 {r.returncode}')
        raise Bad(502, '자료를 못 읽음')


def view_payload(key, html, cmd, fill):
    hit = _views.get(key)
    if hit and time.time() - hit[0] < VIEW_TTL:
        return hit[1]

    def build():
        with open(os.path.join(VAULT, *html.split('/')), encoding='utf-8') as f:
            page = f.read()
        v = {'html': page, 'data': run_decl(cmd, fill)}
        _views[key] = (time.time(), v)
        return v
    return once('view:' + key, build)


def phone_view(q):
    vs, _ = view_decls()
    d = next((v for v in vs if v['module'] == q.get('module') and v['id'] == (q.get('id') or 'main')), None)
    if not d:
        raise Bad(404, '화면 없음')
    return view_payload(f"{d['module']}/{d['id']}", d['html'], d['data'], {'{reason}': 'open'})


def phone_format(q):
    rel, a = clean(q.get('path'))
    if not os.path.isfile(a) or phone_hidden(a):
        raise Bad(404, '없음')
    _, fs = view_decls()
    d = next((f for f in fs if rel.lower().endswith('.' + f['ext'])), None)
    if not d:
        raise Bad(404, '화면 없음')
    return view_payload('fmt:' + rel, d['html'], d['data'], {'{file}': rel})


# ───────── 화면 쓰기(11-17 · 사용자 Q3 «C» 폰에서 쓰기까지) — 데스크톱 brain-base 와 같은 규칙을 PC 에서 돌린다 ─────────
MOA_ID = re.compile(r'[\w.-]{1,64}:[\w.-]{1,64}')
ACT_ID = re.compile(r'[A-Za-z0-9_-]{1,64}\.[A-Za-z0-9_.-]{1,64}')
ARG_KEY = re.compile(r'[A-Za-z0-9_-]{1,40}')


def format_set(b):
    """형식 화면 쓰기 — 내 칸(field·id·value = formatview setMine) · 칸 너비(cols = setCols). 그 파일 한 장만 · 폰이 연 형식 파일만."""
    rel, a = clean(b.get('path'), WRITE_ROOTS)
    if not os.path.isfile(a) or phone_hidden(a):
        raise Bad(404, '없음')
    _, fs = view_decls()
    if not any(rel.lower().endswith('.' + f['ext']) for f in fs):
        raise Bad(404, '화면 없음')
    cols = b.get('cols')
    if cols is None:
        field, rid, value = b.get('field'), b.get('id'), b.get('value')
        if not isinstance(field, str) or not isinstance(rid, str) or not isinstance(value, str) or len(field) > 40 or len(value) > 20 or not MOA_ID.fullmatch(rid):
            raise Bad(400, '값이 잘못됨')
    elif not isinstance(cols, dict):
        raise Bad(400, '값이 잘못됨')
    with WRITE:
        with open(a, encoding='utf-8') as f:
            text = f.read()
        try:
            d = json.loads(text)
        except ValueError:
            return {'ok': False, 'why': '파일이 JSON 아님'}
        if not isinstance(d, dict):
            return {'ok': False, 'why': '파일이 JSON 아님'}
        if cols is None:
            rules = (d.get('fields') or {}).get(field) if isinstance(d.get('fields'), dict) else None
            lst = next((r['mine'] for r in (rules if isinstance(rules, list) else [rules]) if isinstance(r, dict) and isinstance(r.get('mine'), list)), None)
            if lst is None or (value != '' and value not in lst):
                return {'ok': False, 'why': '고를 수 없는 값'}
            mine = d['mine'] if isinstance(d.get('mine'), dict) else {}
            d['mine'] = mine
            col = mine[field] if isinstance(mine.get(field), dict) else {}
            mine[field] = col
            if value == '':
                col.pop(rid, None)
            else:
                col[rid] = value
        else:
            names = d['columns'] if isinstance(d.get('columns'), list) else ['제목', '마감']
            w = {k: min(2000, max(40, int(v + 0.5) if v > 0 else 0)) for k, v in cols.items()   # JS Math.round 와 같게(파이썬 round 는 짝수 쪽)
                 if k in names and isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float('inf')}
            if w == (d.get('widths') or {}):
                return {'ok': True, 'same': True}
            if w:
                d['widths'] = w
            else:
                d.pop('widths', None)
        write_atomic(a, json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    _views.pop('fmt:' + rel, None)
    log(f"폰 형식 화면 {'칸 너비' if cols is not None else '내 칸'} 적음")
    return {'ok': True}


def view_act(b):
    """모듈 화면 행위 — 그 화면 모듈의 행위(<모듈>.<이름>)만 brain.py run 으로(데스크톱 door.brain.run 과 같음 · --yes 없음 = 위험 행위는 돌기 전에 멈춤)."""
    vs, _ = view_decls()
    d = next((v for v in vs if v['module'] == b.get('module') and v['id'] == (b.get('id') or 'main')), None)
    if not d:
        raise Bad(404, '화면 없음')
    act, args = b.get('act'), b.get('args') or {}
    if not isinstance(act, str) or not ACT_ID.fullmatch(act) or not act.startswith(d['module'] + '.'):
        raise Bad(403, '그 화면의 행위가 아님')
    if not isinstance(args, dict) or len(args) > 16 or not all(isinstance(k, str) and ARG_KEY.fullmatch(k) and isinstance(v, str) and len(v) <= 400 for k, v in args.items()):
        raise Bad(400, '인자가 잘못됨')
    py = sys.executable
    if os.path.basename(py).lower() == 'pythonw.exe' and os.path.isfile(os.path.join(os.path.dirname(py), 'python.exe')):
        py = os.path.join(os.path.dirname(py), 'python.exe')
    argv = [py, os.path.join(HERE, 'brain.py'), 'run', act, *[f'{k}={v}' for k, v in args.items()], '--json', '--by', 'phone']
    env = {k: v for k, v in os.environ.items() if not k.startswith('CLAUDECODE')}
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        r = subprocess.run(argv, cwd=VAULT, capture_output=True, timeout=120, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        raise Bad(504, '행위가 오래 걸림')
    out, err = r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')
    try:
        j = json.loads(out.strip().splitlines()[-1])
    except (IndexError, ValueError):
        j = None
    _views.pop(f"{d['module']}/{d['id']}", None)
    if isinstance(j, dict) and isinstance(j.get('ok'), bool):
        log(f"폰 화면 행위 {act} {'됨' if j['ok'] else '안 됨'}")
        return {'ok': j['ok'], **({} if j['ok'] else {'err': str(j.get('err') or j.get('out') or '').strip()[-160:]})}
    log(f'폰 화면 행위 {act} 멈춤 종료 {r.returncode}')
    return {'ok': False, 'err': (err or out).strip()[-160:] or 'brain.py 가 JSON 을 내지 않음'}


# ───────── 홈 손 — 데스크톱 홈과 같은 고정 길(작업 끝냄 · 받은함 제안대로 · 되돌리기) · 장부 by = phone ─────────
_undo = set()                                       # 폰에 준 묶음 id 만 되돌린다(임의 장부 id 를 받지 않음 · 서버를 다시 켜면 비움)


def work_finish(b):
    rel, a = clean(b.get('path'), ('0_작업/',))
    if phone_hidden(a):
        raise Bad(404, '없음')
    import work
    with WRITE:
        r = work.finish(rel, by='phone')
    if r.get('batch'):
        _undo.add(r['batch'])
    _home['v'] = None
    log(f"폰 작업 끝냄 {'묶음 ' + r['batch'] if r.get('batch') else '안 됨'}")
    return {k: r[k] for k in ('batch', 'error') if r.get(k)}


def inbox_do(b):
    import inbox as inbox_mod
    name = b.get('name')
    d = roles.abs('inbox')
    if not isinstance(name, str) or name not in inbox_mod.items() or phone_hidden(os.path.join(d, name)):
        raise Bad(404, '받은함에 없음')
    with WRITE:
        rows = [inbox_mod.classify_one(name, fileops.Ctx(VAULT, by='phone', dry=True))]
        inbox_mod.execute(rows, {name}, 'phone')
    r = rows[0]
    _home['v'] = None
    log(f"폰 받은함 제안대로 {r.get('tag')}")
    return {'ok': bool(r.get('moved')), 'tag': r.get('tag'), **({'why': r['why']} if not r.get('moved') and r.get('why') else {})}


def op_path(rel):
    """폰 손이 닿는 자리 — 폰 범위(READ_ROOTS) 안 · 점·숨김(_색인·_lms) 자리 아님 · 범위 뿌리 자체 아님 · 민감 아님."""
    rel, a = clean(rel)
    parts = rel.split('/')
    if len(parts) < 2 or any(x.lower() in HIDE_PART for x in parts):   # 윈도에서 _LMS = _lms(11-16 · 여러 개 길이 같은 검사를 씀)
        raise Bad(403, '이 자리는 안 됨')
    return rel, a


def folder_name(name):
    """폰이 준 새 폴더 이름 — 안 되면 까닭 · 되면 None(빈 이름·나누개·점 자리·윈도 금지 글자·끝 점/공백·장치 이름·너무 김)."""
    if not isinstance(name, str) or not name.strip():
        return '빈 이름'
    if '/' in name or '\\' in name:
        return '이름에 / \\ 안 됨'
    if name in ('.', '..') or name.startswith('.'):
        return '점으로 시작하는 이름 안 됨'
    if BAD_PART.search(name):
        return '쓸 수 없는 글자(<>:"|?*)'
    if name != name.rstrip(' .') or name != name.lstrip(' '):
        return '앞뒤 공백·끝 점 안 됨'
    if RESERVED.fullmatch(name):
        return '윈도 장치 이름 안 됨'
    if len(name) > 120:
        return '이름이 너무 김(120자)'
    return None


def mkdir_op(b):
    """폰 «새 폴더» — 폰 범위 안(op_path · 숨김 _lms·_색인·점 자리 밖) · 부모 폴더가 있고 숨긴 자리 아님 · 이미 있으면 409.
    fileops.op_mkdir(장부 by=phone) → 되돌리기 묶음(/v1/undo = 빈 폴더면 치움 · 안에 무엇이 생겼으면 둠)."""
    dst = b.get('dst')
    if not isinstance(dst, str):
        raise Bad(400, '빈 이름')
    why = folder_name(dst.rsplit('/', 1)[-1])     # 끝 칸 = 새 이름(역슬래시는 바꾸지 않고 이름 글자로 본다 → 거절)
    if why:
        raise Bad(400, why)
    rel, a = op_path(dst)
    parent = posixpath.dirname(rel)
    pa = os.path.join(VAULT, *parent.split('/'))
    if not os.path.isdir(pa) or phone_hidden(pa):
        raise Bad(404, '폴더 없음')
    if os.path.lexists(a):                      # 윈도는 대소문자를 안 가린다 — 같은 이름(대소문자만 다름)도 있음
        raise Bad(409, '이미 있음')
    c = fileops.Ctx(VAULT, by='phone')
    with WRITE:
        try:
            ev = fileops.op_mkdir(c, rel, '폰에서 새 폴더')
        except fileops.Stop as e:
            raise Bad(409, str(e))
        finally:
            if c.events:
                fileops.write_view(c)
    if not ev:
        raise Bad(409, '이미 있음')
    _undo.add(c.batch)
    log(f'폰 새 폴더 묶음 {c.batch}')
    return {'batch': c.batch, 'dst': rel}


def keep_ext(rel, a, dst, ad):
    """파일 이름 바꾸기(같은 폴더 · dst 가 폴더 아님)는 원래 확장자를 언제나 지킨다 — 확장자를 바꾸는 길은 없다(사용자 11-23 «이름바꾸기에서 확장자를 빼»).
    dst 가 원래 확장자로 끝나면(대소문자 무시) 그 꼴을 원래 글자로 · 아니면 덧붙인다(옛 판 폰이 «Hw4» 를 보내도 «Hw4.sdocx» · «Hw5.pdf» 는 «Hw5.pdf.sdocx»).
    11-23 폰 «이름 바꾸기»가 `….sdocx → Hw4` 로 확장자를 지워 폰이 형식을 몰라 바깥 열기로 넘김. 확장자 없는 파일·폴더·옮기기는 그대로."""
    if not os.path.isfile(a) or os.path.isdir(ad) or posixpath.dirname(rel).lower() != posixpath.dirname(dst).lower():
        return dst
    ext = posixpath.splitext(rel)[1]
    if not ext:
        return dst
    return (dst[:-len(ext)] if dst.lower().endswith(ext.lower()) else dst) + ext


def fileop(b):
    op = b.get('op')
    if op == 'mkdir':
        return mkdir_op(b)
    if op not in ('mv', 'rm'):
        raise Bad(400, '모르는 일')
    rel, a = op_path(b.get('src'))
    if not os.path.exists(a) or phone_hidden(a):
        raise Bad(404, '없음')
    if os.path.isfile(a) and b.get('base') and b['base'] != etag_of(a):
        raise Bad(409, 'PC 에서 바뀜')            # 폰이 본 뒤 PC 에서 고쳐졌다 — 하지 않고 알린다
    c = fileops.Ctx(VAULT, by='phone')
    c.quiet_refs = True                         # 코드·설정 옛 경로 훑기는 알림 글뿐(폰에 안 감) — 한 번에 0.4초쯤 덜 든다(11-16 잼)
    with WRITE:
        try:
            if op == 'mv':
                dst, ad = op_path(b.get('dst'))
                if os.path.isdir(a) and (dst + '/').startswith(rel + '/'):
                    raise Bad(400, '자기 안으로')
                dst = keep_ext(rel, a, dst, ad)
                ev = fileops.op_mv(c, rel, dst, '폰에서 옮김')
                to = ev.get('dst') if isinstance(ev, dict) else None
            else:
                n = sum(len(fs) for _, _, fs in os.walk(a)) if os.path.isdir(a) else None
                ev = fileops.op_rm(c, rel, '폰에서 휴지통으로', count=n, user_asked=True)   # 휴지통(보존 일정표)뿐 — 영구 삭제 길은 없다
                to = None
            if not ev:
                raise Bad(409, '안 됨')
        except fileops.Stop as e:
            raise Bad(409, str(e))
        finally:
            if c.events:
                fileops.write_view(c)
    if c.events:
        _undo.add(c.batch)
    _home['v'] = None
    log(f'폰 {"옮김" if op == "mv" else "휴지통"} 묶음 {c.batch}')
    return {'batch': c.batch, **({'dst': to} if to else {})}


FILEOPS_MAX = 50                                    # 한 번에 고를 수 있는 수 — 한 개 2~3초(옵시디언 이동·링크 고침)라 50개 ≈ 2분


def went(c, rel):
    """이 묶음의 앞 줄이 이미 함께 옮긴(폴더 안 · 짝 메모) 것이면 지금 자리(휴지통이면 '') · 아니면 None."""
    low = rel.lower()
    for e in c.events:
        src = (e.get('src') or '').lower()
        if e.get('op') in ('mv', 'rename', 'rm') and src and (low == src or low.startswith(src + '/')):
            return '' if e['op'] == 'rm' else e['dst'] + rel[len(src):]
    return None


def fileops_many(b):
    """여러 개 고르기(사용자 11-16 «한번에 여러개 선택») — 한 fileops 묶음(장부 by=phone · 되돌리기 한 번)으로 옮기기·휴지통으로.
    한 줄씩 /v1/fileop 과 같은 규칙(범위·숨김·민감·폰이 본 판) · 안 된 줄이 있어도 나머지는 하고 줄마다 까닭을 준다."""
    op = b.get('op')
    if op not in ('mv', 'rm'):
        raise Bad(400, '모르는 일')
    items = b.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= FILEOPS_MAX:
        raise Bad(400, f'고른 것 1~{FILEOPS_MAX}개')
    if op == 'mv':
        dst, ad = clean(b.get('dst'))               # 범위 뿌리(2_지식 등)도 옮길 자리가 된다 — 한 개 길이 «뿌리/이름»을 받는 것과 같게
        if any(x.lower() in HIDE_PART for x in dst.split('/')):
            raise Bad(403, '이 자리는 안 됨')
        if not os.path.isdir(ad) or phone_hidden(ad):
            raise Bad(404, '옮길 폴더 없음')
    c = fileops.Ctx(VAULT, by='phone')
    c.quiet_refs = True
    out = []
    with WRITE:
        try:
            for it in items:
                raw = it.get('src') if isinstance(it, dict) else it
                r = {'src': raw if isinstance(raw, str) else ''}
                out.append(r)
                try:
                    rel, a = op_path(raw)
                except Bad as e:
                    r['error'] = e.msg
                    continue
                now_at = went(c, rel)
                if now_at is not None:
                    r.update(ok=True, followed=True, **({'dst': now_at} if now_at else {}))
                    continue
                if not os.path.exists(a) or phone_hidden(a):
                    r['error'] = '없음'
                    continue
                base = it.get('base') if isinstance(it, dict) else None
                if os.path.isfile(a) and base and base != etag_of(a):
                    r['error'] = 'PC 에서 바뀜'
                    continue
                if op == 'mv' and posixpath.dirname(rel).lower() == dst.lower():
                    r['error'] = '이미 그 자리'
                    continue
                if op == 'mv' and (dst + '/').lower().startswith(rel.lower() + '/'):
                    r['error'] = '자기 안으로'
                    continue
                try:
                    if op == 'mv':
                        ev = fileops.op_mv(c, rel, dst, '폰에서 옮김(여럿)')
                    else:
                        n = sum(len(fs) for _, _, fs in os.walk(a)) if os.path.isdir(a) else None
                        ev = fileops.op_rm(c, rel, '폰에서 휴지통으로(여럿)', count=n, user_asked=True)   # 휴지통뿐 — 영구 삭제 길은 없다
                except fileops.Stop as e:
                    r['error'] = str(e)
                    continue
                if not ev:
                    r['error'] = '안 됨'
                    continue
                r['ok'] = True
                if op == 'mv' and isinstance(ev, dict) and ev.get('dst'):
                    r['dst'] = ev['dst']
        finally:
            if c.events:
                fileops.write_view(c)
    if c.events:
        _undo.add(c.batch)
    _home['v'] = None
    done = sum(1 for r in out if r.get('ok'))
    log(f'폰 {"옮김" if op == "mv" else "휴지통"} 여럿 {done}/{len(out)}' + (f' 묶음 {c.batch}' if c.events else ''))
    return {**({'batch': c.batch} if c.events else {}), 'items': out}


def manual():
    """켜진 모듈의 설명서 장 — module.json contributes.manual · 데스크톱이 3_시스템/설명서/_index 에 옮긴 사본이 있는 것만(폰은 그 사본을 연다)."""
    out = []
    for m in roles.modules(on_only=True, vault=VAULT):
        for ch in ((m.get('json') or {}).get('contributes') or {}).get('manual') or []:
            f = ch.get('file') if isinstance(ch, dict) else None
            if not isinstance(f, str) or not f.startswith(f".claude/skills/{m['id']}/") or '..' in f.split('/'):
                continue
            b = posixpath.basename(f)[:-3] if f.endswith('.md') else posixpath.basename(f)
            if os.path.isfile(os.path.join(VAULT, '3_시스템', '설명서', '_index', b + '.md')):
                out.append({'base': b, 'name': ch.get('name') or m['id'], 'gist': ch.get('gist') or ''})
    return {'items': out}


def folders(_q=None):
    out = []
    for root in READ_ROOTS:
        base = os.path.join(VAULT, root.rstrip('/'))
        for d, ds, _fs in os.walk(base):
            ds[:] = sorted(x for x in ds if not x.startswith('.') and x not in HIDE_PART)
            rel = os.path.relpath(d, VAULT).replace(os.sep, '/')
            if rel.count('/') >= 1 or rel + '/' in READ_ROOTS:
                out.append(rel)
    return {'items': out}


def undo(b):
    key = b.get('batch')
    if key not in _undo:
        raise Bad(404, '되돌릴 묶음 아님')
    c = ctx()
    with WRITE:
        try:
            fileops.op_undo(c, key)
        except fileops.Stop as e:
            raise Bad(409, str(e))
        finally:
            if c.events:
                fileops.write_view(c)
    _undo.discard(key)
    _home['v'] = None
    log('폰 되돌림 ' + key)
    return {'ok': True}


_cards = {}


def phone_topic(q):
    """폰 «주제» 패널(안 2·3) — 주제 카드(topic.py build)와 같은 부품으로 마감·할 일·최근·기록·자리만. 지난 대화·장부·카드 글은 PC에서만(Claude 기록 · 볼트 밖).
    name = 주제 이름·별칭 · path = 지금 노트(PC 경로)의 주제 · 모르면 {topic: None}. 민감·폰 범위 밖 파일 줄은 뺀다. 30초 캐시."""
    topic = core_api.topic()
    fresh_topics()
    name = roles.canon(q['name']) if q.get('name') else roles.topic_of(clean(q['path'])[0]) if q.get('path') else None
    if not name:
        return {'topic': None}
    _warm['topics'] = [name] + [n for n in _warm['topics'] if n != name][:WARM_TOPICS - 1]
    return card_of(name)


def card_of(name):
    hit = _cards.get(name)
    if hit and time.time() - hit[0] < TOPIC_TTL:
        return hit[1]
    return once('topic:' + name, lambda: build_card(name))


def build_card(name):
    topic = core_api.topic()
    t = topic.entry(name)
    today = datetime.datetime.now(topic.KST).date()
    dirs = topic.topic_dirs(t)
    mods = topic.module_entries(t)
    nl, _ = topic.notes(t, dirs, mods)
    ok = lambda p: (p + '/').startswith(READ_ROOTS) and not phone_hidden(os.path.join(VAULT, *p.split('/')))  # noqa: E731
    v = {'topic': {k: t.get(k) for k in ('이름', '영역', '학기', '상태', '별칭')},
         'dirs': [p for _, p in dirs if ok(p)],
         'modules': [{'path': m, 'dir': os.path.isdir(os.path.join(VAULT, *m.split('/')))} for m in mods if ok(m)],
         'status': [x for x in topic.status(t, today) if ok(x['file'])],
         'todos': [x for x in topic.todos(t, dirs, nl) if ok(x['file'])],
         'recent': [x for x in topic.recent(dirs, mods) if ok(x['path'])],
         'records': [x for x in topic.records(t) if ok(x['path'])],
         'today': today.isoformat()}
    _cards[name] = (time.time(), v)
    return v

# ── 폰 화면 C1(11-15 · 모바일볼트 구성안 4차 · 3차 §3.2) — 시트·전체 화면이 데스크톱 오른쪽 곁창과 같은 일을 하게 ──
# 할 일 체크 · 지난 대화 · 장부 · 휴지통 목록·되살리기 · 주제 안 찾기. 폰 범위(READ_ROOTS) 밖·숨김·민감 파일은 안 내준다.
C1_FIND_MAX, C1_TRASH_MAX, C1_TRASH_LIMIT = 30, 50, 500


def topic_parts(name):
    """이름·별칭 → (topic 모듈, 등록부 줄, 자리, 모듈) · 모르는 주제면 404."""
    topic = core_api.topic()
    fresh_topics()
    n = roles.canon(name or '')
    if not n:
        raise Bad(404, '주제 없음')
    t = topic.entry(n)
    return topic, t, topic.topic_dirs(t), topic.module_entries(t)


def phone_ok(p):
    return isinstance(p, str) and bool(p) and (p + '/').startswith(READ_ROOTS) and not any(x.startswith('.') or x.lower() in HIDE_PART for x in p.split('/')) and not phone_hidden(os.path.join(VAULT, *p.split('/')))


def todo_check(b):
    """할 일 상자(폰 시트) — 그 줄이 아직 «- [ ] 같은 글»일 때만 «- [x]» 로(데스크톱 brain-base topic.ts check 와 같은 규칙 · 글은 topic.todos 가 낸 꼴로 견줌)."""
    topic = core_api.topic()
    rel, a = clean(b.get('file'), WRITE_ROOTS)
    line = b.get('line')
    if not os.path.isfile(a) or not rel.lower().endswith('.md') or phone_hidden(a) or not isinstance(line, int) or isinstance(line, bool) or line < 1:
        raise Bad(404, '없음')
    with WRITE:
        with open(a, encoding='utf-8', newline='') as f:
            text = f.read()
        ls = text.splitlines(keepends=True)
        if line > len(ls):
            raise Bad(409, '그 줄이 바뀜')
        ln = ls[line - 1]
        body = ln.rstrip('\r\n')
        m = topic.TODO.match(body)
        got = ' '.join(re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', m.group(1)).split())[:200] if m else None
        if got is None or got != b.get('text'):
            raise Bad(409, '그 줄이 바뀜')
        ls[line - 1] = body.replace('- [ ] ', '- [x] ', 1) + ln[len(body):]
        write_atomic(a, ''.join(ls))
    _cards.clear()
    _home['v'] = None
    log('폰 할 일 체크')
    return {'ok': True}


def topic_chats(q):
    """지난 대화(Stop 훅 스텁 · 3_시스템 안) — 때·첫 요청·세션 id 만(스텁 경로·내용은 안 줌)."""
    topic, t, dirs, mods = topic_parts(q.get('name'))
    return {'items': [{'id': x['id'], 'when': x['when'], 'first': x['first']} for x in topic.chats(t, dirs, mods)]}


def topic_ledger(q):
    """장부(fileops ops.jsonl)에서 이 주제 자리를 지나간 옮김·지움 — 폰 범위 안 경로만(휴지통 자리는 안 줌)."""
    topic, t, dirs, mods = topic_parts(q.get('name'))
    out = []
    for x in topic.ledger(dirs):
        src = x.get('src') if phone_ok(x.get('src')) else None
        dst = x.get('dst') if phone_ok(x.get('dst')) else None
        if src or dst:
            out.append({'ts': x.get('ts') or '', 'op': x.get('op') or '', 'src': src or dst, **({'dst': dst} if dst and src else {})})
    return {'items': out}


def topic_find(q):
    """주제 안 찾기 — 이 주제 자리·모듈의 파일 가운데 경로에 그 말이 든 것(최근 고친 순 · 원본 옆 짝 메모 뺌)."""
    topic, t, dirs, mods = topic_parts(q.get('name'))
    want = ' '.join((q.get('q') or '').split()).casefold()
    if not want:
        return {'items': []}
    fs = set()
    for _, p in dirs:
        fs |= set(topic.walk_files(os.path.join(VAULT, *p.split('/'))))
    for m in mods:
        a = os.path.join(VAULT, *m.split('/'))
        fs |= set(topic.walk_files(a)) if os.path.isdir(a) else {a}
    stems = {os.path.splitext(f)[0] for f in fs if not f.lower().endswith('.md')}
    hits = []
    for f in fs:
        r = os.path.relpath(f, VAULT).replace(os.sep, '/')
        if want not in r.casefold() or (f.lower().endswith('.md') and os.path.splitext(f)[0] in stems) or not phone_ok(r):
            continue
        hits.append({'path': r, 'mtime': os.path.getmtime(f)})
    hits.sort(key=lambda x: -x['mtime'])
    return {'items': hits[:C1_FIND_MAX]}


def trash_list(q=None):
    """휴지통(fileops 가 넣은 것 · 아직 휴지통에 있음 · 되살린 적 없음 · 원래 자리가 폰 범위 안) — 최근 것부터 limit 개 · n = 모두.
    날로 자르지 않는다(11-16): 자동 비우기가 없어(비우기 = 사람 `fileops purge`) 30일 넘은 것도 휴지통에 있고 되살릴 수 있다 — age(지난 날)로 보인다."""
    try:
        lim = min(max(int((q or {}).get('limit') or C1_TRASH_MAX), 1), C1_TRASH_LIMIT)
    except ValueError:
        raise Bad(400, 'limit 숫자 아님')
    c = ctx()
    evs = fileops.load_events(c)
    back = {e.get('of') for e in evs if e.get('op') == 'restore'}
    today = datetime.date.today()
    out, n = [], 0
    for e in reversed(evs):
        if e.get('op') != 'rm' or e.get('id') in back or not e.get('dst'):
            continue
        src = e.get('src') or ''
        a = c.abs(e['dst'])
        if not os.path.exists(a) or not (src + '/').startswith(READ_ROOTS) or any(x.startswith('.') or x.lower() in HIDE_PART for x in src.split('/')) or (os.path.isfile(a) and phone_hidden(a)):
            continue
        n += 1
        if len(out) >= lim:
            continue
        ts = e.get('ts') or ''
        try:
            age = (today - datetime.date.fromisoformat(ts[:10])).days
        except ValueError:
            age = None
        out.append({'id': e['id'], 'ts': ts[:16].replace('T', ' '), 'src': src, **({'age': age} if age is not None else {}), **({'dir': True} if os.path.isdir(a) else {})})
    return {'items': out, 'n': n}


def trash_restore(b):
    """휴지통 줄 되살리기 — 원래 자리로(fileops restore · 장부 by=phone · 되돌리기 묶음). ids = 여럿 → 한 묶음 · 줄마다 결과."""
    if 'ids' in b:
        return trash_restore_many(b.get('ids'))
    key = b.get('id')
    c = ctx()
    ev = fileops.find_event(c, key) if isinstance(key, str) else None
    src = (ev or {}).get('src') or ''
    if not ev or ev.get('op') != 'rm' or not (src + '/').startswith(READ_ROOTS) or any(x.startswith('.') or x.lower() in HIDE_PART for x in src.split('/')):
        raise Bad(404, '휴지통에 없음')
    with WRITE:
        try:
            if not fileops.op_restore(c, key):
                raise Bad(409, '안 됨')
        except fileops.Stop as e:
            raise Bad(409, str(e))
        finally:
            if c.events:
                fileops.write_view(c)
    _undo.add(c.batch)
    _home['v'] = None
    log('폰 되살림 묶음 ' + c.batch)
    return {'ok': True, 'batch': c.batch}


def trash_restore_many(ids):
    if not isinstance(ids, list) or not 1 <= len(ids) <= FILEOPS_MAX or not all(isinstance(x, str) for x in ids):
        raise Bad(400, f'고른 것 1~{FILEOPS_MAX}개')
    c = ctx()
    out = []
    with WRITE:
        try:
            for key in ids:
                r = {'id': key}
                out.append(r)
                ev = fileops.find_event(c, key)
                src = (ev or {}).get('src') or ''
                if not ev or ev.get('op') != 'rm' or not (src + '/').startswith(READ_ROOTS) or any(x.startswith('.') or x.lower() in HIDE_PART for x in src.split('/')):
                    r['error'] = '휴지통에 없음'
                    continue
                r['src'] = src
                try:
                    if not fileops.op_restore(c, key):
                        r['error'] = '안 됨'
                        continue
                except fileops.Stop as e:
                    r['error'] = str(e)
                    continue
                r['ok'] = True
        finally:
            if c.events:
                fileops.write_view(c)
    if c.events:
        _undo.add(c.batch)
    _home['v'] = None
    log(f'폰 되살림 여럿 {sum(1 for r in out if r.get("ok"))}/{len(out)}' + (f' 묶음 {c.batch}' if c.events else ''))
    return {**({'batch': c.batch} if c.events else {}), 'items': out}


# ───────── 폰 승인(11-17 · 설계 제작자 작업 노트 · 소스 C:\brain-approve) ─────────
# 서버는 «안 믿음»: 나르고 부르기만 한다. 붙이는 판단은 전부 게이트 코어 적용기(3_시스템/hooks/approve/approve.py)가 한다.
# 대기 수(배지·알림)는 서버가 묶음 json 만 읽어 센다 — 적용기가 깔리기 전에도 뜬다(B 단계). 적용기가 없으면 나머지 길은 ok:false.
# 풀기·등록·폐기·콘솔 붙이기 끝점은 일부러 없다 — 사람 콘솔만(설계 §3.3 · T8).
APPROVER = os.path.join(VAULT, '3_시스템', 'hooks', 'approve', 'approve.py')  # mf:allow-path  게이트 코어 · 서버는 고치지 않는다
APPROVE_BB = os.path.join(VAULT, '3_시스템', '_index', 'bigboss')  # mf:allow-path  pending.py 묶음 자리(읽기만)
APPROVE_LEDGER = os.path.join(VAULT, '3_시스템', '_index', 'approve', 'ledger.jsonl')  # mf:allow-path  적용기 장부(읽기만)
APPROVE_TTL = 30                                    # ping 에 싣는 짧은 꼴 캐시(초)
APPROVE_MAX = 64 * 1024                             # 서명 요청 본문 상한(approve.py MAX_IN 과 같음)
_appr = {'at': 0.0, 'v': None}
_appr_lock = threading.Lock()


def approve_cli(*args, data=None, timeout=60):
    """적용기를 부른다 → 마지막 줄 JSON. 없거나 깨지면 ok:false(서버는 판단하지 않는다)."""
    if not os.path.isfile(APPROVER):
        return {'ok': False, 'why': '적용기 없음(PC 에서 묶음 33 을 붙여야 함)'}
    kw = {'input': data} if data is not None else {'stdin': subprocess.DEVNULL}
    try:
        r = subprocess.run([sys.executable, APPROVER, *args], capture_output=True, timeout=timeout, creationflags=0x08000000, cwd=VAULT, **kw)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {'ok': False, 'why': f'적용기를 못 돌림 ({type(e).__name__})'}
    lines = r.stdout.decode('utf-8', 'replace').strip().splitlines()
    try:
        out = json.loads(lines[-1])
        return out if isinstance(out, dict) else {'ok': False, 'why': '적용기 답 꼴이 다름'}
    except (ValueError, IndexError):
        return {'ok': False, 'why': '적용기 답이 JSON 아님'}


def approve_count():
    """(대기 수, 가장 오래 분, run 별) — 묶음 json(state pending)만 읽는다. 배지·알림용 셈일 뿐 붙이는 판단이 아니다."""
    now_t, runs, total, oldest = time.time(), [], 0, 0
    try:
        names = sorted(os.listdir(APPROVE_BB))
    except OSError:
        names = []
    for r in names:
        d = os.path.join(APPROVE_BB, r, 'pending')
        if not os.path.isdir(os.path.join(APPROVE_BB, r)):
            continue
        try:
            files = os.listdir(d)
        except OSError:
            files = []          # pending/ 없이 명령만 올린 run(pending.py cmd)도 명령 셈은 한다(11-21 찾음)
        n = o = 0
        for f in files:
            if not re.match(r'\d+-.*\.json$', f):
                continue
            try:
                with open(os.path.join(d, f), encoding='utf-8') as h:
                    j = json.load(h)
            except (OSError, ValueError):
                continue
            if not isinstance(j, dict) or j.get('state') != 'pending':
                continue
            n += 1
            try:
                o = max(o, int((now_t - time.mktime(time.strptime(j.get('added') or '', '%Y-%m-%d %H:%M:%S'))) // 60))
            except (ValueError, OverflowError):
                pass
        cmds = approve_cmds(r, now_t)      # 명령 승인(11-20) — 대기·시효 안 것만
        for c in cmds:
            o = max(o, c['age_min'])
        if n or cmds:
            runs.append({'run': r, 'n': n + len(cmds), 'bundles': n, 'oldest_min': o, 'cmds': cmds})
            total, oldest = total + n + len(cmds), max(oldest, o)
    return total, oldest, runs


APPROVE_REQ_TTL = 12 * 3600    # 명령 요청 시효 — approve.py REQ_TTL 과 같음(셈일 뿐 · 판단은 적용기)


def approve_cmds(run, now_t):
    """run 의 명령 승인 대기 [{id, purpose, age_min}] — 요청 json(state pending · 12시간 안)만 읽는다."""
    d, out = os.path.join(APPROVE_BB, run, 'commands'), []
    try:
        files = sorted(os.listdir(d))
    except OSError:
        return out
    for f in files:
        m = re.match(r'(\d+)-.*\.json$', f)
        if not m:
            continue
        try:
            with open(os.path.join(d, f), encoding='utf-8') as h:
                j = json.load(h)
        except (OSError, ValueError):
            continue
        if not isinstance(j, dict) or j.get('state') != 'pending':
            continue
        try:
            age = now_t - int(j.get('added_at') or 0)
        except (TypeError, ValueError):
            continue
        if 0 <= age <= APPROVE_REQ_TTL:
            out.append({'id': int(m.group(1)), 'purpose': str(j.get('purpose') or '')[:40], 'age_min': int(age // 60)})
    return out


def approve_frozen():
    """적용기 장부의 마지막 동결·풀기(보이기용 — 막는 것은 적용기)."""
    last = False
    try:
        with open(APPROVE_LEDGER, encoding='utf-8') as h:
            for ln in h:
                if '"freeze"' not in ln and '"unfreeze"' not in ln:
                    continue
                try:
                    ev = json.loads(ln).get('ev')
                except ValueError:
                    continue
                last = True if ev == 'freeze' else False if ev == 'unfreeze' else last
    except OSError:
        pass
    return last


def approve_keys():
    try:
        with open(os.path.join(os.path.dirname(APPROVER), 'keys.txt'), encoding='utf-8') as h:
            return sum(1 for ln in h if ln.strip() and not ln.startswith('#'))
    except OSError:
        return 0


# ───────── 손발 앱 모듈 켜기(11-18 · 제작자 작업 노트 §3·§4) ─────────
# 앱(brain.phone 판 35~)은 기능마다 모듈이고, 핑의 'modules' 로 켜고 끈다(앱 갱신 없이). 말하지 않은 id 는 앱이 마지막 값 → module.json 기본.
PHONE_MODS_FILE = os.path.join(STATE, 'phone-modules.json')   # {앱 모듈 id: true|false} — 손으로 덮는 자리(없으면 안 씀)
_phone_mods = {'at': 0.0, 'v': None}


def phone_modules():
    """ping 'modules' — 볼트 모듈의 contributes.phone.app(켜진 모듈이 하나라도 부르면 켬 · 꺼진 모듈만 부르면 끔) · 승인 = 적용기(approve.py)가
    있을 때 · phone-modules.json 이 마지막에 덮음. 30초 담음(핑마다 module.json 을 다 읽지 않게)."""
    t = time.time()
    if _phone_mods['v'] is not None and t - _phone_mods['at'] < 30:
        return _phone_mods['v']
    out = {}
    try:
        for m in roles.modules(vault=VAULT):
            app = (((m.get('json') or {}).get('contributes') or {}).get('phone') or {}).get('app') or []
            for a in app if isinstance(app, list) else []:
                if isinstance(a, str) and a:
                    out[a] = out.get(a, False) or bool(m.get('on'))
    except Exception as e:      # 모듈 목록을 못 읽어도 핑은 나간다(앱은 마지막 값을 씀)
        log(f'phone modules: {e}')
    out['approve'] = os.path.isfile(APPROVER)
    try:
        with open(PHONE_MODS_FILE, encoding='utf-8') as f:
            over = json.load(f)
        if isinstance(over, dict):
            out.update({k: bool(v) for k, v in over.items() if isinstance(k, str)})
    except (OSError, ValueError):
        pass
    _phone_mods.update(at=t, v=out)
    return out


def approve_brief():
    """ping 의 'approve' 칸 {n, oldest, frozen} — 폰 알림(brain-phone)·홈 단추 배지(brain-server)가 본다 · 30초 캐시."""
    with _appr_lock:
        if _appr['v'] is not None and time.time() - _appr['at'] < APPROVE_TTL:
            return _appr['v']
    n, oldest, _ = approve_count()
    v = {'n': n, 'oldest': oldest, 'frozen': approve_frozen()}
    with _appr_lock:
        _appr.update(at=time.time(), v=v)
    return v


def approve_forget():
    with _appr_lock:
        _appr['v'] = None


def approve_status(q):
    n, oldest, runs = approve_count()
    if runs:
        approve_order(runs)
    return {'ok': True, 'waiting': n, 'oldest_min': oldest, 'runs': runs, 'frozen': approve_frozen(), 'keys': approve_keys(),
            'approver': os.path.isfile(APPROVER)}


def approve_order(runs):
    """순서(11-28): run 안 묶음·명령의 순서와 막힘(order · blocked_by '먼저: 묶음 03(대기)')은 적용기 status 가 잰다 - 서버는 나르기만.
    적용기가 없거나 옛 판(items 없음)이면 아무것도 안 붙인다 = 지금 꼴(옛 앱도 그대로 · 막는 것은 어차피 적용기 challenge-cmd)."""
    st = approve_cli('status', '--json', timeout=20)
    by = {r.get('run'): r for r in st.get('runs') or [] if isinstance(r, dict)} if st.get('ok') else {}
    for r in runs:
        a = by.get(r['run'])
        if not a or not isinstance(a.get('items'), list):
            continue
        r['items'], r['bundles_blocked_by'] = a['items'], a.get('bundles_blocked_by')
        got = {c.get('id'): c for c in a.get('cmds') or [] if isinstance(c, dict)}
        for c in r['cmds']:
            x = got.get(c['id'])
            if x:
                c['order'], c['blocked_by'] = x.get('order'), x.get('blocked_by')


def approve_bundle(q):
    run = q.get('run') or ''
    if not re.fullmatch(r'[\w-][\w.-]{0,63}', run) or '..' in run:
        raise Bad(400, 'run 꼴이 다름')
    out = approve_cli('challenge', run, '--json')
    if out.get('frozen'):
        out['frozen_why'] = approve_frozen_why()     # 폰 승인 화면이 «얼어 있음» 까닭을 보이게(11-20 · 보이기용 — 막는 것은 적용기)
    return out


def approve_run_id(q):
    run, nid = str(q.get('run') or ''), str(q.get('id') or '')
    if not re.fullmatch(r'[\w-][\w.-]{0,63}', run) or '..' in run or not re.fullmatch(r'\d{1,4}', nid):
        raise Bad(400, 'run·id 꼴이 다름')
    return run, nid


def approve_command(q):
    """명령 승인 하나 + 도전값(부를 때마다 새 도전값) — 폰이 요청·파일 바이트에서 서명 글을 스스로 만든다(서버는 나르기만)."""
    run, nid = approve_run_id(q)
    out = approve_cli('challenge-cmd', run, nid, '--json')
    if out.get('frozen'):
        out['frozen_why'] = approve_frozen_why()
    return out


def approve_result(q):
    run, nid = approve_run_id(q)
    return approve_cli('result', run, nid)


def approve_frozen_why():
    """적용기 장부의 마지막 동결 까닭(풀린 뒤면 '')."""
    why = ''
    try:
        with open(APPROVE_LEDGER, encoding='utf-8') as h:
            for ln in h:
                if '"freeze"' not in ln and '"unfreeze"' not in ln:
                    continue
                try:
                    j = json.loads(ln)
                except ValueError:
                    continue
                why = (j.get('why') or '') if j.get('ev') == 'freeze' else '' if j.get('ev') == 'unfreeze' else why
    except OSError:
        pass
    return str(why)[:200]


def approve_bin(obj, have=''):
    """form=bin 꼴(앱 판 36~ · 11-19): 머리 JSON 한 줄(항목의 base64 «diff» 대신 «len») + LF + 항목 diff 바이트 차례로.
    30MB 묶음이 base64 JSON 42MB 로 가서 폰이 글자로 두세 번 베끼던 것을 없앤다. 바이트는 적용기가 낸 그대로(나르기만) — 폰이 스스로 해시를 잰다.
    have = 폰 화면 묶음의 이어 붙인 sha 와 같으면 바이트 없이 머리만(«same»). 서버가 거짓말해도 적용기가 제 파일로 서명 글을 다시 만들어 거절한다."""
    import base64
    diffs = [base64.b64decode(i.get('diff') or '') for i in obj.get('items') or []]
    allsha = hashlib.sha256(b''.join(d if d.endswith(b'\n') else d + b'\n' for d in diffs)).hexdigest()
    same = bool(have) and have == allsha
    head = dict(obj, items=[{**{k: v for k, v in i.items() if k != 'diff'}, 'len': len(d)} for i, d in zip(obj['items'], diffs)])
    if same:
        head['same'] = True
    return json.dumps(head, ensure_ascii=False).encode('utf-8') + b'\n' + (b'' if same else b''.join(diffs))


def approve_recent(q):
    try:
        n = min(max(int(q.get('n') or 20), 1), 100)
    except ValueError:
        n = 20
    return approve_cli('recent', '--n', str(n))


def approve_sign(b):
    body = json.dumps({'message': str(b.get('message') or ''), 'sig': str(b.get('sig') or '')}).encode()
    if len(body) > APPROVE_MAX:
        raise Bad(413, '너무 큼')
    res = approve_cli('apply-signed', '-', data=body, timeout=120)
    approve_forget()
    if res.get('started'):
        log(f"폰 명령 승인 {res.get('run')} {res.get('id')} 실행 시작 · 기기 {req_device()}")
    else:
        log(f"폰 승인 {'붙임 ' + str(res.get('applied')) if res.get('ok') else '안 붙임 · ' + str(res.get('why'))} · 기기 {req_device()}")
    return res


def approve_reject(b):
    if b.get('id') is not None:       # 명령 승인 거절(11-20) — 요청을 닫는다
        run, nid = approve_run_id(b)
        res = approve_cli('reject-cmd', run, nid, '--why', str(b.get('why') or '')[:200])
        approve_forget()
        log(f'폰 명령 승인 거절 {run} {nid} · 기기 {req_device()}')
        return res
    res = approve_cli('reject', str(b.get('run') or ''), '--all', str(b.get('all') or ''), '--why', str(b.get('why') or '')[:200])
    approve_forget()                  # 거절 직후 당김이 30초 캐시의 옛 n 을 받지 않게(11-21)
    log(f'폰 승인 거절 {b.get("run")} · 기기 {req_device()}')
    return res


def approve_freeze(b):
    res = approve_cli('freeze', '--why', (f'폰 {req_device()} · ' + str(b.get('why') or ''))[:200])
    approve_forget()
    log(f'폰 승인 동결 · 기기 {req_device()}')
    return res


def approve_enroll(b):
    label = re.sub(r'[^\w .-]', '', str(b.get('label') or req_device()))[:40]
    res = approve_cli('enroll', str(b.get('spki') or ''), '--label', label)
    log(f'폰 승인 키 등록 요청 {res.get("key")} · 기기 {req_device()}')
    return res


C1_GET = {'/v1/topic/chats': topic_chats, '/v1/topic/ledger': topic_ledger, '/v1/topic/find': topic_find, '/v1/trash': trash_list,
          '/v1/approve': approve_status, '/v1/approve/bundle': approve_bundle, '/v1/approve/recent': approve_recent,
          '/v1/approve/command': approve_command, '/v1/approve/result': approve_result}


_names = {'at': 0, 'map': {}}


def name_key(s):
    return unicodedata.normalize('NFC', s).lower()      # 옵시디언 링크처럼 대소문자를 가리지 않는다


_all = {'at': 0, 'keys': set()}


def vault_names():
    """볼트 전체의 이름 키(폰에 안 주는 자리까지 · 경로는 담지 않는다). 폰이 못 찾은 링크가 «볼트에 없음»인지 «있는데 폰에 안 줌»인지 가른다. 1분 캐시.
    점 폴더(.git·.obsidian 등)는 옵시디언도 안 보여 링크가 못 닿는다."""
    if time.time() - _all['at'] > 60:
        keys = set()
        for _, subs, files in os.walk(VAULT):
            subs[:] = [s for s in subs if not s.startswith('.')]
            keys.update(name_key(f[:-3] if f.lower().endswith('.md') else f) for f in files if not f.endswith('.tmp'))
        _all.update(at=time.time(), keys=keys)
    return _all['keys']


SHA_HEX = re.compile(r'[0-9a-f]{64}')
SHA_LINE = re.compile(r'^sha256:\s*["\']?([0-9a-f]{64})', re.M)


def find_sha(h):
    """원본 sha256 → 지금 경로(필기 설계 §4). 색인 노트 1_수집/_색인/<원본 상대경로>.색인.md 의 머리 sha256 으로 찾는다 —
    색인은 ingest 가 원본이 옮겨지면 해시로 다시 잇는다. 원본이 실제로 있고 폰 범위·민감 아님일 때만 경로를 준다."""
    h = (h or '').strip().lower()
    if not SHA_HEX.fullmatch(h):
        raise Bad(400, '해시가 잘못됨')
    base = os.path.join(VAULT, '1_수집', '_색인')
    for d, _, fs in os.walk(base):
        for f in fs:
            if not f.endswith('.색인.md'):
                continue
            a = os.path.join(d, f)
            try:
                with open(a, encoding='utf-8', errors='replace') as fh:
                    head = fh.read(4096)
            except OSError:
                continue
            m = SHA_LINE.search(head)
            if not m or m.group(1) != h:
                continue
            rel = '1_수집/' + os.path.relpath(a, base).replace('\\', '/')[:-len('.색인.md')]  # mf:allow-path  (폰이 원본을 보고 고친 원본을 휴지통 거쳐 덮음 · 사용자 결정 · mobility 작업 F)
            try:
                rel, src = clean(rel)
            except Bad:
                continue
            if os.path.isfile(src) and not phone_hidden(src):
                return {'path': rel}
    raise Bad(404, '없음')


# ───────── 볼트 바뀜 버스(11-23) — PC 에서 누가 바꿨든 폰이 몇 초 안에(폴더 나무 · 연 노트 · 옛 경로 · 링크 · 홈 · 찾기) ─────────
BUS = None
_cgen = {}                  # 기기 id → 바뀜 물음 차례 — 같은 기기가 새로 걸면 옛 물음은 곧 끝낸다(/v1/watch 의 _wgen 과 같은 까닭: 붙잡힌 물음이 쌓여 같은 호스트 연결 6개를 채움 · 11-23 check S30~S32 잼)
_cgen_lock = threading.Lock()
FRESH_READ = 200 * 1024                             # 찾기 보탬이 읽는 노트 앞부분


def watch_keep(rel, is_dir):
    """폰에 보일 자리인가 — READ_ROOTS·DOC_ROOTS 안 · 점 이름·숨은 칸(_lms·_색인)·임시 파일 밖. 민감 판정은 내줄 때(changes_post) 한다."""
    if not (rel + '/').startswith(READ_ROOTS + DOC_ROOTS) or rel.endswith('.tmp'):
        return False
    return not any(x.startswith('.') or x in HIDE_PART for x in rel.split('/'))


def bus_changed(_kinds):
    """바뀜이 났다 — 서버가 기억하던 이름 지도(링크)·홈을 비운다(다음 물음이 새로 잰다)"""
    _names['at'] = _all['at'] = 0
    _home['v'] = None


def bus_start():
    global BUS
    if vaultwatch is None:
        return log('바뀜 버스 없음(vaultwatch.py 없음)')
    try:
        BUS = vaultwatch.Bus(VAULT, watch_keep, os.path.join(HERE, 'ledger', 'ops.jsonl'), bus_changed).start()
        log(f'바뀜 버스 {BUS.mode}')
    except Exception as e:  # noqa: BLE001 — 버스가 서버 시작을 막지 않게(폰은 옛 길 = 5분 목록)
        log(f'바뀜 버스 못 켬 {type(e).__name__}: {e}')


def changes_post(b):
    """POST /v1/changes {since, wait} — 폰 범위 안 바뀜을 폴더(dirs)와 옮김(moves)으로. 폰에 안 주는 노트(민감)는 옮김에서 뺀다(폴더만)."""
    if BUS is None:
        raise Bad(404, '없는 길')
    try:
        since = int(b.get('since') or 0)
    except (TypeError, ValueError):
        since = 0
    who = str(b.get('id') or '')[:64]
    with _cgen_lock:
        my = _cgen[who] = _cgen.get(who, 0) + 1 if who else 0
    r = BUS.since(since, b.get('wait') if isinstance(b.get('wait'), int) else 0, stop=(lambda: _cgen.get(who) != my) if who else None)
    if r.get('stale'):
        return {'seq': r['seq'], 'dirs': [], 'moves': [], 'stale': True}     # 같은 기기가 새로 걸었다(판 바꿈·다시 읽기) — 옛 물음은 바로 끝내 연결을 돌려준다
    dirs, moves = set(), []
    for e in r['events']:
        for p in (e.get('p'), e.get('src'), e.get('dst')):
            if p:
                dirs.add(p.rsplit('/', 1)[0] if '/' in p else '')
        if e['k'] == 'mv' and watch_keep(e['dst'], e['dir']):
            a = os.path.join(VAULT, *e['dst'].split('/'))
            if os.path.exists(a) and not phone_hidden(a):
                moves.append({'src': e['src'], 'dst': e['dst'], 'dir': e['dir']})
    return {'seq': r['seq'], 'dirs': sorted(dirs), 'moves': moves, 'mode': r.get('mode'), **({'reset': True} if r.get('reset') else {})}


def moved_to(rel):
    """없어진 파일의 지금 자리(폰이 옛 경로로 열 때 · 11-23) — 버스가 본 옮김 → 장부 옮김(옵시디언·fileops·따라가기) → 같은 끝 이름(볼트에서 하나뿐인 이름 규약).
    폰에 안 주는 자리·찾지 못함 = None."""
    cands = [c for c in ((BUS.moved(rel) if BUS else None), mark_follow(rel, 0)) if c and c != rel]
    for c in cands:
        try:
            r, a = clean(c, READ_ROOTS + DOC_ROOTS)
        except Bad:
            continue
        if os.path.isfile(a) and not phone_hidden(a):
            return r
    try:
        to = resolve(rel, quiet=True)['path']
    except Bad:
        return None
    return to if to != rel else None


def fresh_hits(q, idx, k):
    """찾기 보탬 — 서버가 켜진 뒤 생기거나 고친 노트 중 색인이 아직 모르는(색인 시각보다 새) 것에서 찾는 말이 다 든 것(최근부터 · 3개까지)"""
    words = [w for w in (q or '').lower().split() if w]
    if BUS is None or not words:
        return []
    out = []
    for rp, _at in reversed(BUS.fresh_notes()):
        if len(out) >= min(3, k):
            break
        if '/_lms/' in rp or not (rp + '/').startswith(READ_ROOTS):
            continue
        a = os.path.join(VAULT, *rp.split('/'))
        try:
            mt = os.path.getmtime(a)
        except OSError:
            continue
        ent = idx.get(rp) if isinstance(idx, dict) else None
        if isinstance(ent, dict) and float(ent.get('mtime') or 0) >= mt:
            continue                                # 색인이 이미 이 판을 안다 — 순위는 색인 몫
        if phone_hidden(a):
            continue
        try:
            with open(a, encoding='utf-8', errors='replace') as f:
                text = (os.path.basename(rp)[:-3] + '\n' + f.read(FRESH_READ)).lower()
        except OSError:
            continue
        if all(w in text for w in words):
            out.append({'path': rp, 'score': 0, 'gist': '', 'fresh': True})
    return out


def resolve(name, quiet=False):
    """노트·원본 이름 → 경로(폰에서 [[링크]]를 누를 때 · 파일 이름은 볼트에서 하나뿐이라는 규약). 1분 캐시.
    못 찾으면 404(볼트에도 없음 · 이름을 로그에 한 줄) 또는 403(볼트에는 있는데 폰에 안 줌 — 민감·READ_ROOTS 밖·_색인·_lms).
    경로 꼴 링크([[1_수집/배움/…/글|원본]] · [[1_수집/…/글.pdf]])는 그 자리를 먼저 보고, 없으면 끝 이름으로 찾는다.
    md 는 확장자 없이, 원본은 확장자까지 적은 이름으로 찾는다(옵시디언 링크와 같다)."""
    whole = (name or '').strip().replace('\\', '/').strip('/')
    if '/' in whole and not whole.lower().endswith('.md'):    # 이름에 # 이 든 원본(«과제 #1.pdf») — 찾기의 «원본» 단추는 온전한 경로를 보낸다
        try:
            rel, a = clean(whole)
        except Bad:
            rel = a = ''
        if a and os.path.isfile(a):
            if phone_hidden(a):                                 # 이름 분기와 같은 403(11-20 검증) — 지금 민감 판정은 md 만(front)이라 이 분기(md 아님)엔 안 걸리지만 판정이 넓어져도 경로째 물음이 새지 않게
                raise Bad(403, 'PC에서만')
            return {'path': rel}
    want = (name or '').split('#')[0].split('|')[0].strip().replace('\\', '/').strip('/')
    if want.lower().endswith('.md'):
        want = want[:-3]
    if '/' in want:
        for cand in (want + '.md', want):
            try:
                rel, a = clean(cand, READ_ROOTS + DOC_ROOTS)
            except Bad:
                continue
            if os.path.isfile(a) and not phone_hidden(a):
                return {'path': rel}
        want = want.rsplit('/', 1)[1]
    if time.time() - _names['at'] > 60:
        m = {}
        for root in READ_ROOTS + DOC_ROOTS:
            for d, subs, files in os.walk(os.path.join(VAULT, root.rstrip('/'))):
                subs[:] = [s for s in subs if not s.startswith('.') and s not in HIDE_PART]
                for f in files:
                    if f.endswith('.tmp'):
                        continue
                    m.setdefault(name_key(f[:-3] if f.lower().endswith('.md') else f), os.path.relpath(os.path.join(d, f), VAULT).replace('\\', '/'))
        _names.update(at=time.time(), map=m)
    rel = _names['map'].get(name_key(want))
    if rel and not phone_hidden(os.path.join(VAULT, *rel.split('/'))):
        return {'path': rel}
    if not rel and _names['at'] and name_key(want) in vault_names() and _names['at'] < _all['at']:
        _names['at'] = 0                            # 이름 지도가 더 낡았다(막 만든 노트) — 한 번 다시 만들어 본다(11-23)
        return resolve(name, quiet)
    if rel or name_key(want) in vault_names():      # 볼트에는 있는데 폰에 안 주는 이름(민감 · 폰 범위 밖 · 색인) — «없음»과 가른다. 경로·내용은 내주지 않는다
        raise Bad(403, 'PC에서만')
    if not quiet:
        log(f'링크 없음 {CTRL.sub(" ", name or "")[:120]}')   # 볼트에도 없는 이름만 — 폰에서 못 찾는 링크를 세어 고칠 것을 가린다(찾는 말·경로 로그와 달리 «없는 이름»이다)
    raise Bad(404, '없음')


# ───────── 볼트 링크 넘김(11-20) — /open 쪽 · 열쇠 없는 길(짝짓기 넷 + 이것) ─────────
OBSIDIAN_ANDROID = 'md.obsidian'


def open_urls(rel):
    """볼트 경로 → 기기마다 옵시디언 주소 {phone, intent, pc}.
    phone = 폰 brain-server 주소(폰에 없으면 PC 에서 받아 엶 · alarms.open_note 와 같은 꼴) · intent = 안드로이드 크롬이 앱으로 넘기는 꼴
    pc = 옵시디언 기본 주소(이 볼트 이름) — PC brain-base 0.49.24~ 는 phone 꼴도 받는다."""
    f = urllib.parse.quote(rel, safe='')
    return {'phone': f'obsidian://brain-server?file={f}',
            'intent': f'intent://brain-server?file={f}#Intent;scheme=obsidian;package={OBSIDIAN_ANDROID};end',
            'pc': f'obsidian://open?vault={urllib.parse.quote(os.path.basename(VAULT), safe="")}&file={f}&paneType=tab'}    # 새 탭(사용자 11-20 «보던 창을 지우고 그 자리를 차지») · 옵시디언 1.15.1 open 처리기 = getLeaf(paneType)


def own_ip(ip):
    """이 PC 에 붙은 주소인가(127.0.0.1 · 이 PC 의 tailnet 주소) — 그 주소로 묶어 보면(bind) 남의 주소는 실패한다."""
    import socket
    if ip in ('', '127.0.0.1', '::1'):
        return True
    try:
        with socket.socket(socket.AF_INET6 if ':' in ip else socket.AF_INET, socket.SOCK_DGRAM) as so:
            so.bind((ip, 0))
        return True
    except OSError:
        return False


def obsidian_front():
    """지금 전경 창이 옵시디언(Obsidian.exe)인가 — /open 탭 닫기 신호. 서버는 콘솔 세션에서 돈다(전경 창을 읽을 수 있음)."""
    import ctypes
    from ctypes import wintypes
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    h = u.GetForegroundWindow()
    if not h:
        return False
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    ph = k.OpenProcess(0x1000, False, pid.value)     # PROCESS_QUERY_LIMITED_INFORMATION
    if not ph:
        return False
    try:
        buf = ctypes.create_unicode_buffer(520)
        n = wintypes.DWORD(520)
        return bool(k.QueryFullProcessImageNameW(ph, 0, buf, ctypes.byref(n))) and os.path.basename(buf.value).lower() == 'obsidian.exe'
    finally:
        k.CloseHandle(ph)


def open_html(rel, err, to, ua):
    """/open 쪽 — 누른 기기(to 또는 User-Agent)의 옵시디언 주소로 바로 넘기고, 못 넘기면 단추 둘."""
    import html as _h
    u = open_urls(rel)
    android = 'android' in ua.lower()
    kind = to if to in ('pc', 'phone') else ('phone' if android or re.search(r'iphone|ipad|mobile', ua, re.I) else 'pc')
    auto = '' if err else (u['intent'] if kind == 'phone' and android else u[kind])
    name = _h.escape(rel.rsplit('/', 1)[-1] or rel)
    msg = f'<p class="err">{_h.escape(err)}: {_h.escape(rel)}</p>' if err else f'<p class="path">{_h.escape(rel)}</p>'
    btn = '' if err else (f'<a class="b" href="{_h.escape(u["intent"] if android else u["phone"])}">폰 옵시디언에서 열기</a>'
                         f'<a class="b" href="{_h.escape(u["pc"])}">PC 옵시디언에서 열기</a>')
    # 넘기기(location.replace)는 맨 끝 대본에 둔다 — 바깥 주소로 넘기면 크롬이 HTML 해석을 멈춰 그 뒤 <script> 는 읽히지도 않는다
    # (11-21 잼: 옛 쪽은 DOM 의 script 1개 · 닫기 대본 없음 → /open/front 0번 · 실제 누름 3번도 0번 · 세 번째 고침 까닭)
    go = ''
    if auto and kind == 'pc':   # 11-20 사용자 «크롬 창이 옵시디언을 연 뒤에도 남음» — 옵시디언이 앞에 오면(서버가 잰 전경 창) 이 탭을 닫음 · 못 닫으면 한 줄
        # blur 는 안 씀: «열기» 묻는 창이 초점을 가져가도 blur 가 올 수 있다(그때 닫으면 옵시디언이 안 열림). 크롬이 바깥 앱 열기를 막은 때
        # (열 때마다 다음 열기는 크롬 페이지 입력이 있어야 풀림 · Chromium g_accept_requests)는 단추를 누르면 열리고 그 뒤에 닫힌다 — 그래서 묻기를 10분 이어 감.
        go += ('<script>(function(){var d=false;function bye(){if(d)return;d=true;setTimeout(function(){window.close();'
               'setTimeout(function(){document.body.insertAdjacentHTML("beforeend","<p class=\\"path\\">옵시디언에서 열었습니다 · 이 탭은 닫아도 됩니다</p>")},400)},300)}'
               'var n=0;function ask(){if(d||n++>=30)return;fetch("/open/front?wait=20",{cache:"no-store"}).then(function(r){return r.json()})'
               '.then(function(j){j&&j.front?bye():ask()},function(){setTimeout(ask,2000)})}setTimeout(ask,300)})()</script>')
    if auto:
        go += f'<script>location.replace({json.dumps(auto)})</script>'
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{name} — 옵시디언으로</title><style>body{{font:16px system-ui,sans-serif;margin:24px;color:#222}}'
            '.path{color:#666;word-break:break-all}.err{color:#b00}.b{display:block;margin:12px 0;padding:14px;border-radius:10px;'
            'background:#7c3aed;color:#fff;text-align:center;text-decoration:none}</style></head>'
            f'<body><h3>{name}</h3>{msg}{btn}{go}</body></html>')


# ───────── 짝짓기(M2 · 11-17) — 열쇠 없이 여는 길은 이 넷뿐 · 코드는 PC 안 대본(pair.py)만 만든다 ─────────
PAIR_GET = ('/pair', '/pair/app', '/pair/plugin')
PAIR_RATE = 30                                      # 열쇠 없는 길 전체 1분 상한(코드 틀림 10번 상한은 pair.py)
_pair_rate = {'t': 0.0, 'n': 0}
_pair_lock = threading.Lock()


def pair_gate():
    with _pair_lock:
        t = time.time()
        if t - _pair_rate['t'] > 60:
            _pair_rate.update(t=t, n=0)
        _pair_rate['n'] += 1
        if _pair_rate['n'] > PAIR_RATE:
            raise Bad(429, '너무 자주')


# ───────── 본 기기(«폰 연결» 붙은 기기 · 준비 목록 plugin·viewer) — tailnet 기기만(PC 안 요청은 안 적음) ─────────
SEEN = os.path.join(STATE, 'seen.json')
SEEN_MAX = 100
_seen = {'d': None}
SEEN_LOCK = threading.Lock()


def seen_mark(path):
    ip = req_ip()
    if not ip or ip in ('127.0.0.1', '::1'):
        return
    kind = 'viewer' if path.startswith('/v1/plugin/brain-source-mobile') else ('app' if req_device() != UNKNOWN_DEVICE else 'obsidian')
    name = req_device() if kind == 'app' else device_here()
    t = time.time()
    with SEEN_LOCK:
        if _seen['d'] is None:
            try:
                with open(SEEN, encoding='utf-8') as f:
                    d = json.load(f)
                _seen['d'] = d if isinstance(d, dict) else {}
            except (OSError, ValueError):
                _seen['d'] = {}
        d, key = _seen['d'], f'{ip}|{kind}'
        cur = d.get(key) if isinstance(d.get(key), dict) else {}
        name = name or cur.get('name')
        ua = getattr(_req, 'ua', '') or cur.get('ua')
        if cur and t - cur.get('at', 0) < 60 and cur.get('name') == name and cur.get('ua') == ua:
            return                                  # 1분 안에 같은 기기 = 파일을 다시 안 씀
        d[key] = {'at': t, **({'name': name} if name else {}), **({'ua': ua} if ua else {})}
        if len(d) > SEEN_MAX:
            for k in sorted(d, key=lambda k: d[k].get('at', 0) if isinstance(d[k], dict) else 0)[:len(d) - SEEN_MAX]:
                d.pop(k, None)
        try:
            os.makedirs(STATE, exist_ok=True)
            with open(SEEN + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(SEEN + '.tmp', SEEN)
        except OSError:
            pass


def ready_post(b):
    try:
        return ready.store(STATE, req_device(), b)
    except ValueError:
        raise Bad(400, '꼴이 잘못됨')


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'brain/0.1'
    sys_version = ''

    def log_message(self, *a):
        pass

    def reply(self, code, obj=None, body=None, ct='application/json; charset=utf-8', headers=None):
        b = body if body is not None else json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.sent = code
        self.send_response(code)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(b)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(b)

    def send_part(self, a, ct, tag, want):
        """파일을 조금씩 읽어 보낸다 — 못 열면 머리를 보내기 전에 오류로 답한다. 머리를 보낸 뒤에는 오류 답을 쓸 수 없으니 연결을 끊는다(폰은 끊김으로 알고 다시 받는다)."""
        with open(a, 'rb') as f:
            st = os.fstat(f.fileno())
            part = byte_range(want, st.st_size)
            start, n = part or (0, st.st_size)
            self.sent = 206 if part else 200
            self.send_response(self.sent)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', str(n))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('ETag', tag)
            self.send_header('X-Mtime', str(int(st.st_mtime)))
            if part:
                self.send_header('Content-Range', f'bytes {start}-{start + n - 1}/{st.st_size}')
            self.end_headers()
            try:
                f.seek(start)
                while n:
                    b = f.read(min(SEND_STEP, n))
                    if not b:                               # 보내는 사이 파일이 줄었다 — 길이를 못 맞춘다
                        self.close_connection = True
                        return
                    self.wfile.write(b)
                    n -= len(b)
            except OSError as e:
                self.close_connection = True
                raise ConnectionError(str(e)) from e

    def authed(self):
        got = (self.headers.get('Authorization') or '').removeprefix('Bearer ').strip()
        return secrets.compare_digest(got.encode('utf-8'), cur_token().encode('utf-8'))

    def handle_one(self, fn, open_=False):
        t0 = time.time()
        code = 200
        why = ''                                    # 4xx 까닭(서버 기록에 · 11-16 «400 이 왜인지 기록에 없음»)
        self.sent = 0
        _req.device = device_of(self.headers.get('X-Brain-Device'))
        _req.ip = ip_of(self.client_address[0], self.headers.get('X-Forwarded-For'))
        _req.ua = (self.headers.get('User-Agent') or '')[:200]   # 기기의 안드로이드·웹뷰 판을 장부(seen.json)에 남기려고
        try:
            if not open_ and not self.authed():     # open_ = 짝짓기 길 넷뿐(짝 코드가 열쇠 노릇 · 코드 없으면 없는 길과 같은 404)
                code = 401
                # 본문을 읽지 않아도 연결을 닫으면 된다
                self.close_connection = True
                return self.reply(401, {'error': '열쇠가 틀림'})
            if not open_:
                seen_mark(urllib.parse.urlparse(self.path).path)
            fn()
        except Bad as e:
            code = e.code
            why = e.msg
            self.refuse(e.code, {'error': e.msg, **e.extra})
        except fileops.Stop as e:
            code = 409
            self.refuse(409, {'error': str(e)})
        except ConnectionError:                     # 폰이 먼저 끊음(앱이 뒤로 감 · 시간 넘김) — 서버 오류가 아니다
            code = 499
            self.close_connection = True
        except Exception as e:  # noqa: BLE001 — 한 요청이 서버를 죽이지 않는다
            code = 500
            log(f'오류 {self.command} {urllib.parse.urlparse(self.path).path} {e!r}')
            self.refuse(500, {'error': type(e).__name__})
        finally:
            log(f'{self.command} {urllib.parse.urlparse(self.path).path} {self.sent if code == 200 and self.sent else code} {int((time.time() - t0) * 1000)}ms' + (f' · {why}' if why else '') + ('' if req_device() == UNKNOWN_DEVICE else f' · {req_device()}'))    # 쿼리는 적지 않는다(찾는 말·경로) · 끝 = 보낸 기기(앱 판 25~)

    def refuse(self, code, obj):
        try:
            self.reply(code, obj)
        except OSError:                             # 답하는 사이에 끊겼다
            self.close_connection = True

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path in PAIR_GET:
            return self.handle_one(self.pair_get, open_=True)
        if urllib.parse.urlparse(self.path).path == '/open':
            return self.handle_one(self.open_page, open_=True)
        if urllib.parse.urlparse(self.path).path == '/open/front':
            return self.handle_one(self.open_front, open_=True)
        self.handle_one(self.get)

    def open_page(self):
        """GET /open?file=<볼트 경로>[&to=pc|phone] — Claude 앱 대화에 단 볼트 링크(https)를 누른 기기의 옵시디언으로 넘기는 쪽(11-20).
        Claude 앱(폰·PC)은 obsidian:// 링크를 누를 수 없게 그린다(사용자 11-20 잼) — https 는 눌리니 여기서 옵시디언 주소로 바꾼다.
        열쇠 없음(브라우저 누름은 머리를 못 붙임) · tailnet 안만(Tailscale serve) · 볼트 안 경로만(clean · 점 폴더·위로 나가기 막음) · 파일 내용은 안 주고 있는지만."""
        pair_gate()
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            rel, a = clean(q.get('file'), ('',))
            err = '' if os.path.exists(a) else '볼트에 없음'
        except Bad as e:
            rel, err = (q.get('file') or '')[:300], e.msg
        body = open_html(rel, err, q.get('to') or '', self.headers.get('User-Agent') or '').encode('utf-8')
        ip = req_ip()
        log(f'볼트 링크 {q.get("to") or ("폰" if re.search(r"android|iphone|ipad|mobile", self.headers.get("User-Agent") or "", re.I) else "PC")} · 주소 {ip}{" (이 PC)" if own_ip(ip) else ""}')   # 11-21 기록엔 누른 기기가 없어 폰·PC 를 못 가름
        return self.reply(200 if not err else 404, body=body, ct='text/html; charset=utf-8',
                          headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Robots-Tag': 'noindex'})

    def open_front(self):
        """GET /open/front?wait=초 — /open 쪽이 «옵시디언이 앞에 왔나»를 묻는다(탭 닫기 신호 · 열쇠 없음 · 참/거짓 하나만 냄).
        wait 동안(≤25초) 0.25초마다 전경 창을 재다 옵시디언이면 바로 답한다 · 이 PC 의 요청만(serve 를 거치면 이 PC 의 tailnet 주소 · 다른 기기 = 없는 길)."""
        pair_gate()
        if not own_ip(req_ip()):
            raise Bad(404, '없음')
        q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
        try:
            wait = max(0.0, min(25.0, float(q.get('wait') or 0)))
        except ValueError:
            wait = 0.0
        end = time.time() + wait
        front = obsidian_front()
        while not front and time.time() < end:
            time.sleep(0.25)
            front = obsidian_front()
        return self.reply(200, {'front': front}, headers={'Cache-Control': 'no-store'})

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path == '/v1/pair':
            return self.handle_one(self.pair_post, open_=True)
        self.handle_one(self.post)

    def pair_get(self):
        """폰 카메라가 연 짝 쪽(/pair) · 공용 APK(/pair/app) · 폰 플러그인 설치 묶음(/pair/plugin) — 살아 있는 짝 코드가 맞을 때만(아니면 없는 길과 같은 404)."""
        pair_gate()
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        c = pairing.check(STATE, q.get('c') or '')
        if not c:
            raise Bad(404, '없는 길')
        apk = os.path.join(STATE, 'app', 'brain-phone', 'brain-phone.apk')
        zp = os.path.join(STATE, 'plugin', 'brain-server', 'brain-server.zip')
        if u.path == '/pair':
            body = pairing.page(q['c'], c.get('base') or '', os.path.isfile(apk), os.path.isfile(zp)).encode('utf-8')
            return self.reply(200, body=body, ct='text/html; charset=utf-8', headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
        a = apk if u.path == '/pair/app' else zp
        if not os.path.isfile(a):
            raise Bad(404, '없는 길')
        ct = 'application/vnd.android.package-archive' if a == apk else 'application/zip'
        return self.send_part(a, ct, etag_of(a), self.headers.get('Range'))

    def pair_post(self):
        """POST /v1/pair {code, name, kind} → {ok, key} — 앱·폰 옵시디언이 «이 PC 에 붙이기» 확인 뒤 부른다(코드 한 번 씀 · 틀림 10번 = 모든 코드 무효)."""
        pair_gate()
        try:
            b = json.loads(self.read_body(4096).decode('utf-8') or '{}')
        except ValueError:
            raise Bad(400, 'JSON 아님')
        if not isinstance(b, dict):
            raise Bad(400, 'JSON 아님')
        name = b.get('name') or (device_here() if b.get('kind') == 'obsidian' else None) or ''    # 폰 옵시디언은 이름을 몰라 같은 주소의 손발 앱 이름으로
        try:
            pairing.use(STATE, b.get('code'), name, b.get('kind'), req_ip())
        except pairing.PairError as e:
            raise Bad(e.code, e.msg)
        log(f"짝짓기 {pairing.KINDS.get(b.get('kind'))} · {' '.join(str(name).split())[:40]}")
        self.reply(200, {'ok': True, 'key': cur_token()})

    def do_PUT(self):
        self.handle_one(self.put)

    def put(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != '/v1/file':
            raise Bad(404, '없는 길')
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        rel, a = bin_for_write(q.get('path'))
        base = (self.headers.get('If-Match') or '').strip()
        if not base:
            raise Bad(428, '판(If-Match) 없음')
        cur = etag_of(a)
        if cur != base:                             # 큰 본문을 받기 전에 — 연결은 닫는다(안 읽은 본문)
            self.close_connection = True
            raise Bad(409, 'PC 판이 바뀜', etag=cur)
        self.reply(200, put_file(rel, a, base, self.read_body(BIN_MAX)))

    def get(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == '/v1/ping':
            warm_soon()             # SSID 를 기다리기 전에 — 곧 올 홈·주제 요청을 미리
            return self.reply(200, ping())
        if u.path == '/v1/search':
            text = (q.get('q') or '').strip()
            if not text:
                raise Bad(400, '찾을 말 없음')
            k = min(int(q.get('k') or 8), 30)
            mode = q.get('mode') if q.get('mode') in ('lexical', 'hybrid') else 'hybrid'
            return self.reply(200, {'q': text, 'items': FIND.search(text, k, mode)})
        if u.path == '/v1/list':
            return self.reply(200, listing(q.get('dir') or ''))
        if u.path == '/v1/home':
            return self.reply(200, phone_home())
        if u.path == '/v1/topic':
            return self.reply(200, phone_topic(q))
        if u.path == '/v1/approve/bundle' and q.get('form') == 'bin':    # 앱 판 36~ · 머리 JSON + 바이트 · gzip(옛 앱 = 아래 JSON 길 그대로)
            res = approve_bundle(q)
            if not res.get('ok') or not isinstance(res.get('items'), list):
                return self.reply(200, res)
            b = approve_bin(res, q.get('have') or '')
            gz = 'gzip' in (self.headers.get('Accept-Encoding') or '')
            if gz:
                import gzip
                b = gzip.compress(b, compresslevel=1)          # 잰 값: 31.6MB → 11.7MB · 0.25초
            return self.reply(200, body=b, ct='application/octet-stream', headers={'Content-Encoding': 'gzip'} if gz else None)
        if u.path in C1_GET:
            return self.reply(200, C1_GET[u.path](q))
        if u.path == '/v1/manual':
            return self.reply(200, manual())
        if u.path == '/v1/push/state':
            return self.reply(200, push_state(q))
        if u.path == '/v1/locks':
            return self.reply(200, locks_get(q))
        if u.path == '/v1/marks':
            return self.reply(200, marks_doc(q))
        if u.path == '/v1/folders':
            return self.reply(200, folders())
        if u.path == '/v1/ready/list':
            return self.reply(200, {'items': ready.items(os.path.join(VAULT, '.claude', 'skills', 'mobility', 'outside.json'))})   # mf:allow-path  (모듈 제 목록 · 글은 한 곳)
        if u.path == '/v1/tabwork':                                   # 탭 곁창 작업 모드 상태(폰 승인 대기·켜짐·거절·만료)
            if tabwork is None:
                return self.reply(200, {'ok': True, 'state': 'ask'})
            try:
                return self.reply(200, tabwork.status(VAULT, q))
            except tabwork.TabWorkError as e:
                raise Bad(e.code, e.msg)
        if u.path in ('/v1/notechat', '/v1/notechat/past'):          # 탭 곁창 — 조각 묻기 · 지난 대화
            try:
                return self.reply(200, notechat_route.poll(q) if u.path == '/v1/notechat' else notechat_route.past(VAULT, q))
            except notechat_route.NoteChatError as e:
                raise Bad(e.code, e.msg)
        if u.path == '/v1/views':
            return self.reply(200, view_list())
        if u.path == '/v1/view':
            return self.reply(200, phone_view(q))
        if u.path == '/v1/format':
            return self.reply(200, phone_format(q))
        if u.path == '/v1/find':
            return self.reply(200, find_sha(q.get('sha256')))
        if u.path == '/v1/resolve':
            return self.reply(200, resolve(q.get('name')))
        if u.path == '/v1/upload':
            return self.reply(200, upload_status(q))
        if u.path == '/v1/schedule':
            return self.reply(200, {'items': schedule_rows(min(int(q.get('days') or 60), 400))})
        if u.path == '/v1/settings':
            return self.reply(200, settings_view())
        if u.path == '/v1/alarms':
            app_seen(self.headers.get('X-Brain-App'), req_device())
            data, tag = alarms.payload(config().get('alarms'))
            try:                                        # 설정 노트 자리 — 앱 «이 기기 알림» 칸의 «잘 시간·당김» 줄이 옵시디언으로 엶(11-18 · 옛 앱은 안 읽음)
                data = json.dumps({**json.loads(data), 'settings': alarms.note_rel('alarm-settings')}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            except Exception as e:
                log(f'alarms settings: {e}')
            if not alarms.load_settings()[0]['켬']:        # 다 끔 — 빈 목록만으론 «마감 없음»과 못 가르니 표시를 더한다(폰이 «다시»로 따로 건 것도 지움)
                data = json.dumps({**json.loads(data), 'off': True}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                tag = tag[:-1] + '-off"'
            elif req_device() != UNKNOWN_DEVICE:      # «이 기기만 끄기»(11-17) — 앱이 울림만 안 울리고 상태 알림은 남긴다 · 값이 바뀌면 태그도
                mute = muted(req_device())
                data = json.dumps({**json.loads(data), 'mute': mute}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                if mute:
                    tag = tag[:-1] + '-mute"'
            try:                                        # 즉시 알림(11-18 시험판) — 붙잡을지 · 방식 · 초 · 지금 seq(폰이 처음 물을 since) · 바뀌면 태그도(304 로 못 받는 일 없게)
                pol = push_policy(req_device())
                data = json.dumps({**json.loads(data), 'push': {**pol, 'seq': alarms.push_seq()}}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                tag = tag[:-1] + push_tag(pol) + '"'
            except Exception as e:
                log(f'alarms push: {e}')
            if self.headers.get('If-None-Match') == tag:
                return self.reply(304, body=b'', headers={'ETag': tag})
            return self.reply(200, body=data, headers={'ETag': tag})
        m = PLUGIN_PATH.fullmatch(u.path)
        if m:
            if m.group(1) == VIEWER_ID and viewer_off():
                raise Bad(404, '폰 보기 꺼짐')       # 기능 단계 mobility.viewer = 끔 — 폰은 표가 없으면 새로 안 깔고 갱신도 멈춘다(깔린 것은 폰에서 끔)
            a = os.path.join(STATE, 'plugin', m.group(1), m.group(2) or 'version.json')
            if not os.path.isfile(a):
                raise Bad(404, '없음')
            if not m.group(2):
                with open(a, 'rb') as f:
                    return self.reply(200, body=f.read())
            ct = {'.css': 'text/css; charset=utf-8', '.wasm': 'application/wasm', '.json': 'application/json; charset=utf-8', '.zip': 'application/zip'}.get(os.path.splitext(a)[1], 'text/javascript; charset=utf-8')
            return self.send_part(a, ct, etag_of(a), self.headers.get('Range'))    # 큰 묶음도 조각으로 · 서버 메모리 고정
        m = APP_PATH.fullmatch(u.path)
        if m:                                           # 폰 앱 자기 갱신(플러그인 판과 같은 방식 · 열쇠는 위에서 이미 봤다)
            a = os.path.join(STATE, 'app', m.group(1), m.group(2) or 'version.json')
            if not os.path.isfile(a):
                raise Bad(404, '없음')
            if not m.group(2):
                with open(a, 'rb') as f:
                    return self.reply(200, body=f.read())
            return self.send_part(a, 'application/vnd.android.package-archive', etag_of(a), self.headers.get('Range'))
        if u.path == '/v1/file':
            rel, a = clean(q.get('path'), READ_ROOTS + DOC_ROOTS)
            if not os.path.isfile(a) or phone_hidden(a):
                to = None if os.path.isfile(a) else moved_to(rel)
                raise Bad(404, '없음', **({'moved': to} if to else {}))      # 옮긴 파일을 옛 경로로 — 폰이 새 자리로 간다(11-23)
            tag = etag_of(a)
            if self.headers.get('If-None-Match') == tag:
                return self.reply(304, body=b'', headers={'ETag': tag})
            ct = 'text/markdown; charset=utf-8' if rel.lower().endswith('.md') else (mimetypes.guess_type(rel)[0] or 'application/octet-stream')
            return self.send_part(a, ct, tag, self.headers.get('Range'))    # 받던 판인지는 폰이 조각마다 ETag 로 본다
        raise Bad(404, '없는 길')

    def too_big(self):
        self.close_connection = True
        return Bad(413, '너무 큼')

    def read_body(self, limit):
        if 'chunked' not in (self.headers.get('Transfer-Encoding') or '').lower():
            n = int(self.headers.get('Content-Length') or 0)
            if n > limit:
                raise self.too_big()
            return self.rfile.read(n)
        out = bytearray()                           # 폰 쪽 통로가 길이 없이 보내도 받는다(본문이 비어 «빈 메모»가 되면 안 된다)
        try:
            while True:
                n = int(self.rfile.readline(64).split(b';')[0], 16)
                if n < 0:
                    raise ValueError
                if not n:
                    while self.rfile.readline(1024).strip():
                        pass
                    return bytes(out)
                if len(out) + n > limit:
                    raise self.too_big()
                out += self.rfile.read(n)
                self.rfile.readline(8)
        except ValueError:
            self.close_connection = True
            raise Bad(400, '본문이 잘못됨')

    def body_pieces(self, n):
        """본문을 SEND_STEP 씩(메모리 고정) — n = Content-Length · None = chunked. 다 오면 self.body_end = True · 끊기면 거기서 멈춘다."""
        self.body_end = False
        if n is not None:
            while n > 0:
                b = self.rfile.read(min(SEND_STEP, n))
                if not b:
                    return
                n -= len(b)
                yield b
            self.body_end = True
            return
        while True:
            line = self.rfile.readline(64)
            if not line:
                return
            k = int(line.split(b';')[0], 16)
            if k < 0:
                raise ValueError
            if not k:
                while self.rfile.readline(1024).strip():
                    pass
                self.body_end = True
                return
            while k > 0:
                b = self.rfile.read(min(SEND_STEP, k))
                if not b:
                    return
                k -= len(b)
                yield b
            self.rfile.readline(8)

    def upload_body(self, q):
        """POST /v1/upload — 본문을 조각 파일(UP_DIR)로 흘려 받으며 해시를 잰다(64MB 상한 대신 PC 남은 자리 · 사용자 11-16).
        offset = 이어 보내는 자리(GET 의 have) · size = 전체. 끊기면 받은 앞부분을 남긴다(TCP 는 순서대로 오니 앞부분은 맞다 · 끝에 sha256 으로 다시 본다)."""
        def stop(e):
            self.close_connection = True            # 본문을 안 읽었다 — 큰 본문을 받기 전에 끊는다
            return e
        try:
            name = upload_name(q.get('name'))
            upload_dir(q.get('to'))                 # 자리를 먼저 — 안 되는 자리면 바이트를 받기 전에 403(조각을 안 남김)
            sha, size, off = upload_args(q)
            n = None if 'chunked' in (self.headers.get('Transfer-Encoding') or '').lower() else int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise stop(Bad(400, '크기가 잘못됨'))
        except Bad as e:
            raise stop(e)
        if size is None and n is not None:
            size = off + n
        if (n is not None and size is not None and off + n > size) or (off and (not sha or size is None)):
            raise stop(Bad(400, '크기가 잘못됨'))
        if size == 0:
            raise stop(Bad(400, '빈 파일'))
        up_sweep()
        key = f'{sha}-{size}' if sha and size is not None else 'one-' + secrets.token_hex(8)
        part = os.path.join(UP_DIR, key + '.part')
        with _up_lock:
            e = _up.setdefault(key, {'lock': threading.Lock(), 'sock': None, 'h': None, 'n': -1})
        if not e['lock'].acquire(blocking=False):
            old = e['sock']                         # 폰이 끊긴 줄 모르고 남은 옛 연결(망 바뀜) — 끊고 이 연결이 잇는다(같은 열쇠 = 같은 내용)
            if old is not None:                     # 윈도는 shutdown 으로 막힌 recv 가 안 깬다(잰 값 20초 그대로) — 손잡이를 바로 닫아 깨운다(0.5초 · 뒤의 close 는 무해)
                try:
                    old.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                _socket.socket.close(old)
            if not e['lock'].acquire(timeout=15):
                raise stop(Bad(409, '받는 중'))
        done = False
        try:
            have = os.path.getsize(part) if os.path.isfile(part) else 0
            if off == 0 and have:                   # 처음부터(묻지 않고 보내는 옛 앱) — 남은 조각을 비운다
                open(part, 'wb').close()
                have, e['n'] = 0, -1
            if off != have:
                raise stop(Bad(409, '받은 자리가 다름', have=have))
            try:
                up_room(size - have if size is not None else 0)
            except Bad as x:
                raise stop(x)
            if e['n'] != have:                      # 서버가 다시 떴다 — 받아 둔 앞부분을 다시 읽어 해시를 잇는다
                e['h'], e['n'] = hashlib.sha256(), 0
                if have:
                    with open(part, 'rb') as f:
                        for b in iter(lambda: f.read(SEND_STEP), b''):
                            e['h'].update(b)
                    e['n'] = have
            got, mark, end = 0, UP_CHECK, False
            e['sock'] = self.connection
            self.connection.settimeout(UP_IDLE)
            try:
                with open(part, 'ab') as f:
                    for b in self.body_pieces(n):
                        f.write(b)
                        f.flush()
                        e['h'].update(b)
                        got += len(b)
                        e['n'] = have + got
                        if got >= mark:
                            mark += UP_CHECK
                            if shutil.disk_usage(UP_DIR).free < UP_MARGIN:
                                raise Bad(507, 'PC 저장 공간 부족', free=shutil.disk_usage(UP_DIR).free, need=(size or 0) - have - got, margin=UP_MARGIN)
                    end = self.body_end
            except Bad as x:
                done = True                         # 받는 사이 PC 가 찼다 — 조각을 지워 자리를 돌려준다
                raise stop(x)
            except ValueError:
                done = True
                raise stop(Bad(400, '본문이 잘못됨'))
            except OSError:                         # 시간 넘김(UP_IDLE) · 폰이 끊음 · 새 연결이 이어 받으려고 끊음
                end = False
            finally:
                e['sock'] = None
                try:
                    self.connection.settimeout(None)
                except OSError:
                    pass
            total = have + got
            if not end:
                self.close_connection = True
                done = key.startswith('one-')        # 이어 받을 열쇠가 없으면 남길 까닭이 없다
                log(f'폰 공유 끊김 {total}/{size}B')
                raise ConnectionError('끊김')
            if size is not None and total < size:  # 나눠 보냄 — 다음 조각을 기다린다
                return self.reply(200, {'ok': True, 'have': total})
            if size is not None and total > size:
                done = True
                raise Bad(400, '크기가 잘못됨')
            try:
                out = upload_finish(name, part, e['h'].hexdigest(), sha, q.get('to'))
            except Bad as x:
                done = x.code == 400                # 해시 다름·빈 파일 = 조각을 버림 · 409(이름 다툼) = 조각을 두고 다시 받는다
                raise
            done = True
            self.reply(200, out)
        finally:
            if done:
                with _up_lock:
                    _up.pop(key, None)
                try:
                    os.remove(part)
                except OSError:
                    pass
            e['lock'].release()

    def post(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        if path == '/v1/upload':                    # 본문 = 파일 바이트(JSON 아님) — 흘려 받는다
            return self.upload_body({k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()})
        if path == '/v1/pdf':                       # 본문 = HTML(JSON 아님) — 폰 «PDF 로 볼트에 저장»·«PDF 로 공유»
            return self.reply(200, make_pdf({k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}, self.read_body(PDF_MAX)))
        raw =self.read_body(DIAG_BODY if path == '/v1/diag' else MAX_BODY)
        try:
            b = json.loads(raw.decode('utf-8') or '{}')
        except ValueError:
            raise Bad(400, 'JSON 아님')
        if path in ('/v1/tabwork/ask', '/v1/tabwork/end'):          # 탭 곁창 작업 모드 — 폰 승인 요청 올림·거둠(켜는 것은 폰 서명뿐)
            if tabwork is None:
                if path == '/v1/tabwork/ask':
                    raise Bad(503, '승인 요청을 못 올림: 작업 모드가 이 판에 없음')
                return self.reply(200, {'ok': True, 'state': 'ask'})
            try:
                res = tabwork.ask(VAULT, b) if path == '/v1/tabwork/ask' else tabwork.end(VAULT, b)
            except tabwork.TabWorkError as e:
                raise Bad(e.code, e.msg)
            approve_forget()                  # 폰 알림·배지가 30초 캐시의 옛 셈을 받지 않게
            log(f'탭 작업 모드 {path.rsplit("/", 1)[-1]} · {str(b.get("session") or "")[:8]} → {res.get("state")} · 기기 {req_device()}')
            return self.reply(200, res)
        if path in ('/v1/notechat', '/v1/notechat/stop'):           # 탭 곁창 — 시작(모델 호출은 이때만)·멈춤
            try:
                return self.reply(200, notechat_route.start(VAULT, b, lambda r: clean(r), phone_hidden) if path == '/v1/notechat' else notechat_route.stop(b))
            except notechat_route.NoteChatError as e:
                raise Bad(e.code, e.msg)
        fn = {'/v1/memo': memo, '/v1/note': note, '/v1/new': new_note, '/v1/schedule': add_schedule, '/v1/schedule/check': check_schedule, '/v1/schedule/merge': merge_schedule, '/v1/diag': diag, '/v1/rc': rc_start, '/v1/alarms/fired': lambda x: alarms.fired(x, None if req_device() == UNKNOWN_DEVICE else req_device()), '/v1/alarms/act': alarm_act, '/v1/rings': rings_check, '/v1/push': push_hold, '/v1/push/ack': push_ack_post, '/v1/push/emit': push_emit_post, '/v1/alarms/power': alarm_power, '/v1/alarms/mute': alarm_mute, '/v1/settings': settings_post,
              '/v1/work/finish': work_finish, '/v1/inbox/do': inbox_do, '/v1/undo': undo, '/v1/fileop': fileop, '/v1/fileops': fileops_many, '/v1/todo/check': todo_check, '/v1/trash/restore': trash_restore, '/v1/ink': ink, '/v1/marks': marks_post, '/v1/lock': lock, '/v1/watch': watch, '/v1/changes': changes_post,
              '/v1/format/set': format_set, '/v1/view/act': view_act, '/v1/ready': ready_post,
              '/v1/approve/sign': approve_sign, '/v1/approve/reject': approve_reject, '/v1/approve/freeze': approve_freeze, '/v1/approve/enroll': approve_enroll}.get(path)
        if not fn:
            raise Bad(404, '없는 길')
        self.reply(200, fn(b))


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = False     # 두 벌이 같은 문을 차지하지 않게 — 이미 돌면 뜨지 않는다


TOKEN_VALUE = ''


# 기록 보존은 코어 예약 «외부뇌 기록 보존»(3_시스템/autocommit.py) 몫이다 — 서버가 예약 없을 때 대신 돌던 순찰은 11-21 뺐다
# (본체 바깥 설정 autocommit-task 가 예약을 재고 등록한다 · mobility 경계 B3).


def bind(port, tries=20, gap=0.5):
    """문 열기 — 옛 서버가 문을 놓기 전에 새로 뜨면(끄고 바로 켬 · 11-16 02:42 예약 결과 1 · 로그 없음) 잠깐 기다려 다시.
    정말 다른 서버가 돌고 있으면 끝내 못 열고 로그 한 줄 뒤 끝낸다(allow_reuse_address 끔 = 두 벌 안 뜸 그대로)."""
    for i in range(tries):
        try:
            return Server(('127.0.0.1', port), H)
        except OSError as e:
            if i == tries - 1:
                log(f'시작 실패 127.0.0.1:{port} — 문이 {tries * gap:.0f}초 동안 쓰이는 중({getattr(e, "winerror", None) or e.errno})')
                raise
            time.sleep(gap)


def main():
    global TOKEN_VALUE
    if len(sys.argv) > 1 and sys.argv[1] == 'token':
        return print(token())
    TOKEN_VALUE = token()
    import nowin
    nowin.install()     # 예약(pyw)으로 돌면 콘솔이 없다 — 요청마다 부르는 git·py·powershell 이 보이는 창을 띄우지 않게(11-17 · nowin.py 머리말)
    port = int(os.environ.get('BRAIN_SERVER_PORT') or config().get('port') or 8377)
    _locks_load()
    try:                # 로그인 전 서버(세션 0 · S4U 예약)가 문을 쥐고 있으면 사용자 세션의 이 서버가 넘겨받는다(자동 재시작 대비책 C · server_swap.py)
        import server_swap
        took = server_swap.take_over()
        if took:
            log(f'로그인 전 서버 넘겨받음 {took}')
    except Exception as e:  # noqa: BLE001 — 넘겨받기가 서버 시작을 막지 않게
        log(f'넘겨받기 건너뜀 {type(e).__name__}: {e}')
    srv = bind(port)
    log(f'시작 127.0.0.1:{port}')

    def sweep():
        while True:
            time.sleep(300)
            FIND.unload_if_idle()
            trim_rc_log()
            if not os.environ.get('BRAIN_SERVER_PORT'):      # 시험 서버는 RC 를 다시 켜지 않는다(시험은 함수를 직접 부름)
                try:
                    rc_frame_tick()
                    rc_nightly()
                except Exception as e:  # noqa: BLE001 — 순찰이 이것 때문에 멈추지 않게
                    log(f'RC 새벽 순찰 오류 {type(e).__name__}: {e}')
                try:
                    rc_seen_tick()
                    rc_net_tick()               # 방금 gone(net)을 적었으면 망이 닿을 때 바로 다시 켬(망이 없으면 다음 순찰)
                except Exception as e:  # noqa: BLE001
                    log(f'RC 봄 순찰 오류 {type(e).__name__}: {e}')
                try:
                    login_tick()
                except Exception as e:  # noqa: BLE001
                    log(f'로그인 순찰 오류 {type(e).__name__}: {e}')
            try:
                pairing.sweep(STATE)            # 만료된 짝 화면 글·브라우저 쪽(pair-show.json · pair.html)을 지운다
            except OSError:
                pass
            if _net['job'] is None:
                refresh_ssid()          # 핑이 SSID 를 기다리지 않게 읽어 둔다(ssid() · 10분 안이면 그 값)
    threading.Thread(target=sweep, daemon=True).start()
    if not os.environ.get('BRAIN_SERVER_PORT'):      # 시험 서버는 RC 를 되살리지 않는다(시험은 함수를 직접 부름)
        def resume():
            try:
                rc_resume()
            except Exception as e:  # noqa: BLE001 — 되살리기가 서버를 멈추지 않게
                log(f'RC 되살리기 오류 {type(e).__name__}: {e}')
        threading.Thread(target=resume, daemon=True, name='rc-resume').start()
    threading.Thread(target=push_watch, daemon=True, name='push-watch').start()     # 즉시 알림 살피기(설정 push 가 없으면 아무것도 안 잼)
    bus_start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
