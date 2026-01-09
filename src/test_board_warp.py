# scripts/test_board_warp.py
# Uso:
#   python scripts/test_board_warp.py --image "/path/img.jpg" --outdir "data/test_logs" \
#       --aruco_dict DICT_4X4_50 --ids 0 1 2 3 --warp_w 1200 --warp_h 500
#
# Note:
# - Serve opencv-contrib-python (non solo opencv-python) per cv2.aruco
# - Se non sai il dizionario, usa --aruco_dict AUTO (prova più dizionari)
# - Se non passi --ids, prende "4 marker migliori" tra quelli trovati.

import os
import argparse
import cv2
import numpy as np


# ----------------------------
# Geometria
# ----------------------------
def order_points_quad(pts: np.ndarray) -> np.ndarray:
    """
    Ordina 4 punti come [TL, TR, BR, BL].
    pts shape: (4,2)
    """
    pts = pts.astype(np.float32)
    s = pts.sum(axis=1)           # x+y
    diff = np.diff(pts, axis=1)   # x-y

    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


# ----------------------------
# ArUco detection helpers
# ----------------------------
def get_aruco_dict(name: str):
    if not hasattr(cv2.aruco, name):
        raise ValueError(f"Unknown ArUco dict name: {name}")
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))


def detect_aruco(gray: np.ndarray, dict_name: str):
    """
    Versione robusta: prova più scale e parametri più permissivi.
    Ritorna (corners, ids, used_dict_name)
    """
    def _make_detector(dname: str):
        aruco_dict = get_aruco_dict(dname)
        params = cv2.aruco.DetectorParameters()

        # Parametri più robusti per webcam/blur
        params.adaptiveThreshWinSizeMin = 3
        params.adaptiveThreshWinSizeMax = 53
        params.adaptiveThreshWinSizeStep = 4
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        params.cornerRefinementWinSize = 5
        params.cornerRefinementMaxIterations = 30
        params.cornerRefinementMinAccuracy = 0.1

        # Permissivo su perimetro (utile se marker piccoli)
        params.minMarkerPerimeterRate = 0.02
        params.maxMarkerPerimeterRate = 4.0

        detector = cv2.aruco.ArucoDetector(aruco_dict, params)
        return detector

    # Preprocess base: equalize per migliorare contrasto
    gray_eq = cv2.equalizeHist(gray)

    # Crea lista dizionari da provare
    if dict_name == "AUTO":
        dicts = [
            "DICT_4X4_50", "DICT_4X4_100", "DICT_4X4_250", "DICT_4X4_1000",
            "DICT_5X5_50", "DICT_5X5_100", "DICT_5X5_250", "DICT_5X5_1000",
            "DICT_6X6_50", "DICT_6X6_100", "DICT_6X6_250", "DICT_6X6_1000",
        ]
    else:
        dicts = [dict_name]

    # Prova più scale (importante se marker sono "pochi pixel")
    scales = [1.0, 1.5, 2.0, 2.5]

    best = ([], None, "NONE")
    best_n = 0

    for dname in dicts:
        detector = _make_detector(dname)
        for s in scales:
            if s == 1.0:
                g = gray_eq
            else:
                g = cv2.resize(gray_eq, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)

            corners, ids, _ = detector.detectMarkers(g)

            n = 0 if ids is None else len(ids)
            if n > best_n:
                best = (corners, ids, dname)
                best_n = n

            # se abbiamo già 4 marker, basta
            if best_n >= 4:
                return best[0], best[1], best[2]

    return best[0], best[1], best[2]



def select_4_markers(corners, ids, expected_ids=None):
    """
    Se expected_ids è dato (lista di 4), seleziona quei marker.
    Altrimenti seleziona 4 marker "migliori" tra quelli trovati (più esterni).
    Ritorna: list di tuple (id, pts(4,2), center(2,))
    """
    if ids is None or len(ids) == 0:
        raise RuntimeError("No markers detected (ids is None/empty).")

    ids_list = ids.flatten().tolist()
    data = []
    for i, mid in enumerate(ids_list):
        pts = corners[i].reshape(4, 2).astype(np.float32)
        center = pts.mean(axis=0)
        data.append((mid, pts, center))

    if expected_ids is not None:
        expected_set = set(expected_ids)
        filtered = [m for m in data if m[0] in expected_set]
        if len(filtered) != 4:
            found = sorted([m[0] for m in filtered])
            raise RuntimeError(f"Expected ids {sorted(expected_set)}, but found only {found}.")
        # Mantieni un ordine stabile: come expected_ids
        filtered.sort(key=lambda x: expected_ids.index(x[0]))
        return filtered

    # Nessun expected: scegli 4 marker più esterni
    centers = np.array([m[2] for m in data], dtype=np.float32)
    global_center = centers.mean(axis=0)

    dists = [float(np.linalg.norm(m[2] - global_center)) for m in data]
    idx = np.argsort(dists)[::-1][:4]  # 4 più lontani
    chosen = [data[i] for i in idx]
    return chosen


