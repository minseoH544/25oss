from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)


Term = object
Predicate = Tuple[str, ...]
Substitution = Dict[str, Term]


def is_variable(term: Term) -> bool:
    return isinstance(term, str) and term.startswith("?")


def substitute(expr: Term, subs: Substitution) -> Term:
    if isinstance(expr, str):
        return subs.get(expr, expr)
    if isinstance(expr, tuple):
        return tuple(substitute(part, subs) for part in expr)
    return expr


def occurs_check(var: str, value: Term, subs: Substitution) -> bool:
    if var == value:
        return True
    if isinstance(value, str) and is_variable(value) and value in subs:
        return occurs_check(var, subs[value], subs)
    if isinstance(value, tuple):
        return any(occurs_check(var, part, subs) for part in value)
    return False


def unify(x: Term, y: Term, subs: Optional[Substitution] = None) -> Optional[Substitution]:
    # === QUIZ: implement recursive unification ===
    if subs is None:
        subs = {}

        # 1. 두 값이 같으면 현재 치환 반환
    if x == y:
        return subs
        # 2. x가 변수면 변수 바인딩 시도
    elif is_variable(x):
        return unify_var(x, y, subs)
        # 3. y가 변수면 변수 바인딩 시도
    elif is_variable(y):
        return unify_var(y, x, subs)
        # 4. 둘 다 튜플이고 길이가 같으면 내부 요소들 유니파이
    elif isinstance(x, tuple) and isinstance(y, tuple) and len(x) == len(y):
        for xi, yi in zip(x, y):
            subs = unify(xi, yi, subs)
            if subs is None: return None
        return subs
    return None


def unify_var(var: str, value: Term, subs: Substitution) -> Optional[Substitution]:
    # === QUIZ: handle variable binding during unification ===
    if var in subs:
        return unify(subs[var], value, subs)
    if is_variable(value) and value in subs:
        return unify(var, subs[value], subs)
    if occurs_check(var, value, subs):
        return None

    new_subs = subs.copy()
    new_subs[var] = value
    return new_subs

def is_ground(fact: Predicate) -> bool:
    return all(not (isinstance(arg, str) and is_variable(arg)) for arg in fact)


def is_exists(expr: Term) -> bool:
    return isinstance(expr, tuple) and len(expr) == 3 and expr[0] == "EXISTS"


@dataclass
class Rule:
    variables: Tuple[str, ...]
    premises: Tuple[Predicate, ...]
    conclusion: Term


class KB:
    def __init__(
        self,
        facts: Optional[Iterable[Predicate]] = None,
        rules: Optional[Iterable[Term]] = None,
    ) -> None:
        self.facts: Set[Predicate] = set()
        self.rules: List[Rule] = []
        self._exist_counter = 0

        if facts:
            for f in facts: self.add_fact(f)
        if rules:
            for r in rules: self.add_rule(r)

    def add_fact(self, fact: Predicate) -> bool:
        if fact in self.facts:
            return False
        self.facts.add(fact)
        return True

    def add_rule(self, rule: Term) -> None:
        parsed = rule if isinstance(rule, Rule) else self._parse_rule(rule)
        self.rules.append(parsed)

    def forward_chain(self, max_iterations: int = 50) -> None:
        # === QUIZ: repeatedly apply rules and grow the fact set ===
        for _ in range(max_iterations):
            new_facts_this_step = set()

            for rule in self.rules:
                for theta in self._satisfying_substitutions(rule.premises):
                    conclusion = substitute(rule.conclusion, theta)

                    if is_exists(conclusion):
                        # 1. 존재 조건 패턴 추출: ('EXISTS', ['?y'], ('loves', 'mia', '?y'))
                        # conclusion[2]는 ('loves', 'mia', '?y') 형태임
                        pattern = conclusion[2]

                        # 2. 이미 해당 조건을 만족하는 사실이 있는지 확인
                        # 예: loves(mia, _sk1)이 이미 있다면 쿼리 결과가 존재함
                        if self.query(pattern):
                            continue  # 이미 만족되었으므로 새로운 스코렘 생성을 건너뜀

                        # 3. 만족되지 않았을 때만 새로운 스코렘 상수 생성
                        fact = self._instantiate_exists(conclusion)
                    else:
                        fact = conclusion

                    if is_ground(fact) and fact not in self.facts:
                        new_facts_this_step.add(fact)

            if not new_facts_this_step:
                break

            added_any = False
            for f in new_facts_this_step:
                if self.add_fact(f):
                    added_any = True

            if not added_any:
                break

    def query(self, pattern: Predicate) -> List[Substitution]:
        # === QUIZ: perform pattern matching against known facts ===
        results = []
        for fact in self.facts:
            subs = unify(pattern, fact, {})
            if subs is not None:
                results.append(subs)
        return results

    def _satisfying_substitutions(self, premises: Sequence[Predicate]) -> Iterator[Substitution]:
        # === QUIZ: backtracking search for substitutions that satisfy premises ===
        def backtrack(idx: int, current_subs: Substitution):
            if idx == len(premises):
                yield current_subs
                return

            p = substitute(premises[idx], current_subs)
            # self.facts 대신 list(self.facts)를 사용하여 반복 중 변경 에러 방지
            for fact in list(self.facts):
                new_subs = unify(p, fact, current_subs)
                if new_subs is not None:
                    yield from backtrack(idx + 1, new_subs)

        return backtrack(0, {})

    def _instantiate_exists(self, expr: Term) -> Predicate:
        # === QUIZ: skolemize existential quantifiers ===
        vars_to_skolem = expr[1]
        inner_expr = expr[2]

        subs = {}
        for var in vars_to_skolem:
            self._exist_counter += 1
            subs[var] = f"_sk{self._exist_counter}"

        return substitute(inner_expr, subs)

    def _parse_rule(self, expr: Term) -> Rule:
        # === QUIZ: convert a FORALL/IMPLIES expression into a Rule dataclass ===
        if not isinstance(expr, tuple) or expr[0] != "FORALL":
            raise ValueError("Rule must start with FORALL")

        variables = tuple(expr[1])
        implies_part = expr[2]

        if implies_part[0] != "IMPLIES":
            raise ValueError("Inner part must be IMPLIES")

        premises = self._normalize_premises(implies_part[1])
        conclusion = implies_part[2]

        return Rule(variables, premises, conclusion)

    def _normalize_premises(self, raw: Term) -> Tuple[Predicate, ...]:
        # === QUIZ: normalize raw premises into a tuple of predicates ===
        if isinstance(raw, list):
            return tuple(raw)
        return (raw,)


__all__ = ["KB", "Rule", "unify", "substitute", "is_variable"]