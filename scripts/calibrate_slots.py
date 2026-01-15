# scripts/calibrate_slots.py
# Calibra ROI degli slot sul piano di gioco.
# - Cattura frame
# - Warp top-down con ArUco
# - Salva background warpato (foglio vuoto)
# - Selezione manuale 5 ROI con drag mouse (rettangolo + croce al centro)
# - Stampa YAML da incollare in data/config.yaml

import os
import sys
import time
import cv2
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.board_vision import build_board_vision_from_config_dict


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def draw_cross(img, cx, cy, size=10, thickness=2):
    cv2.line(img, (cx - size, cy), (cx + size, cy), (0, 255, 0), thickness)
    cv2.line(img, (cx, cy - size), (cx, cy + size), (0, 255, 0), thickness)


def draw_slots_overlay(topdown_bgr, rois):
    """Disegna ROI + croce centro + indice sopra l'immagine topdown."""
    img = topdown_bgr.copy()
    for i, (x, y, w, h) in enumerate(rois):
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cx, cy = x + w // 2, y + h // 2
        draw_cross(img, cx, cy, size=12, thickness=2)
        cv2.putText(
            img,
            f"slot {i}",
            (x + 5, y + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
    return img


def select_rois_drag(img_bgr, n_rois=5, window_name="Calibrate ROIs"):
    """
    UI manuale:
      - drag mouse per disegnare rettangolo
      - ENTER per confermare ROI corrente
      - R reset ROI corrente
      - U undo ultima ROI confermata
      - Q quit (solo se rois == n_rois)
    """
    base = img_bgr.copy()
    rois = []

    drawing = False
    x0 = y0 = x1 = y1 = 0
    has_current = False  # esiste un rettangolo corrente disegnato ma non confermato

    def redraw():
        vis = base.copy()

        # ROI già confermate
        for i, (x, y, w, h) in enumerate(rois):
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cx, cy = x + w // 2, y + h // 2
            draw_cross(vis, cx, cy, size=12, thickness=2)
            cv2.putText(
                vis, f"slot {i}", (x + 5, y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
            )

        # ROI corrente (in disegno o già disegnata)
        if has_current:
            xa, xb = sorted([x0, x1])
            ya, yb = sorted([y0, y1])
            w = xb - xa
            h = yb - ya
            if w > 0 and h > 0:
                cv2.rectangle(vis, (xa, ya), (xb, yb), (0, 200, 255), 2)  # giallo
                cx, cy = xa + w // 2, ya + h // 2
                # croce gialla per "current"
                cv2.line(vis, (cx - 10, cy), (cx + 10, cy), (0, 200, 255), 2)
                cv2.line(vis, (cx, cy - 10), (cx, cy + 10), (0, 200, 255), 2)
                cv2.putText(
                    vis,
                    f"CURRENT -> slot {len(rois)} (ENTER to confirm)",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 200, 255),
                    2,
                )

        # HUD comandi
        hud = [
            "Drag mouse: draw ROI",
            "ENTER: confirm current ROI",
            "R: reset current   U: undo last   Q: quit (after 5 ROI)",
        ]
        y = vis.shape[0] - 60
        for line in hud:
            cv2.putText(vis, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y += 22

        cv2.imshow(window_name, vis)

    def on_mouse(event, x, y, flags, param):
        nonlocal drawing, x0, y0, x1, y1, has_current

        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            has_current = True
            x0, y0 = x, y
            x1, y1 = x, y
            redraw()

        elif event == cv2.EVENT_MOUSEMOVE:
            if drawing:
                x1, y1 = x, y
                redraw()

        elif event == cv2.EVENT_LBUTTONUP:
            if drawing:
                drawing = False
                x1, y1 = x, y
                has_current = True
                redraw()

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, on_mouse)

    print("\n[ROI UI]")
    print("- Trascina col tasto sinistro per disegnare la ROI")
    print("- ENTER per confermare la ROI (slot 0->4)")
    print("- R reset ROI corrente, U annulla ultima ROI confermata")
    print("- Q per uscire (solo quando hai 5 ROI)\n")

    redraw()

    while True:
        key = cv2.waitKey(20) & 0xFF

        if key == ord('r'):
            # reset current
            has_current = False
            drawing = False
            redraw()

        elif key == ord('u'):
            # undo last confirmed
            if rois:
                rois.pop()
                print("↩️ Undo ultima ROI. Ora count =", len(rois))
            has_current = False
            drawing = False
            redraw()

        elif key == ord('q'):
            if len(rois) == n_rois:
                break
            print(f"⚠️ Hai {len(rois)}/{n_rois} ROI. Completa prima.")
            redraw()

        elif key in (13, 10):  # ENTER
            if not has_current:
                print("⚠️ Nessuna ROI corrente. Disegna un rettangolo col mouse.")
                continue

            xa, xb = sorted([x0, x1])
            ya, yb = sorted([y0, y1])
            w = xb - xa
            h = yb - ya

            if w < 10 or h < 10:
                print("⚠️ ROI troppo piccola. Riprova.")
                has_current = False
                redraw()
                continue

            if len(rois) >= n_rois:
                print("⚠️ Hai già 5 ROI. Premi Q per uscire o U per annullare.")
                continue

            rois.append([int(xa), int(ya), int(w), int(h)])
            print(f"✅ Confermata ROI slot {len(rois)-1}: {rois[-1]}")
            has_current = False
            redraw()

            if len(rois) == n_rois:
                print("✅ Selezionate 5 ROI. Premi Q per finire (o U per correggere).")

        # ESC: exit senza salvare
        elif key == 27:
            cv2.destroyAllWindows()
            raise RuntimeError("Calibrazione annullata (ESC).")

    cv2.destroyAllWindows()
    return rois


def capture_warp_with_retries(vision, max_tries=10, sleep_s=0.2):
    """Cattura e warpa con retry per marker instabili."""
    last_err = None
    for attempt in range(max_tries):
        frame = vision.capture_frame()
        try:
            topdown, dbg = vision.warper.warp(frame)
            return topdown, dbg
        except Exception as e:
            last_err = e
            print(f"⚠️ Tentativo {attempt+1}/{max_tries} fallito: {e}")
            time.sleep(sleep_s)
    raise RuntimeError(f"Non riesco a fare warp dopo {max_tries} tentativi. Ultimo errore: {last_err}")


def main():
    cfg_path = os.path.join("data", "config.yaml")
    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))

    vision = build_board_vision_from_config_dict(cfg)

    ensure_dir("data/calibration")

    print("Metti il foglio VUOTO (senza blocchi) e premi INVIO...")
    input()

    # 1) cattura + warp (robusto con retry)
    topdown, _ = capture_warp_with_retries(vision, max_tries=10)

    # 2) salva background warpato (foglio vuoto)
    cv2.imwrite("data/calibration/board_bg.png", topdown)
    cv2.imwrite("data/calibration/board_topdown.png", topdown)
    print("✅ Salvati:")
    print("  - data/calibration/board_bg.png")
    print("  - data/calibration/board_topdown.png")

    # 3) selezione ROI slot (drag + ENTER)
    print("\nOra seleziona le 5 ROI (slot 0→4 da sinistra a destra).")
    rois = select_rois_drag(topdown, n_rois=5, window_name="Calibrate ROIs")

    # 4) salva overlay di verifica
    overlay = draw_slots_overlay(topdown, rois)
    cv2.imwrite("data/calibration/board_slots_overlay.png", overlay)
    print("✅ Salvato: data/calibration/board_slots_overlay.png (verifica ROI)")

    # 5) stampa YAML da incollare
    print("\n--- INCOLLA QUESTO in data/config.yaml sotto vision: ---")
    print("  slots_roi_px:")
    for r in rois:
        print(f"    - [{r[0]}, {r[1]}, {r[2]}, {r[3]}]")


if __name__ == "__main__":
    main()