def compute_board_corners_from_markers(marker_data):
    """
    marker_data: list di (id, pts(4,2), center(2,))
    Strategia robusta:
      - calcola centro globale
      - per ciascun marker prendi il corner più lontano dal centro globale ("outer corner")
    Ritorna src_quad ordinato [TL,TR,BR,BL]
    """
    centers = np.array([m[2] for m in marker_data], dtype=np.float32)
    global_center = centers.mean(axis=0)

    board_pts = []
    for (mid, pts, _c) in marker_data:
        d = np.linalg.norm(pts - global_center[None, :], axis=1)
        outer = pts[np.argmax(d)]
        board_pts.append(outer)

    board_pts = np.array(board_pts, dtype=np.float32)
    src_quad = order_points_quad(board_pts)
    return src_quad


# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to input JPEG/PNG")
    ap.add_argument("--outdir", default="data/test_logs", help="Output folder")
    ap.add_argument("--aruco_dict", default="AUTO", help="e.g., DICT_4X4_50 or AUTO")
    ap.add_argument("--ids", nargs="*", type=int, default=None, help="Expected 4 marker ids (optional)")
    ap.add_argument("--warp_w", type=int, default=1200, help="Warped width (px)")
    ap.add_argument("--warp_h", type=int, default=500, help="Warped height (px)")
    args = ap.parse_args()

    if not hasattr(cv2, "aruco"):
        raise RuntimeError("cv2.aruco not found. Install opencv-contrib-python (not opencv-python).")

    img = cv2.imread(args.image)
    if img is None:
        raise RuntimeError(f"Cannot read image: {args.image}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    corners, ids, used_dict = detect_aruco(gray, args.aruco_dict)

    # salva debug anche se non trova abbastanza marker
    ensure_dir(args.outdir)
    debug = img.copy()
    if ids is not None and len(ids) > 0:
        cv2.aruco.drawDetectedMarkers(debug, corners, ids)
    cv2.imwrite(os.path.join(args.outdir, "debug_fail.png"), debug)
    print("Saved debug_fail.png to inspect detection")


    if ids is None or len(ids) < 4:
        raise RuntimeError(f"Detected <4 markers. Dict tried/used: {used_dict}. "
                           f"Try another dict or ensure markers are visible.")

    marker_data = select_4_markers(corners, ids, expected_ids=args.ids)
    src_quad = compute_board_corners_from_markers(marker_data)

    W, H = args.warp_w, args.warp_h
    dst_quad = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src_quad, dst_quad)
    topdown = cv2.warpPerspective(img, M, (W, H))

    # ---- Debug visualization ----
    debug = img.copy()
    cv2.aruco.drawDetectedMarkers(debug, corners, ids)

    # Disegna i 4 punti usati per l'omografia
    for p in src_quad.astype(int):
        cv2.circle(debug, tuple(p), 10, (0, 0, 255), -1)
    cv2.polylines(debug, [src_quad.astype(int)], isClosed=True, color=(0, 0, 255), thickness=3)

    # Etichette marker scelti
    for (mid, _pts, c) in marker_data:
        cv2.putText(debug, f"id={mid}", (int(c[0]), int(c[1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    ensure_dir(args.outdir)
    out_top = os.path.join(args.outdir, "topdown.png")
    out_dbg = os.path.join(args.outdir, "debug.png")

    cv2.imwrite(out_top, topdown)
    cv2.imwrite(out_dbg, debug)

    print("=== DONE ===")
    print(f"Used ArUco dict: {used_dict}")
    print(f"Saved: {out_top}")
    print(f"Saved: {out_dbg}")


if __name__ == "__main__":
    main()
