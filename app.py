from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from pathlib import Path
import shutil
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
import os, re

app = Flask(__name__)
app.secret_key = os.environ.get("RACKWEB_SECRET") or os.urandom(32)
BASE_DIR = Path(__file__).resolve().parent
# For hosting, point RACK_DATA_DIR at a persistent disk (Render: /var/data).
# Copy the bundled workbook only on first startup; never overwrite existing hosted data.
DATA_DIR = Path(os.environ.get("RACK_DATA_DIR", str(BASE_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXCEL_FILE = DATA_DIR / "rack.xlsx"
BUNDLED_EXCEL_FILE = BASE_DIR / "rack.xlsx"
if not EXCEL_FILE.exists() and BUNDLED_EXCEL_FILE.exists() and EXCEL_FILE != BUNDLED_EXCEL_FILE:
    shutil.copy2(BUNDLED_EXCEL_FILE, EXCEL_FILE)

def clean(value):
    return re.sub(r"\s+", " ", str(value or "").strip())

def norm(value):
    return clean(value).casefold()

def load_rack_data():
    """Read each worksheet as a physical rack layout without flattening or rewriting it."""
    if not EXCEL_FILE.exists():
        return [], [], "Không tìm thấy rack.xlsx. Hãy đặt file Excel kho của bạn cạnh app.py."
    try:
        wb = load_workbook(EXCEL_FILE, data_only=True)
        rack_sheets, all_items = [], []
        for ws in wb.worksheets:
            max_row, max_col = ws.max_row, ws.max_column
            # Limit only completely empty trailing columns/rows; keep internal gaps as rack geometry.
            while max_col > 1 and all(ws.cell(r, max_col).value is None for r in range(1, max_row + 1)):
                max_col -= 1
            while max_row > 1 and all(ws.cell(max_row, c).value is None for c in range(1, max_col + 1)):
                max_row -= 1

            rows = []
            current_level = ""
            for r in range(1, max_row + 1):
                cells = []
                row_has_value = False
                level_label = current_level
                for c in range(1, max_col + 1):
                    val = ws.cell(r, c).value
                    value = clean(val)
                    if value:
                        row_has_value = True
                    if c == 1 and value.casefold().startswith("tầng"):
                        current_level = value
                        level_label = value
                    if value and c > 1 and not value.casefold().startswith("khu "):
                        item = {
                            "code": value,
                            "sheet": ws.title,
                            "cell": ws.cell(r, c).coordinate,
                            "row": r,
                            "col": c,
                            "level": level_label,
                        }
                        all_items.append(item)
                    cells.append({
                        "value": value,
                        "coord": ws.cell(r, c).coordinate,
                        "is_level": c == 1 and value.casefold().startswith("tầng"),
                        "is_zone": value.casefold().startswith("khu "),
                        "is_code": bool(value and c > 1 and not value.casefold().startswith("khu ")),
                        "highlight": False,
                        "fill_color": (ws.cell(r, c).fill.fgColor.rgb[-6:] if ws.cell(r, c).fill.fgColor.type == "rgb" and ws.cell(r, c).fill.fgColor.rgb else ""),
                    })
                level_text = norm(level_label)
                if "3" in level_text:
                    tier_class = "tier-3"
                elif "2" in level_text:
                    tier_class = "tier-2"
                elif "1" in level_text:
                    tier_class = "tier-1"
                else:
                    tier_class = "tier-neutral"

                if row_has_value:
                    rows.append({"number": r, "cells": cells, "level": level_label, "tier_class": tier_class})
                else:
                    # Keep blank rows so the view resembles the original sheet's physical gaps.
                    rows.append({"number": r, "cells": cells, "level": level_label, "tier_class": tier_class, "blank": True})
            rack_sheets.append({
                "name": ws.title,
                "rows": rows,
                "max_col": max_col,
                "max_row": max_row,
                "items_count": sum(1 for item in all_items if item["sheet"] == ws.title),
            })
        return rack_sheets, all_items, None
    except Exception as exc:
        return [], [], f"Không đọc được file Excel: {exc}"

@app.route("/")
def index():
    sheets, items, error = load_rack_data()
    q = clean(request.args.get("q", ""))
    selected_sheet = clean(request.args.get("sheet", ""))
    matches = items
    if q:
        needle = norm(q)
        matches = [x for x in matches if needle in norm(x["code"]) or needle in norm(x["sheet"]) or needle in norm(x["cell"])]
    if selected_sheet:
        matches = [x for x in matches if x["sheet"] == selected_sheet]
    matched_cells = {(x["sheet"], x["cell"]) for x in matches} if q else set()
    # When searching, mark matching cells in the physical rack grid.
    for sheet in sheets:
        for row in sheet["rows"]:
            for cell in row["cells"]:
                cell["highlight"] = (sheet["name"], cell["coord"]) in matched_cells
    sheet_names = [s["name"] for s in sheets]
    sheet_counts = {s["name"]: s["items_count"] for s in sheets}
    return render_template(
        "index.html", sheets=sheets, items=items, matches=matches, q=q,
        selected_sheet=selected_sheet, sheet_names=sheet_names,
        sheet_counts=sheet_counts, total=len(items),
        sheet_count=len(sheets), match_count=len(matches), error=error
    )

@app.route("/edit", methods=["POST"])
def edit_cell():
    """Update an existing rack cell in rack.xlsx from the browser."""
    payload = request.get_json(silent=True) or request.form
    sheet_name = clean(payload.get("sheet", ""))
    coordinate = clean(payload.get("cell", "")).upper()
    new_value = str(payload.get("value", "")).strip()

    if not EXCEL_FILE.exists():
        return jsonify(ok=False, message="Không tìm thấy rack.xlsx."), 404
    if not sheet_name or not coordinate:
        return jsonify(ok=False, message="Thiếu tên sheet hoặc địa chỉ ô."), 400
    if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", coordinate):
        return jsonify(ok=False, message="Địa chỉ ô Excel không hợp lệ."), 400

    try:
        wb = load_workbook(EXCEL_FILE)
        if sheet_name not in wb.sheetnames:
            return jsonify(ok=False, message="Không tìm thấy sheet cần sửa."), 404
        ws = wb[sheet_name]
        # Do not write into the non-anchor part of a merged cell range.
        for merged_range in ws.merged_cells.ranges:
            if coordinate in merged_range:
                anchor = ws.cell(merged_range.min_row, merged_range.min_col).coordinate
                if coordinate != anchor:
                    return jsonify(ok=False, message=f"Ô {coordinate} thuộc vùng gộp; hãy sửa ô đầu vùng {anchor}."), 400
        cell = ws[coordinate]
        # Keep edited values as text so codes such as 014 or 001 are not converted to numbers.
        cell.value = new_value if new_value else None
        wb.save(EXCEL_FILE)
        wb.close()
        return jsonify(ok=True, message=f"Đã lưu {sheet_name}!{coordinate} vào rack.xlsx.", value=new_value)
    except PermissionError:
        return jsonify(ok=False, message="Không lưu được. Hãy đóng rack.xlsx nếu file đang mở trong Excel rồi thử lại."), 409
    except Exception as exc:
        return jsonify(ok=False, message=f"Lỗi khi lưu ô Excel: {exc}"), 500


def editable_excel_cell(ws, coordinate):
    """Validate an address and reject the non-anchor cells of merged ranges."""
    coordinate = coordinate.upper().strip()
    if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", coordinate):
        raise ValueError("Địa chỉ ô Excel không hợp lệ.")
    # Bound requests to the actual worksheet footprint to avoid accidental huge edits.
    from openpyxl.utils.cell import coordinate_to_tuple
    row, col = coordinate_to_tuple(coordinate)
    if row > max(ws.max_row + 100, 1000) or col > max(ws.max_column + 30, 100):
        raise ValueError("Ô nằm ngoài phạm vi sơ đồ.")
    for merged_range in ws.merged_cells.ranges:
        if coordinate in merged_range:
            anchor = ws.cell(merged_range.min_row, merged_range.min_col).coordinate
            if coordinate != anchor:
                raise ValueError(f"Ô {coordinate} thuộc vùng gộp; hãy chọn ô đầu vùng {anchor}.")
    return ws[coordinate]


@app.route("/suggest")
def suggest_codes():
    """Return typeahead suggestions for box codes, sheets and Excel coordinates."""
    query = norm(request.args.get("q", ""))
    if not query:
        return jsonify(results=[])
    _, items, error = load_rack_data()
    if error:
        return jsonify(results=[])
    results = [item for item in items if query in norm(item["code"]) or query in norm(item["sheet"]) or query in norm(item["cell"])]
    results.sort(key=lambda item: (not norm(item["code"]).startswith(query), norm(item["code"]), item["sheet"], item["cell"]))
    return jsonify(results=results[:12])


@app.route("/rack-action", methods=["POST"])
def rack_action():
    """Add/delete/move a box while keeping the Excel workbook as the source of truth."""
    payload = request.get_json(silent=True) or request.form
    action = clean(payload.get("action", "")).lower()
    sheet_name = clean(payload.get("sheet", ""))
    source = clean(payload.get("cell", "")).upper()
    target = clean(payload.get("target", "")).upper()
    value = str(payload.get("value", "")).strip()

    if not EXCEL_FILE.exists():
        return jsonify(ok=False, message="Không tìm thấy rack.xlsx."), 404
    if not sheet_name or not source:
        return jsonify(ok=False, message="Thiếu tên sheet hoặc địa chỉ ô."), 400

    try:
        wb = load_workbook(EXCEL_FILE)
        if sheet_name not in wb.sheetnames:
            wb.close()
            return jsonify(ok=False, message="Không tìm thấy sheet."), 404
        ws = wb[sheet_name]
        source_cell = editable_excel_cell(ws, source)
        from openpyxl.utils.cell import coordinate_to_tuple
        source_row, source_col = coordinate_to_tuple(source)
        if source_col < 2:
            wb.close()
            return jsonify(ok=False, message="Không thể thêm/xóa/di chuyển thùng ở cột nhãn tầng."), 400

        if action == "add":
            if not value:
                wb.close()
                return jsonify(ok=False, message="Mã thùng không được để trống."), 400
            if source_cell.value not in (None, ""):
                wb.close()
                return jsonify(ok=False, message=f"Ô {source} đã có dữ liệu."), 409
            source_cell.value = value
            source_cell.number_format = "@"

        elif action == "delete":
            if source_cell.value in (None, ""):
                wb.close()
                return jsonify(ok=False, message="Ô này đang trống."), 400
            # Protect structural labels even if a user manually invokes the endpoint.
            current = clean(source_cell.value).casefold()
            if current.startswith("khu ") or current.startswith("tầng"):
                wb.close()
                return jsonify(ok=False, message="Không thể xóa nhãn khu/tầng bằng thao tác xóa thùng."), 400
            source_cell.value = None

        elif action == "move":
            if not target:
                wb.close()
                return jsonify(ok=False, message="Chưa chọn vị trí đích."), 400
            if source == target:
                wb.close()
                return jsonify(ok=False, message="Vị trí đích trùng vị trí ban đầu."), 400
            target_cell = editable_excel_cell(ws, target)
            _, target_col = coordinate_to_tuple(target)
            if target_col < 2:
                wb.close()
                return jsonify(ok=False, message="Không thể di chuyển thùng vào cột nhãn tầng."), 400
            if source_cell.value in (None, ""):
                wb.close()
                return jsonify(ok=False, message="Vị trí nguồn không có thùng."), 400
            if target_cell.value not in (None, ""):
                wb.close()
                return jsonify(ok=False, message=f"Ô {target} đã có dữ liệu. Hãy chọn ô trống."), 409
            current = clean(source_cell.value).casefold()
            if current.startswith("khu ") or current.startswith("tầng"):
                wb.close()
                return jsonify(ok=False, message="Không thể di chuyển nhãn khu/tầng như thùng."), 400
            target_cell.value = str(source_cell.value)
            target_cell.number_format = "@"
            source_cell.value = None
        else:
            wb.close()
            return jsonify(ok=False, message="Thao tác không hợp lệ."), 400

        wb.save(EXCEL_FILE)
        wb.close()
        return jsonify(ok=True, message="Đã lưu thay đổi vào rack.xlsx.", reload=True)
    except PermissionError:
        return jsonify(ok=False, message="Không lưu được. Hãy đóng rack.xlsx trong Excel rồi thử lại."), 409
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except Exception as exc:
        return jsonify(ok=False, message=f"Lỗi khi cập nhật Excel: {exc}"), 500


@app.route("/color-cells", methods=["POST"])
def color_cells():
    """Apply a user-selected background color to multiple rack cells and persist it in Excel."""
    payload = request.get_json(silent=True) or {}
    sheet_name = clean(payload.get("sheet", ""))
    coordinates = payload.get("cells", [])
    color = clean(payload.get("color", "")).lstrip("#").upper()
    if not EXCEL_FILE.exists():
        return jsonify(ok=False, message="Không tìm thấy rack.xlsx."), 404
    if not sheet_name or not isinstance(coordinates, list) or not coordinates:
        return jsonify(ok=False, message="Hãy chọn ít nhất một ô trên cùng một sheet."), 400
    if not re.fullmatch(r"[0-9A-F]{6}", color):
        return jsonify(ok=False, message="Mã màu không hợp lệ."), 400
    try:
        wb = load_workbook(EXCEL_FILE)
        if sheet_name not in wb.sheetnames:
            wb.close()
            return jsonify(ok=False, message="Không tìm thấy sheet."), 404
        ws = wb[sheet_name]
        valid = []
        for coordinate in coordinates:
            coordinate = clean(coordinate).upper()
            if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", coordinate):
                continue
            # Do not paint label/merged child cells; reject merged children to protect workbook geometry.
            merged_child = False
            for merged_range in ws.merged_cells.ranges:
                if coordinate in merged_range:
                    anchor = ws.cell(merged_range.min_row, merged_range.min_col).coordinate
                    if coordinate != anchor:
                        merged_child = True
                    break
            if not merged_child:
                valid.append(coordinate)
        if not valid:
            wb.close()
            return jsonify(ok=False, message="Các ô đã chọn không thể tô màu (có thể thuộc vùng gộp)."), 400
        fill = PatternFill(fill_type="solid", fgColor=color)
        for coordinate in valid:
            ws[coordinate].fill = fill
        wb.save(EXCEL_FILE)
        wb.close()
        return jsonify(ok=True, message=f"Đã tô màu {len(valid)} ô và lưu vào rack.xlsx.", reload=True)
    except PermissionError:
        return jsonify(ok=False, message="Không lưu được. Hãy đóng rack.xlsx trong Excel rồi thử lại."), 409
    except Exception as exc:
        return jsonify(ok=False, message=f"Lỗi khi tô màu: {exc}"), 500


@app.route("/export")
def export_excel():
    if not EXCEL_FILE.exists():
        flash("Không tìm thấy rack.xlsx.", "error")
        return redirect(url_for("index"))
    return send_file(EXCEL_FILE, as_attachment=True, download_name="rack.xlsx")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
