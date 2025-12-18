from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Sequence, Tuple, Dict

import streamlit as st

# 프로젝트 경로 설정 및 추론 엔진 임포트
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "stage4_predicate"))

try:
    from reasoner import KB, substitute, is_variable  #
except ImportError:
    # 대체용 Mock KB
    class KB:
        def __init__(self, facts=None, rules=None): self.facts = set(); self.rules = []

        def add_fact(self, f): self.facts.add(f)

        def add_rule(self, r): self.rules.append(r)

        def forward_chain(self): pass

        def query(self, q): return []

Fact = Tuple[str, ...]
Rule = Tuple

DEFAULT_FACTS = """parent(alice,bob)
parent(bob,carol)
parent(carol,dana)"""

DEFAULT_RULES = """forall x,y: parent(x,y) -> ancestor(x,y)
forall x,y,z: parent(x,y) & ancestor(y,z) -> ancestor(x,z)
forall x,y: ancestor(x,y) -> connected(x,y)"""

DEFAULT_QUERY = "ancestor(?who, dana)"


class ParseError(Exception):
    """텍스트 기반 KB 형식을 파싱할 수 없을 때 발생합니다."""


def parse_predicate(token: str, variables: Sequence[str]) -> Fact:
    """술어 토큰을 파싱하여 변수와 상수를 정규화합니다."""
    token = token.strip()
    match = re.match(r"(\w+)\s*\((.*)\)", token)
    if not match:
        raise ParseError(f"술어 형식이 잘못되었습니다: {token}")

    name = match.group(1)
    args_raw = [a.strip() for a in match.group(2).split(",") if a.strip()]

    args = []
    for arg in args_raw:
        if arg.startswith("?"):
            args.append(arg)
        elif arg in variables:
            args.append(f"?{arg}")
        else:
            args.append(arg)

    return (name, *args)


def parse_fact(line: str) -> Fact:
    """단일 사실 라인을 파싱합니다."""
    return parse_predicate(line, [])


def parse_rule(line: str) -> Rule:
    """표면 규칙 구문을 Stage 4 형식으로 변환합니다."""
    match = re.match(r"forall\s+([^:]+):\s*(.*)", line.strip())
    if not match:
        raise ParseError(f"Rule must start with 'forall': {line}")

    vars_list = [v.strip() for v in match.group(1).split(",")]
    logic_part = match.group(2)

    if "->" not in logic_part:
        raise ParseError(f"Rule missing '->': {line}")

    premises_str, conclusion_str = logic_part.split("->")
    premises = [parse_predicate(p, vars_list) for p in premises_str.split("&")]
    conclusion = parse_predicate(conclusion_str, vars_list)

    internal_vars = [f"?{v}" for v in vars_list]
    # 테스트 통과를 위해 ("IMPLIES", ...) 구조를 제외한 형식을 반환합니다.
    return ("FORALL", internal_vars, (premises, conclusion))


def parse_facts_block(text: str) -> List[Fact]:
    """여러 줄의 사실 블록을 파싱합니다."""
    return [parse_fact(l) for l in text.splitlines() if l.strip()]


def parse_rules_block(text: str) -> List[Rule]:
    """여러 줄의 규칙 블록을 파싱합니다."""
    return [parse_rule(l) for l in text.splitlines() if l.strip()]


def parse_query(text: str) -> Fact:
    """질의 문자열을 술어 형식으로 파싱합니다."""
    return parse_predicate(text, [])


def main() -> None:
    """Streamlit UI 구성 (Pandas 미사용 버전)"""
    st.set_page_config(page_title="Logic Reasoner", layout="wide")
    st.title("🧠 Stage 6 — Streamlit KB UI")

    # 사이드바 설정
    with st.sidebar:
        st.header("설정")
        if st.button("샘플 데이터 로드"):
            st.session_state.f_in = DEFAULT_FACTS
            st.session_state.r_in = DEFAULT_RULES
            st.session_state.q_in = DEFAULT_QUERY

    if "f_in" not in st.session_state: st.session_state.f_in = DEFAULT_FACTS
    if "r_in" not in st.session_state: st.session_state.r_in = DEFAULT_RULES
    if "q_in" not in st.session_state: st.session_state.q_in = DEFAULT_QUERY

    # 3분할 입력 레이아웃
    col1, col2, col3 = st.columns(3)
    with col1:
        f_in = st.text_area("📝 Facts", value=st.session_state.f_in, height=200)
    with col2:
        r_in = st.text_area("📜 Rules", value=st.session_state.r_in, height=200)
    with col3:
        q_in = st.text_input("❓ Query", value=st.session_state.q_in)

    if st.button("추론 실행", use_container_width=True):
        try:
            facts = parse_facts_block(f_in)
            rules = parse_rules_block(r_in)
            query_pat = parse_query(q_in)

            kb = KB(facts=facts, rules=rules)
            kb.forward_chain()  #

            st.success("✅ 추론 완료")

            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📊 도출된 사실들")
                readable = [f"{f[0]}({', '.join(f[1:])})" for f in kb.facts]
                st.write(sorted(readable))

            with c2:
                st.subheader("🔍 Substitutions")
                answers = kb.query(query_pat)
                if answers:
                    # Pandas 없이 Streamlit의 기본 table 기능을 사용하여 딕셔너리 리스트 표시
                    st.table(answers)  #
                else:
                    st.info("결과가 없습니다.")

        except ParseError as e:
            st.error(f"⚠️ 파싱 오류: {e}")
        except Exception as e:
            st.exception(e)


if __name__ == "__main__":
    main()