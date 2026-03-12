from clingo.control import Control
from clingo import Function
from typing import List
import time, re, sys

import re

def parse_grid_file(filename):
    data = {}
    pattern = re.compile(r'(\w+)\((\d+),\s*(\d+)\)\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)')

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                name = match.group(1)
                x = match.group(2)
                y = match.group(3)
                value = float(match.group(4))

                key = f"{name}({x},{y})"
                data[key] = value

    return data

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, Tuple
import math

import clingo
from clingo import Symbol
PredProb = Tuple[str, float]  # ("digit_1(1)", 0.8)

def run_clingo_pacman(program: str, pred_probs: Sequence[PredProb]):
    def _parse_atom(atom_str: str) -> Symbol:
        """
        Parse "digit_1(1)" into a clingo Symbol.
        """
        s = atom_str.strip()
        # clingo.parse_term is the easiest and robust way
        if hasattr(clingo, "parse_term"):
            return clingo.parse_term(s)  # type: ignore[attr-defined]
        # fallback: let clingo's parser parse an atom via a tiny program
        raise RuntimeError("clingo.parse_term is not available in this clingo build.")
    
    def prob_to_weight(p: float, *, scale: int = 10000, eps: float = 1e-12) -> int:
        """
        Integer weight for weak constraints / minimize:
          weight = round(-log(p) * scale)
        Higher p => smaller penalty.
        """
        p2 = min(max(float(p), eps), 1.0)
        return int(round(-math.log(p2) * scale))
    
    def _lit_of(self, sym: Symbol) -> int:
        sa = self.ctl.symbolic_atoms[sym]
        if sa is None:
            raise RuntimeError(f"Atom {sym} not found in grounded program")
        return sa.literal
    
    clingo_control = Control(['--warn=none', '--opt-mode=optN', '0', '--stats=2'])
    signature = set({"actor", "goal", "grid_node", "shortest_path"})
    grid_size = 5

    time1 = time.perf_counter()
    clingo_control.add("base", [], program)
    clingo_control.ground([("base", [])])
    # print(f"grounding time: {time.perf_counter() - time1}")

    minimize_terms: List[Tuple[int, int]] = []
    assumptions: List[Tuple[Symbol, bool]] = []
    for atom_s, p in pred_probs:
        sym = _parse_atom(atom_s)
        lit = clingo_control.symbolic_atoms[sym].literal
        if p > 0.01:
            w = prob_to_weight(p)
            minimize_terms.append((lit, w))
        else:
            assumptions.append(-lit)

    with clingo_control.backend() as b:
        b.add_minimize(1, minimize_terms)

    models = [] 
    new_models = []
    sp_covered = set()
    sp_expanded = set()

    def on_model_func(m):
        global ncalls, cnt
        # print([str(atom) for atom in m.symbols(atoms=True) if atom.name in signature], f"cost: {m.cost}")
        new_models.append(([str(atom) for atom in m.symbols(atoms=True) if atom.name in signature], m.cost))


    i = 0
    best_solution = None
    pat = re.compile(r"^\w+\(\s*(-?\d+)\s*\)$")
    time1 = time.perf_counter()
    done = False
    num_choice = 0
    num_conflict = 0
    while True:
        i += 1
        new_models.clear()
        for sp_len in list(sp_expanded):
            sym = _parse_atom(f"shortest_path({sp_len})")
            if clingo_control.symbolic_atoms[sym] != None:
                lit = clingo_control.symbolic_atoms[sym].literal
                assumptions.append(-lit)

        time1 = time.perf_counter()
        clingo_control.solve(assumptions = assumptions, on_model = on_model_func)
        # print(f"c {i}-th clingo_control.solve time: {time.perf_counter() - time1}")
        num_choice += clingo_control.statistics['solving']['solvers']['choices']
        num_conflict += clingo_control.statistics['solving']['solvers']['conflicts']

        if len(new_models) == 0:
            # print("ctl.statistics keys:", clingo_control.statistics['problem']['lp'])
            break
        
        index = 0

        for model in new_models[::-1]:
            index += 1
            if index > 4:
                break
            for atom in model[0]:
                if atom.startswith("shortest_path"):
                    m = pat.match(atom)
                    sp_length = int(m.group(1))
                    
                    if sp_length in sp_covered:
                        break
                    models.append(model[0])
                    sp_covered.add(sp_length)

                    for length in range(sp_length, grid_size * grid_size, 2):
                        sp_expanded.add(length)
        
        if 1 in sp_expanded and 2 in sp_expanded:
            break

    # print(f"Num choice: {num_choice}, Num conflict: {num_conflict}")
    return models, num_choice, num_conflict



