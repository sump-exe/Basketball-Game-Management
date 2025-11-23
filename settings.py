"""
Minimal DB-backed settings module.

Purpose:
- Persist two simple settings: team_size (int) and seasons_enabled (bool).
- Provide an open_settings_popup(parent) that only:
    * validates and saves the settings to DB
    * closes the settings popup
    * calls scheduleGameTab.update_schedule_optionmenus(...) via mainGui.refs so the
      Schedule Game team dropdowns update immediately in the current session.
- Does NOT close/open any application windows.
"""
import customtkinter as ctk
from tkinter import messagebox
from theDB import mydb

# Defaults
_DEFAULTS = {
    "team_size": 12,
    "seasons_enabled": True
}
_TABLE_NAME = "app_settings"

_last_popup = None


# -----------------------
# DB helpers
# -----------------------
def _ensure_table():
    cur = mydb.cursor()
    try:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        mydb.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _load_all_from_db():
    _ensure_table()
    cur = mydb.cursor()
    try:
        cur.execute(f"SELECT key, value FROM {_TABLE_NAME}")
        rows = cur.fetchall()
        out = {}
        for k, v in rows:
            out[k] = v
        return out
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _save_key_value(key, value):
    _ensure_table()
    cur = mydb.cursor()
    try:
        cur.execute(f"INSERT OR REPLACE INTO {_TABLE_NAME} (key, value) VALUES (?, ?)", (key, str(value)))
        mydb.commit()
        return True
    except Exception:
        try:
            mydb.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            cur.close()
        except Exception:
            pass


# -----------------------
# Public API
# -----------------------
def get_settings():
    raw = _load_all_from_db()
    out = {}
    ts = raw.get("team_size")
    try:
        out["team_size"] = int(ts) if ts is not None else _DEFAULTS["team_size"]
    except Exception:
        out["team_size"] = _DEFAULTS["team_size"]
    se = raw.get("seasons_enabled")
    if se is None:
        out["seasons_enabled"] = _DEFAULTS["seasons_enabled"]
    else:
        s = str(se).strip().lower()
        out["seasons_enabled"] = s in ("1", "true", "yes", "on")
    return out


def save_settings(settings: dict) -> bool:
    ok = True
    if "team_size" in settings:
        try:
            ts = int(settings["team_size"])
        except Exception:
            ts = _DEFAULTS["team_size"]
        ok = ok and _save_key_value("team_size", ts)
    if "seasons_enabled" in settings:
        ok = ok and _save_key_value("seasons_enabled", 1 if bool(settings["seasons_enabled"]) else 0)
    return bool(ok)


# -----------------------
# UI: settings popup
# -----------------------
def open_settings_popup(parent=None):
    """Open the Settings popup (team size, seasons enabled).
    Safe version: NO grab_set(), NO grab_release(), avoids logout misfire.
    """

    global _last_popup

    # Close any existing popup
    if _last_popup is not None:
        if hasattr(_last_popup, "winfo_exists") and _last_popup.winfo_exists():
            try:
                _last_popup.destroy()
            except Exception:
                pass
        _last_popup = None

    # Create popup
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title("Settings")
    win.geometry("360x260")
    win.resizable(False, False)

    # Keep popup above parent but without grab_set()
    try:
        if parent:
            win.transient(parent)     # attach window visually to parent
        win.lift()                    # raise window
        win.attributes("-topmost", True)
        win.after(50, lambda: win.attributes("-topmost", False))
    except Exception:
        pass

    # Store reference
    _last_popup = win

    # ======================================================
    # UI
    # ======================================================
    title = ctk.CTkLabel(win, text="Settings", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(pady=(12, 8))

    # Frame
    frm = ctk.CTkFrame(win)
    frm.pack(padx=20, pady=10, fill="both", expand=True)

    # Team size
    ctk.CTkLabel(frm, text="Team Size:").grid(row=0, column=0, sticky="w", pady=5)
    team_size_entry = ctk.CTkEntry(frm, width=80)
    team_size_entry.grid(row=0, column=1, sticky="w", pady=5)

    # Seasons Enabled
    seasons_var = ctk.BooleanVar()
    seasons_check = ctk.CTkCheckBox(frm, text="Enable Seasons", variable=seasons_var)
    seasons_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

    # Load saved settings
    try:
        cur_settings = get_settings()
    except Exception:
        cur_settings = {}
    if cur_settings:
        team_size_entry.insert(0, str(cur_settings.get("team_size", "")))
        seasons_var.set(cur_settings.get("seasons_enabled", False))

    # ======================================================
    # Save handler
    # ======================================================
    def _validate_team_size_val(text):
        try:
            ts_val = int(text)
            return ts_val > 0
        except Exception:
            return False

    def _apply_to_schedule_dropdowns():
        """
        Best-effort: call scheduleGameTab.update_schedule_optionmenus with refs
        from mainGui so the dropdown values refresh immediately.
        No windows should be opened or closed here.
        """
        try:
            import mainGui as mg
            refs = getattr(mg, "refs", {}) or {}
            import scheduleGameTab as sgt
        except Exception:
            return
        try:
            sgt.update_schedule_optionmenus(
                refs.get("tab3_team1_opt"),
                refs.get("tab3_team2_opt"),
                refs.get("tab3_venue_opt")
            )
        except Exception:
            pass

    def _on_save_clicked():
        txt = team_size_entry.get().strip()
        if not _validate_team_size_val(txt):
            messagebox.showerror("Invalid Input", "Team size must be a positive integer.")
            return
        ts_val = int(txt)
        seasons_val = bool(seasons_var.get())

        # Persist settings using this module's save_settings
        ok = save_settings({"team_size": ts_val, "seasons_enabled": seasons_val})
        if not ok:
            messagebox.showerror("Settings", "Failed to save settings.")
            return

        # Inform user and close popup
        try:
            messagebox.showinfo("Settings Saved", "Settings have been saved and applied.")
        except Exception:
            pass

        try:
            if hasattr(win, "destroy"):
                win.destroy()
        except Exception:
            pass

        # Clear tracked popup ref
        global _last_popup
        _last_popup = None

        # Immediately apply the change to schedule dropdowns in the running session.
        # This is best-effort and will not open/close other windows.
        _apply_to_schedule_dropdowns()

    # Footer buttons
    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack(pady=10)

    ctk.CTkButton(btn_frame, text="Save", width=80, command=_on_save_clicked).grid(row=0, column=0, padx=10)
    ctk.CTkButton(btn_frame, text="Cancel", width=80, command=lambda: win.destroy()).grid(row=0, column=1, padx=10)

    return win