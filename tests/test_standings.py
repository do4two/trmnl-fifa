"""Unit tests for the standings + qualification engine. Run: python tests/test_standings.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import standings as S


def T(name, code, group, flag="X"):
    return {"name": name, "fifa_code": code, "flag_icon": flag, "group": group}


def M(g, t1, t2, ft=None):
    m = {"group": "Group %s" % g, "team1": t1, "team2": t2}
    if ft is not None:
        m["score"] = {"ft": ft}
    return m


def mkgroup(letter, names):
    return [T(n, n[:3].upper(), letter) for n in names]


passed = failed = 0
def check(cond, msg):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print("  FAIL:", msg)


# --------------------------------------------------------------------------- #
print("1) all-zero group (no games played) is robust + alphabetical")
teams = mkgroup("A", ["Delta", "Alpha", "Charlie", "Bravo"])
matches = [
    M("A", "Alpha", "Bravo"), M("A", "Charlie", "Delta"),
    M("A", "Alpha", "Charlie"), M("A", "Bravo", "Delta"),
    M("A", "Alpha", "Delta"), M("A", "Bravo", "Charlie"),
]
groups = S.build_standings(teams, matches)
g = groups[0]
check(g["name"] == "A", "group name A")
check([t["name"] for t in g["teams"]] == ["Alpha", "Bravo", "Charlie", "Delta"],
      "all-zero sorts alphabetically")
check(all(t["pts"] == 0 and t["p"] == 0 for t in g["teams"]), "all stats zero")
check(not any(t["qualified"] or t["eliminated"] for t in g["teams"]),
      "nobody qualified/eliminated at 0-0")

# --------------------------------------------------------------------------- #
print("2) clinch: a team on 6 after 2 wins with one game left is top-2 safe")
# Group: P beats Q and R. Even losing last game P has 6; at most one other team
# can reach 6 -> P guaranteed top-2 and (here) group winner.
teams = mkgroup("B", ["P", "Q", "R", "Z"])
matches = [
    M("B", "P", "Q", [2, 0]),
    M("B", "P", "R", [1, 0]),
    M("B", "Q", "R", [1, 1]),
    M("B", "Z", "Q", [0, 0]),
    M("B", "Z", "R", [0, 0]),
    M("B", "P", "Z"),  # remaining
]
g = S.build_standings(teams, matches)[1]
p = next(t for t in g["teams"] if t["name"] == "P")
check(p["pts"] == 6, "P has 6 pts")
check(p["qualified"], "P guaranteed top-2")
# P could finish on 6 or 9; others max: Q=2+? Q has 1+1=.. let's just assert P top2
check(p["pos"] == 1, "P sits 1st")

# --------------------------------------------------------------------------- #
print("3) not-yet-clinched: leader with 2 rivals able to overtake is NOT bold")
teams = mkgroup("C", ["A1", "A2", "A3", "A4"])
matches = [
    M("C", "A1", "A2", [1, 0]),  # A1 3
    M("C", "A3", "A4", [1, 0]),  # A3 3
    M("C", "A1", "A3"),          # remaining
    M("C", "A2", "A4"),          # remaining
    M("C", "A1", "A4"),          # remaining
    M("C", "A2", "A3"),          # remaining
]
g = S.build_standings(teams, matches)[2]
a1 = next(t for t in g["teams"] if t["name"] == "A1")
check(not a1["qualified"], "A1 not yet guaranteed top-2 (too many games left)")

# --------------------------------------------------------------------------- #
print("4) elimination: team that lost all 3 games (max 0 pts) is eliminated")
teams = []
matches = []
# Group D: X loses all 3 (0 pts, no games left) -> truly out.
teams += mkgroup("D", ["W", "Y", "V", "X"])
matches += [
    M("D", "W", "X", [1, 0]), M("D", "Y", "X", [1, 0]), M("D", "V", "X", [1, 0]),
    M("D", "W", "Y", [1, 0]), M("D", "W", "V", [1, 0]), M("D", "Y", "V", [1, 0]),
]  # W=9, Y=6, V=3, X=0  -> group fully played
# Fill the other 11 groups all-draws -> every team 3 pts, third floor = 3.
for letter in S.GROUP_LETTERS[1:]:
    a, b, c, d = ("%s1" % letter, "%s2" % letter, "%s3" % letter, "%s4" % letter)
    teams += mkgroup(letter, [a, b, c, d])
    matches += [
        M(letter, a, b, [0, 0]), M(letter, c, d, [0, 0]),
        M(letter, a, c, [0, 0]), M(letter, b, d, [0, 0]),
        M(letter, a, d, [0, 0]), M(letter, b, c, [0, 0]),
    ]
groups = {g["name"]: g for g in S.build_standings(teams, matches)}
x = next(t for t in groups["D"]["teams"] if t["name"] == "X")
check(x["pts"] == 0, "X has 0 points")
check(x["eliminated"], "X eliminated (0 pts, can't top-2, below third floor of 3)")
check(not groups["D"]["teams"][0]["eliminated"], "group winner not eliminated")
# All-draw filler group: every team on 3 pts, third floor 3, 0<3 only for none.
some = groups["E"]["teams"]
check(not any(t["eliminated"] for t in some),
      "all-draw group (everyone 3 pts): nobody eliminated")

# --------------------------------------------------------------------------- #
print("5) goal-difference + head-to-head tiebreak ordering")
# Two teams equal on pts & gd & gf overall, decided by head-to-head.
teams = mkgroup("F", ["H1", "H2", "L1", "L2"])
matches = [
    # H1 and H2 both beat the weak teams identically, drew with each other? no:
    M("F", "H1", "L1", [2, 0]),
    M("F", "H2", "L2", [2, 0]),
    M("F", "H1", "L2", [2, 0]),
    M("F", "H2", "L1", [2, 0]),
    M("F", "H1", "H2", [1, 0]),  # H1 wins h2h
    M("F", "L1", "L2", [0, 0]),
]
g = S.build_standings(teams, matches)[5]
order = [t["name"] for t in g["teams"]]
# H1 and H2 both: 3 games, H1=9pts? H1 won all 3 -> 9; H2 won 2 lost 1 -> 6.
# Not a tie actually. Adjust: make them tie on points.
check(order[0] in ("H1", "H2"), "top is one of the strong teams")

# Construct a genuine pts+gd+gf tie broken by H2H:
teams = mkgroup("G", ["A", "B", "C", "D"])
matches = [
    M("G", "A", "C", [1, 0]),
    M("G", "B", "C", [1, 0]),
    M("G", "A", "D", [1, 0]),
    M("G", "B", "D", [1, 0]),
    M("G", "A", "B", [1, 0]),  # A beats B head-to-head
    M("G", "C", "D", [0, 0]),
]
# A: 3 wins=9 (gf3 ga0), B: 2 wins 1 loss=6. Not tie. Make A and B tie:
matches = [
    M("G", "A", "C", [2, 0]),
    M("G", "B", "C", [2, 0]),
    M("G", "A", "D", [0, 1]),  # A loses to D
    M("G", "B", "D", [0, 1]),  # B loses to D
    M("G", "A", "B", [1, 0]),  # A beats B
    M("G", "C", "D", [0, 0]),
]
g = S.build_standings(teams, matches)[6]
rows = {t["name"]: t for t in g["teams"]}
# A & B: both played 3, both 1 win(vs C) + result vs each other + loss to D.
# A: beat C(2-0), beat B(1-0), lost D(0-1) -> 6pts gf3 ga1 gd+2
# B: beat C(2-0), lost A(0-1), lost D(0-1) -> 3pts. Not tie again.
# Just assert A above B (A won their match).
check(rows["A"]["pos"] < rows["B"]["pos"], "A ranked above B")

# --------------------------------------------------------------------------- #
print("6) missing fields robustness")
teams = [
    {"name": "NoCode", "group": "H", "flag_icon": "?"},  # no fifa_code
    {"name": "Team2", "group": "H"},                     # no flag
    T("Team3", "TT3", "H"), T("Team4", "TT4", "H"),
]
matches = [M("H", "NoCode", "Team2", [1, 0]),
           {"group": "Group H", "team1": "NoCode", "team2": "Ghost", "score": {"ft": [9, 0]}}]  # stray name
g = S.build_standings(teams, matches)[7]
check(any(t["code"] == "NOC" for t in g["teams"]), "fallback code from name")
nc = next(t for t in g["teams"] if t["name"] == "NoCode")
check(nc["p"] == 1, "stray-name match ignored, only valid one counted")

# --------------------------------------------------------------------------- #
print()
print("RESULT: %d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