@dataclass
class SolveOutput:
    sat: bool
    optimal: bool
    cost: Optional[List[int]]
    shown: List[Symbol]


class ClingoRunner:
    """
    Ground once, then repeatedly:
      - (optional) forbid low-prob atoms via assumptions  (equiv. ':- atom.')
      - rebuild the objective from (predicate,prob) pairs without regrounding
      - solve

    NOTE: The predicates you pass (e.g., "digit_1(1)") must exist in the grounded program.
    """

    def __init__(
        self,
        *,
        program_text: Optional[str] = None,
        program_file: Optional[str] = None,
        ground_parts: Optional[List[Tuple[str, List[Any]]]] = None,
    ):
        if program_text is None and program_file is None:
            raise ValueError("Provide program_text or program_file")

        self.ctl = Control(['--warn=none', '--opt-mode=optN', '0', '--stats=2'])
        if program_file is not None:
            self.ctl.load(program_file)
        if program_text is not None:
            self.ctl.add("base", [], program_text)

        self.ctl.ground(ground_parts or [("base", [])])

        # optional convenience: keep only one model
        try:
            self.ctl.configuration.solve.models = 2
        except Exception:
            pass

    def _parse_atom(self, atom_str: str) -> Symbol:
        """
        Parse "digit_1(1)" into a clingo Symbol.
        """
        s = atom_str.strip()
        # clingo.parse_term is the easiest and robust way
        if hasattr(clingo, "parse_term"):
            return clingo.parse_term(s)  # type: ignore[attr-defined]
        # fallback: let clingo's parser parse an atom via a tiny program
        raise RuntimeError("clingo.parse_term is not available in this clingo build.")

    def _lit_of(self, sym: Symbol) -> int:
        sa = self.ctl.symbolic_atoms[sym]
        if sa is None:
            raise RuntimeError(f"Atom {sym} not found in grounded program")
        return sa.literal

    @staticmethod
    def prob_to_weight(p: float, *, scale: int = 1000, eps: float = 1e-12) -> int:
        """
        Integer weight for weak constraints / minimize:
          weight = round(-log(p) * scale)
        Higher p => smaller penalty.
        """
        p2 = min(max(float(p), eps), 1.0)
        return int(round(-math.log(p2) * scale))
    
    def run_clingo_pacman(self, pred_probs: Sequence[PredProb]):
        def _parse_atom(atom_str: str) -> Symbol:
            """
            Parse "digit_1(1)" into a clingo Symbol.
            """
            s = atom_str.strip()
            # clingo.parse_term is the easiest and robust way
            if hasattr(clingo, "parse_term"):
                return clingo.parse_term(s)  # type: ignore[attr-defined]
            # fallback: let clingo's parser parse an atom via a tiny program
            raise RuntimeError("clingo.parse_term is not available in this clingo build.")
        
        def prob_to_weight(p: float, *, scale: int = 10000, eps: float = 1e-12) -> int:
            """
            Integer weight for weak constraints / minimize:
            weight = round(-log(p) * scale)
            Higher p => smaller penalty.
            """
            p2 = min(max(float(p), eps), 1.0)
            return int(round(-math.log(p2) * scale))
        
        def _lit_of(self, sym: Symbol) -> int:
            sa = self.ctl.symbolic_atoms[sym]
            if sa is None:
                raise RuntimeError(f"Atom {sym} not found in grounded program")
            return sa.literal
        
        signature = set({"actor", "goal", "grid_node", "shortest_path"})
        grid_size = 5

        time1 = time.perf_counter()
        # self.ctl.add("base", [], program)
        # self.ctl.ground([("base", [])])
        # print(f"grounding time: {time.perf_counter() - time1}")
        self.ctl.remove_minimize()

        minimize_terms: List[Tuple[int, int]] = []
        assumptions: List[Tuple[Symbol, bool]] = []
        for atom_s, p in pred_probs:
            sym = _parse_atom(atom_s)
            lit = self.ctl.symbolic_atoms[sym].literal
            if p > 0.01:
                w = prob_to_weight(p)
                minimize_terms.append((lit, w))
            else:
                assumptions.append(-lit)

        with self.ctl.backend() as b:
            b.add_minimize(1, minimize_terms)

        models = [] 
        new_models = []
        sp_expanded = set()
        sp_covered = set()
        pat = re.compile(r"^\w+\(\s*(-?\d+)\s*\)$")

        def on_model_func(m):
            global ncalls, cnt
            # print([str(atom) for atom in m.symbols(atoms=True) if atom.name in signature], f"cost: {m.cost}")
            new_models.append(([str(atom) for atom in m.symbols(atoms=True) if atom.name in signature], m.cost))

        i = 0
        pat = re.compile(r"^\w+\(\s*(-?\d+)\s*\)$")
        num_choice = 0
        num_conflict = 0
        while True:
            i += 1
            new_models.clear()
            for sp_len in list(sp_expanded):
                sym = _parse_atom(f"shortest_path({sp_len})")
                if self.ctl.symbolic_atoms[sym] != None:
                    lit = self.ctl.symbolic_atoms[sym].literal
                    assumptions.append(-lit)

            time1 = time.perf_counter()
            self.ctl.solve(assumptions = assumptions, on_model = on_model_func)
            # print(f"c {i}-th clingo_control.solve time: {time.perf_counter() - time1}")
            num_choice += self.ctl.statistics['solving']['solvers']['choices']
            num_conflict += self.ctl.statistics['solving']['solvers']['conflicts']

            if len(new_models) == 0:
                # print("ctl.statistics keys:", clingo_control.statistics['problem']['lp'])
                break
            
            index = 0

            for model in new_models[::-1]:
                index += 1
                if index > 4:
                    break
                for atom in model[0]:
                    if atom.startswith("shortest_path"):
                        m = pat.match(atom)
                        sp_length = int(m.group(1))
                        
                        if sp_length in sp_covered:
                            break
                        models.append(model[0])
                        sp_covered.add(sp_length)

                        for length in range(sp_length, grid_size * grid_size, 2):
                            sp_expanded.add(length)
            
            if 1 in sp_expanded and 2 in sp_expanded:
                break
            # print(f"solving time: {time.perf_counter() - time1}")
            # print(f"Num choice: {num_choice}, Num conflict: {num_conflict}")
            
        return models, num_choice, num_conflict

