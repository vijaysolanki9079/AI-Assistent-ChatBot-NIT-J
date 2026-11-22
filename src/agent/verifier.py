import re
from typing import List, Any, Set, Tuple

class OutputVerifier:
    """
    Validates that every factual number mentioned in the final answer
    is strictly present in the tool result payload or trivially derived.
    Prevents the narration bug (summing max packages, averages, or inventing numbers).
    """

    @staticmethod
    def extract_numbers_from_text(text: str) -> List[float]:
        # Strip commas inside numbers (e.g. 400,000 -> 400000)
        clean_text = re.sub(r'(\d),(\d)', r'\1\2', text)
        tokens = re.findall(r'(?<![A-Za-z0-9_])(?:\d+(?:\.\d+)?|\.\d+)(?![A-Za-z0-9_])', clean_text)
        nums = []
        for t in tokens:
            try:
                v = float(t)
                nums.append(v)
            except ValueError:
                continue
        return nums

    @staticmethod
    def extract_allowed_numbers(rows: List[List[Any]], extra_allowed: Set[float] = None) -> Set[float]:
        allowed = set(extra_allowed or [])
        allowed.update([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0, float(len(rows))])

        row_floats = []
        col_count = len(rows[0]) if rows else 0
        col_sums = [0.0] * col_count
        col_is_count = [True] * col_count

        for row in rows:
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                if isinstance(cell, (int, float)):
                    val = float(cell)
                    allowed.add(val)
                    row_floats.append(val)
                    col_sums[idx] += val
                elif isinstance(cell, str):
                    m = re.match(r'^\s*(\d+(?:\.\d+)?)\s*$', cell)
                    if m:
                        val = float(m.group(1))
                        allowed.add(val)
                        row_floats.append(val)
                        col_sums[idx] += val
                    else:
                        col_is_count[idx] = False

        # Allow sums of integer count columns (e.g. total placed across distinct cohorts)
        for idx in range(col_count):
            if col_is_count[idx] and col_sums[idx] > 0:
                allowed.add(round(col_sums[idx], 2))

        # Allow simple pairwise differences
        for i in range(len(row_floats)):
            for j in range(i + 1, len(row_floats)):
                diff = round(abs(row_floats[i] - row_floats[j]), 2)
                allowed.add(diff)

        return allowed

    @classmethod
    def verify(cls, draft_text: str, rows: List[List[Any]], allowed_years: Set[float] = None) -> Tuple[bool, List[float]]:
        draft_nums = cls.extract_numbers_from_text(draft_text)
        
        years = {2020.0, 2021.0, 2022.0, 2023.0, 2024.0, 2025.0, 2026.0, 2027.0, 20.0, 21.0, 22.0, 24.0, 25.0, 26.0}
        if allowed_years:
            years.update(allowed_years)

        allowed = cls.extract_allowed_numbers(rows, extra_allowed=years)

        ungrounded = []
        for num in draft_nums:
            matched = any(abs(num - a) < 0.05 for a in allowed)
            if not matched:
                ungrounded.append(num)

        return (len(ungrounded) == 0, ungrounded)
