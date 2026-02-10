import ezdxf
from ezdxf import bbox
import math

def get_all_entities(doc):
    msp = doc.modelspace()
    for e in msp:
        if e.dxftype() == "INSERT":
            if e.dxf.name in doc.blocks:
                block = doc.blocks.get(e.dxf.name)
                for block_entity in block:
                    yield block_entity
        else:
            yield e

def get_length(e):
    try:
        t = e.dxftype()
        if t == "LINE":
            return math.dist(e.dxf.start, e.dxf.end)
        elif t == "ARC":
            return abs(math.radians(e.dxf.end_angle - e.dxf.start_angle)) * e.dxf.radius
        elif t == "CIRCLE":
            return 2 * math.pi * e.dxf.radius
        elif t in ["LWPOLYLINE", "POLYLINE"]:
            from ezdxf import path
            p = path.make_path(e)
            return sum(line.length for line in p.flattening(distance=0.5))
    except:
        return 0.0
    return 0.0

def calculate_dxf_metrics(file_path: str) -> tuple[float, float]:
    """
    Returns:
      (cut_length_mm, area_mm2)
    Note: area uses bbox extents like your previous system.
    """
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    box = bbox.extents(msp)
    part_area_mm2 = float(box.size.x * box.size.y)

    part_cut_len = 0.0
    for e in get_all_entities(doc):
        if e.dxftype() not in ["TEXT", "MTEXT", "DIMENSION", "HATCH"]:
            part_cut_len += float(get_length(e))

    return float(part_cut_len), float(part_area_mm2)
