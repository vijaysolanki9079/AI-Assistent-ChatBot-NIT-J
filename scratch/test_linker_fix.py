import sys
import os
sys.path.insert(0, os.path.abspath("."))
import re
from rapidfuzz import fuzz, process

q = "Year-wise average package for Computer Science and Engineering"
words = re.findall(r'[A-Za-z0-9&]+', q)
print("Words:", words)

candidates = []
for n in [5, 4, 3, 2, 1]:
    for i in range(len(words) - n + 1):
        candidates.append(" ".join(words[i:i+n]))

print("Contains 'Computer Science and Engineering'?", "Computer Science and Engineering" in candidates)

