from __future__ import annotations

from itertools import combinations, product
from timeit import default_timer as timer
from typing import Dict, Iterable, List, Set

from src.exceptions import InvalidCellValue, InvalidSudoku
from src.util import *


class Sudoku:
    def __init__(self, cells: List[int] = None, name: str = "Sudoku"):
        if cells is None:
            cells = [0] * 81
        self.set_cells(cells)
        self.candidates = [set() for _ in range(81)]
        self.name = name

    def get_cell(self, r: int, c: int) -> int:
        return self.cells[cell_index(r, c)]

    def set_cells(self, cells: List[int]):
        if len(cells) != 81:
            raise InvalidSudoku()

        for cell in cells:
            if not valid_cell_value(cell):
                raise InvalidCellValue()

        self.cells = cells

    def place_cell(self, i: int, value: int):
        self.cells[i] = value
        self.candidates[i] = set()
        self.eliminate_candidates(value, i)

    def unset_cell(self, r: int, c: int):
        self.set_cell(r, c, 0)

    def row(self, r: int) -> List[int]:
        return self.cells[r * 9:r * 9 + 9]

    def column(self, c: int) -> List[int]:
        return self.cells[c::9]

    def box(self, n: int) -> List[int]:
        block_r = n // 3
        block_c = n % 3
        c_start = block_c * 3
        c_end = c_start + 3
        cells = []
        for r in range(block_r * 3, block_r * 3 + 3):
            cells.extend(self.row(r)[c_start:c_end])
        return cells

    def eliminate_candidates(self, value: int, i: int = None, r: int = None, c: int = None, b: int = None) -> int:
        if value == 0:
            return 0
        cnt = 0
        if i is not None:
            r, c, b = position(i)
        if r is not None:
            cnt += self.eliminate_candidates_of_indices(row_indices(r), value)
        if c is not None:
            cnt += self.eliminate_candidates_of_indices(
                column_indices(c), value)
        if b is not None:
            cnt += self.eliminate_candidates_of_indices(box_indices(b), value)
        return cnt

    def eliminate_candidates_of_indices(self, indices: Iterable[int], value: int) -> int:
        cnt = 0
        for i in indices:
            if value in self.candidates[i]:
                self.candidates[i].remove(value)
                cnt += 1
        return cnt

    def compute_candidates(self, i: int = None) -> Set[int]:
        if i is None:
            for i in range(81):
                self.compute_candidates(i)
            return
        r, c, b = position(i)
        if self.cells[i] != 0:
            return
        row = set(self.row(r))
        column = set(self.column(c))
        box = set(self.box(b))
        candidates = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        candidates = candidates - row - column - box
        self.candidates[i] = candidates
        return candidates

    def solve_hidden_singles(self) -> int:
        '''
            Solve hidden singles in row, column and box. Repeat until no more hidden singles are found.
        '''

        def solve_hidden_singles_of_indices(indices: List[str]) -> int:
            '''
                Find a cell with unique candidate in a list of cells.
            '''
            candidates_sets: List[Set[int]] = [self.candidates[i]
                                               for i in indices if len(self.candidates[i]) >= 1]

            if len(candidates_sets) == 0:
                return 0

            cnt = 0
            for i in indices:
                candidates = set(self.candidates[i])

                # Check if it has a unique candidate in the area
                if len(candidates) > 1:
                    other_sets = [s for s in candidates_sets if s is not self.candidates[i]] or [set()]
                    other_candidates = set.union(*other_sets)
                    candidates -= other_candidates

                # If it has a unique candidate, place it
                if len(candidates) == 1:
                    cnt += 1
                    self.place_cell(i, candidates.pop())
            return cnt

        cnt = 0
        for i in range(9):
            cnt += solve_hidden_singles_of_indices(box_indices(i))
            cnt += solve_hidden_singles_of_indices(row_indices(i))
            cnt += solve_hidden_singles_of_indices(column_indices(i))

        if cnt > 0:
            cnt += self.solve_hidden_singles()

        return cnt

    def count_candidates(self, indices: Iterable[int]) -> Dict[int, int]:
        d = {}
        sets = [self.candidates[i] for i in indices]
        for s in sets:
            for n in s:
                d[n] = d.get(n, 0) + 1
        return d

    def pointing_pair(self) -> int:
        """
            For each column in each box, check if they have numbers that does not belong to other columns in the box,
            then eliminate candidates of that number in that column of other boxes.

            Same applied for rows.
        """
        cnt = 0
        for b in range(9):
            bi = box_indices(b)
            box_candidates_count = self.count_candidates(bi)

            # Scan rows in box
            for br in range(3):
                rbi = query_indices(r=br, b=b)
                r = b // 3 * 3 + br
                ri = row_indices(r=r)
                rb_candidates_count = self.count_candidates(rbi)
                other_rb_indices = list(set(ri) - set(rbi))
                for k, v in rb_candidates_count.items():
                    if box_candidates_count[k] == v:
                        cnt += self.eliminate_candidates_of_indices(
                            other_rb_indices, k)

            # Scan columns in box
            for bc in range(3):
                cbi = query_indices(c=bc, b=b)
                c = b % 3 * 3 + bc
                ci = column_indices(c=c)
                cb_candidates_count = self.count_candidates(cbi)
                other_cb_indices = list(set(ci) - set(cbi))
                for k, v in cb_candidates_count.items():
                    if box_candidates_count[k] == v:
                        cnt += self.eliminate_candidates_of_indices(
                            other_cb_indices, k)
        return cnt

    def box_line_reduction(self) -> int:
        """
            For each column, if there is a pair or triple in the same box, eliminate that candidate from the rest of the box.

            Same applied for each row.
        """
        cnt = 0
        for r in range(9):
            candidate_counts = self.count_candidates(row_indices(r))
            for k, v in candidate_counts.items():
                if v not in (2, 3):
                    continue
                _indices = set(i for i in row_indices(
                    r) if k in self.candidates[i])

                _positions = [position(i) for i in _indices]
                _boxes = set(p[2] for p in _positions)
                if len(_boxes) != 1:
                    continue
                b = _boxes.pop()
                bi = set(box_indices(b)) - _indices
                cnt += self.eliminate_candidates_of_indices(bi, k)

        for c in range(9):
            candidate_counts = self.count_candidates(column_indices(c))
            for k, v in candidate_counts.items():
                if v not in (2, 3):
                    continue
                _indices = set(i for i in column_indices(
                    c) if k in self.candidates[i])
                _positions = [position(i) for i in _indices]
                _boxes = set(p[2] for p in _positions)
                if len(_boxes) != 1:
                    continue
                b = _boxes.pop()
                bi = set(box_indices(b)) - _indices
                cnt += self.eliminate_candidates_of_indices(bi, k)

        return cnt

    def box_box_reduction(self) -> int:
        """
            For each 2 boxes in same direction, if they have a candidate only lies within 2 rows (or columns), remove candidates of that number from 2 rows in the other box.
        """
        cnt = 0
        for x in range(1, 10):
            # Check horizontal boxes
            for k in range(3):
                boxes = set(k * 3 + i for i in range(3))
                pairs = [set(pair) for pair in combinations(boxes, 2)]
                for pair in pairs:
                    b1, b2 = pair
                    rb1 = set(row_of(i) for i in box_indices(b1) if x in self.candidates[i])
                    rb2 = set(row_of(i) for i in box_indices(b2) if x in self.candidates[i])
                    rows = rb1 | rb2
                    if len(rb1) == 0 or len(rb2) == 0 or len(rows) != 2:
                        continue
                    other_box_i = (boxes - pair).pop()
                    indices = [i for i in box_indices(other_box_i) if row_of(i) in rb1]
                    cnt += self.eliminate_candidates_of_indices(indices, x)

            # Check vertical boxes
            for k in range(3):
                boxes = set(k + i * 3 for i in range(3))
                pairs = [set(pair) for pair in combinations(boxes, 2)]
                for pair in pairs:
                    b1, b2 = pair
                    cb1 = set(column_of(i) for i in box_indices(b1) if x in self.candidates[i])
                    cb2 = set(column_of(i) for i in box_indices(b2) if x in self.candidates[i])
                    columns = cb1 | cb2
                    if len(cb1) == 0 or len(cb2) == 0 or len(columns) != 2:
                        continue

                    other_box_i = (boxes - pair).pop()
                    indices = [i for i in box_indices(other_box_i) if column_of(i) in columns]
                    cnt += self.eliminate_candidates_of_indices(indices, x)

        return cnt

    def hidden_subsets(self) -> int:
        """
            For each area (box, column or row), check for each subset of size k from 2 to 4, if it has k candidates that do not belong other cells in the area,
            eliminate all other candidates that are belong to other cells in the area.
        """
        def eliminate_hidden_subsets_of_indices(indices: List[str]) -> int:
            cnt = 0
            for size in range(2, min(4, len(indices))):
                indices_subsets = list(combinations(indices, size))
                for subset_indices in indices_subsets:
                    subset_candidates = set.union(
                        *[self.candidates[i] for i in subset_indices])
                    other_indices = list(set(indices) - set(subset_indices))
                    other_candidates = set.union(
                        *[self.candidates[i] for i in other_indices])
                    subset_unique_candidates = subset_candidates - other_candidates
                    # If the subset (size k) has k candidates that does not belong to other cells, eliminate other candidates in the subset that belong to other cells.
                    if len(subset_unique_candidates) == size:
                        for candidate in other_candidates:
                            cnt += self.eliminate_candidates_of_indices(
                                subset_indices, candidate)
            return cnt

        cnt = 0
        for x in range(9):
            bi = [i for i in box_indices(x) if self.cells[i] == 0]
            ri = [i for i in row_indices(x) if self.cells[i] == 0]
            ci = [i for i in column_indices(x) if self.cells[i] == 0]
            cnt += eliminate_hidden_subsets_of_indices(bi)
            cnt += eliminate_hidden_subsets_of_indices(ri)
            cnt += eliminate_hidden_subsets_of_indices(ci)

        return cnt

    def naked_subsets(self) -> int:
        """
            For each area (box, column or row), check for naked subset of size k from 2 to 4. If it has k candidates, then eliminate those candidates from other cells in the area.
        """
        def eliminate_naked_subsets_of_indices(indices: List[str]):
            cnt = 0
            for size in range(2, min(4, len(indices))):
                indices_subsets = list(combinations(indices, size))
                for subset_indices in indices_subsets:
                    subset_candidates = set.union(
                        *[self.candidates[i] for i in subset_indices])
                    if len(subset_candidates) == size:
                        other_indices = list(
                            set(indices) - set(subset_indices))
                        for candidate in subset_candidates:
                            cnt += self.eliminate_candidates_of_indices(
                                other_indices, candidate)
            return cnt

        cnt = 0
        for x in range(9):
            bi = [i for i in box_indices(x) if self.cells[i] == 0]
            ri = [i for i in row_indices(x) if self.cells[i] == 0]
            ci = [i for i in column_indices(x) if self.cells[i] == 0]
            cnt += eliminate_naked_subsets_of_indices(bi)
            cnt += eliminate_naked_subsets_of_indices(ri)
            cnt += eliminate_naked_subsets_of_indices(ci)

        return cnt

    def x_wing(self, n=2) -> int:
        """
            Detect x-wing in row or column then eliminate that candidate from intersecting cells.
        """
        cnt = 0
        # Detect x-wing in rows
        for x in range(1, 10):
            valid_rows = []

            for r in range(9):
                candidate_counts = self.count_candidates(row_indices(r))
                if not 2 <= candidate_counts.get(x, 0) <= n:
                    continue
                valid_rows.append(r)

            if len(valid_rows) < n:
                continue

            combs = list(combinations(valid_rows, n))

            for rows in combs:
                indices = set()
                for r in rows:
                    ri = set(i for i in row_indices(r) if x in self.candidates[i])
                    indices.update(ri)
                columns = set(column_of(i) for i in indices)
                if len(columns) == n:
                    for c in columns:
                        _ci = set(i for i in column_indices(c) if row_of(i) not in rows)
                        cnt += self.eliminate_candidates_of_indices(_ci, x)

        # Detect x-wing in columns
        for x in range(1, 10):
            valid_columns = []

            for c in range(9):
                candidate_counts = self.count_candidates(column_indices(c))
                if not 2 <= candidate_counts.get(x, 0) <= n:
                    continue
                valid_columns.append(c)

            if len(valid_columns) < n:
                continue

            combs = list(combinations(valid_columns, n))

            for columns in combs:
                indices = set()
                for c in columns:
                    ci = set(i for i in column_indices(c) if x in self.candidates[i])
                    indices.update(ci)
                rows = set(row_of(i) for i in indices)
                if len(rows) == n:
                    for r in rows:
                        _ri = set(i for i in row_indices(r) if column_of(i) not in columns)
                        cnt += self.eliminate_candidates_of_indices(_ri, x)
        return cnt

    def y_wing(self) -> int:
        cnt = 0
        for i in range(81):
            if self.cells[i] != 0:
                continue
            candidates = self.candidates[i]
            if len(candidates) != 2:
                continue
            # Assume that current cell is pivot of y-wing
            r, c, b = position(i)

            pincers_column = []
            pincers_row = []
            pincers_box = []

            # Check for pincers in column
            for _r in range(0, 9):
                _i = cell_index(_r, c)
                _candidates = self.candidates[_i]
                _b = box_of_i(_i)
                if b == _b:
                    continue
                if len(_candidates) != 2:
                    continue
                # Take if there is one candidate in common
                if len(_candidates & candidates) == 1:
                    pincers_column.append(_i)

            # Check for pincers in row
            for _c in range(0, 9):
                _i = cell_index(r, _c)
                _candidates = self.candidates[_i]
                _b = box_of_i(_i)
                if b == _b:
                    continue
                if len(_candidates) != 2:
                    continue
                # Take if there is one candidate in common
                if len(_candidates & candidates) == 1:
                    pincers_row.append(_i)

            # Check for pincers in box
            for _r in range(r // 3 * 3, r // 3 * 3 + 3):
                for _c in range(c // 3 * 3, c // 3 * 3 + 3):
                    # Skip if the two cells are in the same column or row
                    if _r == r or _c == c:
                        continue

                    _i = cell_index(_r, _c)
                    _candidates = self.candidates[_i]
                    if len(_candidates) != 2:
                        continue
                    # Take if there is one candidate in common
                    if len(_candidates & candidates) == 1:
                        pincers_box.append(_i)

            pincers_rc = product(pincers_column, pincers_row)
            pincers_rb = product(pincers_row, pincers_box)
            pincers_cb = product(pincers_column, pincers_box)

            cnt = 0

            for i1, i2 in pincers_rc:
                if self.candidates[i1] ^ self.candidates[i2] == candidates:
                    candidate_to_eliminiate = (
                        self.candidates[i1] & self.candidates[i2]).pop()
                    # Intersect positions of pincers
                    r1, c1, _ = position(i1)
                    r2, c2, _ = position(i2)
                    cnt += self.eliminate_candidates_of_indices(
                        [cell_index(r1, c2), cell_index(r2, c1)], candidate_to_eliminiate)

            for i1, i2 in pincers_rb:
                if self.candidates[i1] ^ self.candidates[i2] == candidates:
                    candidate_to_eliminiate = (
                        self.candidates[i1] & self.candidates[i2]).pop()
                    r1, _, b1 = position(i1)
                    r2, _, b2 = position(i2)
                    # Remove candidates from the same row of the other pincer box.
                    cnt += self.eliminate_candidates_of_indices(
                        set(query_indices(r=r1 % 3, b=b2)) | set(
                            query_indices(r=r2 % 3, b=b1)),
                        candidate_to_eliminiate
                    )

            for i1, i2 in pincers_cb:
                if self.candidates[i1] ^ self.candidates[i2] == candidates:
                    candidate_to_eliminiate = (
                        self.candidates[i1] & self.candidates[i2]).pop()
                    _, c1, b1 = position(i1)
                    _, c2, b2 = position(i2)
                    # Remove candidates from the same column of the other pincer box.
                    cnt += self.eliminate_candidates_of_indices(
                        set(query_indices(c=c1 % 3, b=b2)) | set(
                            query_indices(c=c2 % 3, b=b1)),
                        candidate_to_eliminiate
                    )

        return cnt

    def swordfish(self) -> int:
        """
            Similar to X-Wing, but checks for 3 rows or 3 columns.
        """
        return self.x_wing(3)

    def jellyfish(self) -> int:
        """
            Similar to X-Wing, but checks for 4 rows or 4 columns.
        """
        return self.x_wing(4)

    def xyz_wing(self) -> int:
        cnt = 0
        for i in range(81):
            if self.cells[i] != 0:
                continue
            candidates = self.candidates[i]
            if len(candidates) != 3:
                continue
            # Assume that current cell is pivot of xyz-wing
            r, c, b = position(i)

            pincers_column = []
            pincers_row = []
            pincers_box = []

            # Check for pincers in column
            for _r in range(0, 9):
                _i = cell_index(_r, c)
                _candidates = self.candidates[_i]
                _b = box_of_i(_i)
                if _b == b:
                    continue
                if len(_candidates) != 2:
                    continue
                # Take if there is two candidates in common
                if len(_candidates & candidates) == 2:
                    pincers_column.append(_i)

            # Check for pincers in row
            for _c in range(0, 9):
                _i = cell_index(r, _c)
                _candidates = self.candidates[_i]
                _b = box_of_i(_i)
                if _b == b:
                    continue
                if len(_candidates) != 2:
                    continue
                # Take if there is two candidates in common
                if len(_candidates & candidates) == 2:
                    pincers_row.append(_i)

            # Check for pincers in box
            for _r in range(r // 3 * 3, r // 3 * 3 + 3):
                for _c in range(c // 3 * 3, c // 3 * 3 + 3):
                    if _r == r and _c == c:
                        continue
                    _i = cell_index(_r, _c)
                    _candidates = self.candidates[_i]
                    if len(_candidates) != 2:
                        continue
                    # Take if there is two candidate in common
                    if len(_candidates & candidates) == 2:
                        pincers_box.append(_i)

            pincers_rb = product(pincers_row, pincers_box)
            pincers_cb = product(pincers_column, pincers_box)

            cnt = 0

            for ir, ib in pincers_rb:
                if self.candidates[ir] | self.candidates[ib] == candidates:
                    candidate_to_eliminiate = (self.candidates[ir] & self.candidates[ib]).pop()
                    rir = row_of(ir)
                    rib = row_of(ib)
                    # Exception: 2 pincers and pivot in the same row
                    if rir == rib:
                        continue
                    print(f"xyz-wing: Eliminate {candidate_to_eliminiate} from row {rir} and box {b}")
                    # Remove the common candidate in the same row and same box of the pivot
                    cnt += self.eliminate_candidates_of_indices(
                        set(query_indices(r=r % 3, b=b)) - {i},
                        candidate_to_eliminiate
                    )

            for ic, ib in pincers_cb:
                if self.candidates[ic] | self.candidates[ib] == candidates:
                    candidate_to_eliminiate = (self.candidates[ic] & self.candidates[ib]).pop()
                    # Exception: 2 pincers and pivot in the same column
                    if column_of(ic) == column_of(ib):
                        continue
                    # Remove the common candidate in the same column and same box of the pivot
                    cnt += self.eliminate_candidates_of_indices(
                        set(query_indices(c=c % 3, b=b)) - {i},
                        candidate_to_eliminiate
                    )

        return cnt

    def eliminate_using_all_techniques(self) -> int:
        cnt = 0
        cnt += self.pointing_pair()
        cnt += self.box_line_reduction()
        cnt += self.box_box_reduction()
        cnt += self.naked_subsets()
        cnt += self.hidden_subsets()
        cnt += self.y_wing()
        cnt += self.x_wing()
        cnt += self.xyz_wing()
        cnt += self.swordfish()
        cnt += self.jellyfish()
        if cnt > 0:
            cnt += self.eliminate_using_all_techniques()
        return cnt

    def solve(self, is_recursive=False) -> int:
        cnt = 0
        if not is_recursive:
            self.compute_candidates()
            cnt += self.solve_hidden_singles()
        self.eliminate_using_all_techniques()
        cnt += self.solve_hidden_singles()
        if cnt > 0:
            cnt += self.solve(is_recursive=True)
        return cnt

    def solve_and_display(self) -> Sudoku:
        print(f"🔢 {self.name}")
        if not self.valid:
            print(f"❗ Invalid {self.name}!")
            return
        self.display()
        print(f"⌛ Solving {self.name}...")
        start = timer()
        cells_solved = self.solve()
        end = timer()
        self.display()
        print(f"{self.name}: {cells_solved} cells solved")
        if self.solved:
            print(f"✅ {self.name} solved in {end - start:.4f} seconds!")
        else:
            print(f"❌ Failed to solve {self.name}.")
        if not self.valid:
            print(f"❗ Invalid {self.name}!")
        print()
        return self

    @ property
    def valid(self) -> bool:
        for i in range(9):
            column = [v for v in self.column(i) if v != 0]
            box = [v for v in self.box(i) if v != 0]
            row = [v for v in self.row(i) if v != 0]

            if len(set(column)) != len(column):
                return False
            if len(set(box)) != len(box):
                return False
            if len(set(row)) != len(row):
                return False
        return True

    @ property
    def solved(self) -> bool:
        return self.valid and all(v != 0 for v in self.cells)

    @ classmethod
    def from_file(cls, filename: str):
        sudoku = cls()
        sudoku.set_cells(load_cells_from_file(filename))
        return sudoku

    def display(self):
        for r1 in range(3):
            for r2 in range(3):
                r = r1 * 3 + r2
                self.display_row(r)
            if r1 < 2:
                print("------+-------+------")
        print()

    def display_row(self, r: int):
        row = self.row(r)
        for i in range(3):
            for j in range(3):
                s = str(row[i * 3 + j])
                s = s.replace("0", "_")
                print(s, end=" ")
            if i < 2:
                print("|", end=" ")
        print()

    def display_candidates(self):
        def display_set(i: int):
            print("".join(str(n)
                  for n in self.candidates[i]).center(10), end=" ")
        for r1 in range(3):
            for r2 in range(3):
                r = r1 * 3 + r2
                for c1 in range(3):
                    for c2 in range(3):
                        c = c1 * 3 + c2
                        i = cell_index(r, c)
                        display_set(i)
                    if c1 < 2:
                        print("|", end=" ")
                print()
            if r1 < 2:
                print("-" * 33 + "+" + "-" * 34 + "+" + "-" * 33)