# ---------------- Example ----------------
if __name__ == "__main__":
    PROGRAM = None
    dir_name = "inputs"
    var_list = []
    num_step = 10
    num_test = 32
    literal_list = []
    with open('pacman_base.lp', 'r') as file:
        PROGRAM = file.read()

    for i in range(5):
        for j in range(5):
            var_list.append(f"actor({i},{j})")
            var_list.append(f"goal({i},{j})")
            var_list.append(f"enemy({i},{j})")

    runner = ClingoRunner(program_text=PROGRAM)
    inc = False
    if len(sys.argv) >= 2:
        inc = True
    if inc:
        for i in range(1, num_step + 1):
            time_start = time.perf_counter()
            num_test_done = 0
            conf_num = 0
            choice_num = 0
            model_num = 0
            for file_num in range(num_test):
                file_name = f"{dir_name}/instance_{i}_{file_num}.txt"
                num_test_done = num_test_done + 1
                literal_list.clear()

                probs = parse_grid_file(file_name)

                for var in var_list:
                    if var.startswith("actor") or var.startswith("goal"):
                        if var in probs:
                            literal_list.append((var, probs[var]))
                        else:
                            literal_list.append((var, 0))
                    else:
                        var2 = var.replace("enemy","grid_node")
                        if var in probs:
                            literal_list.append((var2, (1 - probs[var]) * 0.95))
                        else:
                            literal_list.append((var2, 0.95))

                ret, nconflict, nchoice = runner.run_clingo_pacman(pred_probs=literal_list)
                choice_num += nchoice
                conf_num += nconflict
                model_num += len(ret)
                # print(ret)

            print(f"{i}-th iteration [Incremental]: solving time: {round(time.perf_counter() - time_start, 4)}, choices: {choice_num},  conflict: {conf_num}")
    else:
        # non incremental mode
        print("Non incremental mode")
        for i in range(1, num_step + 1):
            time_start = time.perf_counter()
            num_test_done = 0
            conf_num = 0
            choice_num = 0
            model_num = 0
            for file_num in range(num_test):
                file_name = f"{dir_name}/instance_{i}_{file_num}.txt"
                num_test_done = num_test_done + 1
                literal_list.clear()

                probs = parse_grid_file(file_name)

                for var in var_list:
                    if var.startswith("actor") or var.startswith("goal"):
                        if var in probs:
                            literal_list.append((var, probs[var]))
                        else:
                            literal_list.append((var, 0))
                    else:
                        var2 = var.replace("enemy","grid_node")
                        if var in probs:
                            literal_list.append((var2, (1 - probs[var]) * 0.95))
                        else:
                            literal_list.append((var2, 0.95))

                ret, nconflict, nchoice  = run_clingo_pacman(PROGRAM, pred_probs=literal_list)
                choice_num += nchoice
                conf_num += nconflict
                model_num += len(ret)
                # print(ret)

            print(f"{i}-th iteration [Non-incremental]: solving time: {round(time.perf_counter() - time_start, 4)}, choices: {choice_num},  conflict: {conf_num}")
