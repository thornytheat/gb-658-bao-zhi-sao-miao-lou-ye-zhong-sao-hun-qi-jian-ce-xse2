from app.modules.m1_intake.parser import parse_manifest
from app.modules.m1_intake.integrity import valid_sha256, complete_tail, stable_file_key

HEADER = "issue,edition,page,file_name,sha256,phash,clarity,header_issue\n"
def row(issue="2026-11-01", page="001"):
    return f"{issue},01,{page},a.tif,{'a'*64},0f0f,90,{issue}\n"

def test_parse_clean_manifest():
    good, bad = parse_manifest(HEADER + row())
    assert (len(good), len(bad), good[0]["line_no"]) == (1, 0, 2)

def test_strip_bom_header():
    good, bad = parse_manifest("\ufeff" + HEADER + row())
    assert len(good) == 1 and not bad  # TRAP-02

def test_repeated_header_is_not_record():
    good, bad = parse_manifest(HEADER + row() + HEADER + row(page="002"))
    assert [item["page"] for item in good] == ["001", "002"]

def test_column_count_goes_quarantine():
    good, bad = parse_manifest(HEADER + "2026-11-01,01,001\n")
    assert not good and bad[0]["reason_code"] == "COLUMN_COUNT"  # TRAP-05

def test_empty_file_has_distinct_result():
    good, bad = parse_manifest("")
    assert not good and bad[0]["reason_code"] == "EMPTY_FILE"  # TRAP-18

def test_sha_requires_exact_hex():
    assert valid_sha256("a" * 64) and not valid_sha256("x" * 64)

def test_truncated_tail_detected():
    assert complete_tail("x\n") and not complete_tail("x")  # TRAP-16

