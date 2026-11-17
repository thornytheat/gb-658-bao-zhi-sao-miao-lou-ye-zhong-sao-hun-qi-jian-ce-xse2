import csv
import io

def evidence_csv(rows: list[dict]) -> str:
    output = io.StringIO(newline="")
    fields = ["business_key", "line_no", "reason_code", "raw_value"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()

