"""mobility 설정 한 곳 — 개인 값 파일(config.json · git 밖)과 조리법 기본값(모듈 setup.json)을 읽는다(LLM 0 · 쓰기 없음).

  py -3 .claude/skills/mobility/scripts/conf.py port [--vault V]    # 서버 문 번호 = config «port» → 없으면 조리법 기본값

개인 값 파일 = <볼트>/3_시스템/_index/server/config.json(처음 설정 setup.py apply 가 채움 · 예시 = 모듈 config.example.json).
서버(server.py)·등록 대본(server-setup.ps1)·바깥 설정 재기(pc_state.py)·조리법(setup.py)이 문 번호를 여기 한 곳에서 읽는다.
server.py 는 아직 자기 줄(config «port» → 8377)로 읽는다 — 그 8377 이 조리법 기본값과 같은지는 setup_check 가 잰다.
"""
import json
import os
import sys

MOD = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(MOD)
RECIPE = os.path.join(MODULE, "setup.json")


def vault_of(vault=None):
    return os.path.abspath(vault) if vault else os.path.abspath(os.path.join(MOD, "..", "..", "..", ".."))


def config_path(vault=None):
    return os.path.join(vault_of(vault), "3_시스템", "_index", "server", "config.json")


def load(vault=None):
    """개인 값 — 없거나 깨지면 {}(서버와 같은 동작)."""
    try:
        with open(config_path(vault), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def recipe():
    with open(RECIPE, encoding="utf-8") as f:
        return json.load(f)


def default(item_id):
    for it in recipe().get("항목", []):
        if it.get("id") == item_id:
            return it.get("기본값")
    raise KeyError(item_id)


def port(vault=None):
    v = load(vault).get("port")
    if type(v) is int and 1024 <= v <= 65535:
        return v
    return int(default("port"))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    vault = args[args.index("--vault") + 1] if "--vault" in args else None
    if args[:1] == ["port"]:
        print(port(vault))
        return 0
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main())
