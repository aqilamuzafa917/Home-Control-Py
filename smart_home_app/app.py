"""UI entry point for the Smart Home desktop application."""

from __future__ import annotations

import io
import threading
import webbrowser
from typing import Iterable

import customtkinter as ctk
from PIL import Image

from .cloud import Device, XiaomiCloudEngine
from .config import delete_credentials, load_credentials, save_credentials
from .constants import (
    APP_TITLE,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BTN_SEC,
    COLOR_CARD,
    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_POWER_OFF,
    COLOR_POWER_ON,
    COLOR_POWER_ON_TEXT,
    COLOR_RED,
    COLOR_TEXT,
    COLOR_TEXT_SEC,
    DEFAULT_DIMMING,
    DEFAULT_SIZE,
    DEFAULT_TEMP,
    ICON_WIDTH,
    MIN_SIZE,
    PROP_AQI,
    PROP_FAVORITE,
    PROP_FILTER,
    PROP_MODE,
    PROP_POWER,
)
from .wiz import WiZLightClient


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SmartHomeApp(ctk.CTk):
    """Main application window that hosts the WiZ and Xiaomi tabs."""

    def __init__(self) -> None:
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(DEFAULT_SIZE)
        self.minsize(*MIN_SIZE)
        self.configure(fg_color=COLOR_BG)
        try:
            self.attributes("-type", "dialog")
        except Exception:
            pass

        self.wiz_client = WiZLightClient()
        self.wiz_is_syncing = False
        self.wiz_state = False

        self.air_engine = XiaomiCloudEngine()
        self.air_device: Device | None = None

        # --- Navigation
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(pady=(20, 10), padx=40, fill="x")
        self.seg_nav = ctk.CTkSegmentedButton(
            nav_frame,
            values=["WiZ Light", "Xiaomi Air Purifier"],
            command=self.switch_tab,
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT,
            font=("SF Pro Text", 13, "bold"),
        )
        self.seg_nav.pack(fill="x")
        self.seg_nav.set("WiZ Light")

        # --- Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.view_wiz = ctk.CTkFrame(self.container, fg_color=COLOR_CARD, corner_radius=20)
        self.view_air = ctk.CTkFrame(self.container, fg_color="transparent")

        self._init_wiz_ui()
        self._init_air_ui()

        self.switch_tab("WiZ Light")
        self.after(500, self.wiz_scan_task_threaded)
        self.after(800, self.air_check_saved_login)

    # ------------------------------------------------------------------ #
    # Tabs
    # ------------------------------------------------------------------ #
    def switch_tab(self, value: str) -> None:
        self.view_wiz.pack_forget()
        self.view_air.pack_forget()
        if value == "WiZ Light":
            self.view_wiz.pack(fill="both", expand=True, pady=10)
        else:
            self.view_air.pack(fill="both", expand=True, pady=10)

    # ------------------------------------------------------------------ #
    # WiZ UI + logic
    # ------------------------------------------------------------------ #
    def _init_wiz_ui(self) -> None:
        self.lbl_wiz_status = ctk.CTkLabel(
            self.view_wiz, text="Searching...", font=("SF Pro Text", 12), text_color=COLOR_TEXT_SEC
        )
        self.lbl_wiz_status.pack(pady=(20, 0))

        self.btn_wiz_power = ctk.CTkButton(
            self.view_wiz,
            text="⏻",
            command=self.wiz_toggle,
            width=100,
            height=100,
            corner_radius=50,
            font=("SF Pro Display", 40),
            fg_color=COLOR_POWER_OFF,
            hover_color="#48484A",
            text_color=COLOR_TEXT_SEC,
        )
        self.btn_wiz_power.pack(pady=(30, 30))

        # Temperature
        frame_t_head = ctk.CTkFrame(self.view_wiz, fg_color="transparent")
        frame_t_head.pack(fill="x", padx=25, pady=(10, 5))
        ctk.CTkLabel(
            frame_t_head, text="Temperature", font=("SF Pro Text", 13, "bold"), text_color=COLOR_TEXT
        ).pack(side="left")
        self.lbl_wiz_temp = ctk.CTkLabel(
            frame_t_head, text=f"{DEFAULT_TEMP}K", font=("SF Pro Text", 13), text_color=COLOR_TEXT_SEC
        )
        self.lbl_wiz_temp.pack(side="right")

        frame_t_sl = ctk.CTkFrame(self.view_wiz, fg_color="transparent")
        frame_t_sl.pack(fill="x", padx=15, pady=(0, 20))
        for col in range(3):
            frame_t_sl.grid_columnconfigure(col, weight=0 if col != 1 else 1)

        ctk.CTkLabel(frame_t_sl, text="🔥", font=("Arial", 20), width=ICON_WIDTH).grid(row=0, column=0)
        self.sl_wiz_temp = ctk.CTkSlider(
            frame_t_sl,
            from_=2200,
            to=6500,
            height=24,
            fg_color="#48484A",
            button_color="white",
            command=self.wiz_update_labels,
        )
        self.sl_wiz_temp.set(DEFAULT_TEMP)
        self.sl_wiz_temp.grid(row=0, column=1, sticky="ew", padx=5)
        self.sl_wiz_temp.bind("<ButtonRelease-1>", self.wiz_send_pilot)
        ctk.CTkLabel(frame_t_sl, text="❄️", font=("Arial", 20), width=ICON_WIDTH).grid(row=0, column=2)

        # Brightness
        frame_b_head = ctk.CTkFrame(self.view_wiz, fg_color="transparent")
        frame_b_head.pack(fill="x", padx=25, pady=(5, 5))
        ctk.CTkLabel(
            frame_b_head, text="Brightness", font=("SF Pro Text", 13, "bold"), text_color=COLOR_TEXT
        ).pack(side="left")
        self.lbl_wiz_dim = ctk.CTkLabel(
            frame_b_head, text=f"{DEFAULT_DIMMING}%", font=("SF Pro Text", 13), text_color=COLOR_TEXT_SEC
        )
        self.lbl_wiz_dim.pack(side="right")

        frame_b_sl = ctk.CTkFrame(self.view_wiz, fg_color="transparent")
        frame_b_sl.pack(fill="x", padx=15, pady=(0, 30))
        for col in range(3):
            frame_b_sl.grid_columnconfigure(col, weight=0 if col != 1 else 1)

        ctk.CTkLabel(
            frame_b_sl, text="🔅", font=("Arial", 20), text_color=COLOR_TEXT_SEC, width=ICON_WIDTH
        ).grid(row=0, column=0)
        self.sl_wiz_dim = ctk.CTkSlider(
            frame_b_sl,
            from_=10,
            to=100,
            height=24,
            fg_color="#48484A",
            progress_color="white",
            button_color="white",
            command=self.wiz_update_labels,
        )
        self.sl_wiz_dim.set(DEFAULT_DIMMING)
        self.sl_wiz_dim.grid(row=0, column=1, sticky="ew", padx=5)
        self.sl_wiz_dim.bind("<ButtonRelease-1>", self.wiz_send_pilot)
        ctk.CTkLabel(
            frame_b_sl, text="🔆", font=("Arial", 20), text_color=COLOR_TEXT_SEC, width=ICON_WIDTH
        ).grid(row=0, column=2)

        tools = ctk.CTkFrame(self.view_wiz, fg_color="transparent")
        tools.pack(pady=20, padx=20, fill="x")

        self.wiz_combo = ctk.CTkOptionMenu(
            tools,
            values=["Scanning..."],
            fg_color="#3A3A3C",
            button_color="#3A3A3C",
            button_hover_color="#48484A",
            text_color=COLOR_TEXT_SEC,
            font=("SF Pro Text", 12),
            height=28,
        )
        self.wiz_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_wiz_scan = ctk.CTkButton(
            tools,
            text="Scan & Sync",
            command=self.wiz_scan_task_threaded,
            width=100,
            height=28,
            fg_color="#3A3A3C",
            hover_color="#48484A",
            text_color=COLOR_TEXT,
            font=("Arial", 13, "bold"),
        )
        self.btn_wiz_scan.pack(side="right")

    def wiz_scan_task_threaded(self) -> None:
        self.lbl_wiz_status.configure(text="Scanning...")
        threading.Thread(target=self.wiz_scan_task, daemon=True).start()

    def wiz_scan_task(self) -> None:
        found = self.wiz_client.scan()
        if found:
            self.wiz_combo.configure(values=found)
            if self.wiz_combo.get() not in found:
                self.wiz_combo.set(found[0])
            self._wiz_sync()
        else:
            self.lbl_wiz_status.configure(text="No lights found")

    def _wiz_sync(self) -> None:
        ip = self.wiz_get_ip()
        if not ip:
            return
        self.wiz_is_syncing = True
        self.lbl_wiz_status.configure(text="Syncing...")
        res = self.wiz_client.get_state(ip)
        if res and "result" in res:
            self.after(0, lambda: self._apply_wiz_data(res["result"]))
        self.wiz_is_syncing = False

    def _apply_wiz_data(self, data: dict) -> None:
        self.wiz_state = data.get("state", False)
        self.wiz_update_power_ui()
        if "temp" in data:
            self.sl_wiz_temp.set(data["temp"])
        if "dimming" in data:
            self.sl_wiz_dim.set(data["dimming"])
        self.wiz_update_labels(0)
        self.lbl_wiz_status.configure(text="Connected")

    def wiz_get_ip(self) -> str | None:
        val = self.wiz_combo.get()
        return val if val not in {"Scanning...", "No lights"} else None

    def wiz_toggle(self) -> None:
        self.wiz_state = not self.wiz_state
        self.wiz_update_power_ui()
        ip = self.wiz_get_ip()
        threading.Thread(target=self.wiz_client.set_power, args=(ip, self.wiz_state), daemon=True).start()

    def wiz_update_power_ui(self) -> None:
        if self.wiz_state:
            self.btn_wiz_power.configure(
                fg_color=COLOR_POWER_ON, text_color=COLOR_POWER_ON_TEXT, hover_color="#F2F2F7"
            )
        else:
            self.btn_wiz_power.configure(
                fg_color=COLOR_POWER_OFF, text_color=COLOR_TEXT_SEC, hover_color="#48484A"
            )

    def wiz_send_pilot(self, _event) -> None:
        if self.wiz_is_syncing:
            return
        ip = self.wiz_get_ip()
        payload = (int(self.sl_wiz_temp.get()), int(self.sl_wiz_dim.get()))
        threading.Thread(target=lambda: self.wiz_client.set_pilot(ip, *payload), daemon=True).start()

    def wiz_update_labels(self, _value) -> None:
        k = float(self.sl_wiz_temp.get())
        if k < 4000:
            ratio = (k - 2200) / 1800
            r, g, b = 255, int(160 + (95 * ratio)), int(70 + (185 * ratio))
        else:
            ratio = (k - 4000) / 2500
            r, g, b = int(255 - (50 * ratio)), int(255 - (20 * ratio)), 255
        self.sl_wiz_temp.configure(progress_color=f"#{r:02x}{g:02x}{b:02x}")
        self.lbl_wiz_temp.configure(text=f"{int(k)}K")
        self.lbl_wiz_dim.configure(text=f"{int(self.sl_wiz_dim.get())}%")

    # ------------------------------------------------------------------ #
    # Xiaomi UI + logic
    # ------------------------------------------------------------------ #
    def _init_air_ui(self) -> None:
        self.frame_air_login = ctk.CTkFrame(self.view_air, fg_color=COLOR_CARD, corner_radius=20)
        ctk.CTkLabel(
            self.frame_air_login, text="Xiaomi Setup", font=("SF Pro Display", 22, "bold")
        ).pack(pady=25)
        self.qr_label = ctk.CTkLabel(self.frame_air_login, text="", width=200, height=200)
        self.qr_label.pack(pady=10)

        self.btn_qr_gen = ctk.CTkButton(
            self.frame_air_login,
            text="Generate QR Code",
            command=self.air_start_login,
            fg_color=COLOR_ACCENT,
            hover_color="#0060C0",
            height=32,
        )
        self.btn_qr_gen.pack(pady=(10, 5))

        self.btn_open_browser = ctk.CTkButton(
            self.frame_air_login,
            text="Open in Browser ⎋",
            command=self.air_open_link,
            fg_color=COLOR_BTN_SEC,
            hover_color="#48484A",
            text_color=COLOR_TEXT,
            height=32,
            state="disabled",
        )
        self.btn_open_browser.pack(pady=5)

        self.lbl_air_status = ctk.CTkLabel(self.frame_air_login, text="Ready", text_color=COLOR_TEXT_SEC)
        self.lbl_air_status.pack(pady=15)

        self.frame_air_dash = ctk.CTkFrame(self.view_air, fg_color=COLOR_CARD, corner_radius=20)
        self.lbl_aqi_title = ctk.CTkLabel(
            self.frame_air_dash, text="Air Quality (PM2.5)", font=("SF Pro Text", 12), text_color=COLOR_TEXT_SEC
        )
        self.lbl_aqi_title.pack(pady=(20, 0))

        self.btn_aqi_val = ctk.CTkButton(
            self.frame_air_dash,
            text="--",
            font=("SF Pro Display", 70, "bold"),
            text_color=COLOR_TEXT,
            fg_color="transparent",
            hover_color=COLOR_BTN_SEC,
            height=75,
            command=self._air_sync_thread,
        )
        self.btn_aqi_val.pack(pady=(0, 10))

        self.btn_air_power = ctk.CTkButton(
            self.frame_air_dash,
            text="⏻",
            command=self.air_toggle,
            width=90,
            height=90,
            corner_radius=45,
            font=("SF Pro Display", 36),
            fg_color=COLOR_POWER_OFF,
            hover_color="#48484A",
            text_color=COLOR_TEXT_SEC,
        )
        self.btn_air_power.pack(pady=10)

        self.seg_air_mode = ctk.CTkSegmentedButton(
            self.frame_air_dash,
            values=["Auto", "Silent", "Manual"],
            command=self.air_set_mode,
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT,
        )
        self.seg_air_mode.pack(pady=20, padx=30, fill="x")

        self.frame_air_man = ctk.CTkFrame(self.frame_air_dash, fg_color="transparent")
        for col in range(3):
            self.frame_air_man.grid_columnconfigure(col, weight=0 if col != 1 else 1)

        ctk.CTkLabel(self.frame_air_man, text="💨", font=("Arial", 20), width=ICON_WIDTH).grid(row=0, column=0)
        self.sl_air_fan = ctk.CTkSlider(
            self.frame_air_man,
            from_=1,
            to=14,
            number_of_steps=13,
            height=24,
            progress_color=COLOR_ACCENT,
            button_color="white",
        )
        self.sl_air_fan.grid(row=0, column=1, sticky="ew", padx=5)
        self.sl_air_fan.bind("<ButtonRelease-1>", self.air_set_speed)
        ctk.CTkLabel(
            self.frame_air_man,
            text="MAX",
            font=("SF Pro Text", 10, "bold"),
            width=ICON_WIDTH,
            text_color=COLOR_TEXT_SEC,
        ).grid(row=0, column=2)

        self.frame_air_info = ctk.CTkFrame(self.view_air, fg_color="transparent")
        self.lbl_filter = ctk.CTkLabel(
            self.frame_air_info, text="Filter: --%", font=("SF Pro Text", 12), text_color=COLOR_TEXT_SEC
        )
        self.lbl_filter.pack(pady=(10, 5))
        self.btn_logout = ctk.CTkButton(
            self.frame_air_info,
            text="Logout",
            command=self.air_logout,
            width=60,
            fg_color="transparent",
            text_color=COLOR_RED,
            hover_color=COLOR_BG,
            font=("SF Pro Text", 12),
        )
        self.btn_logout.pack(pady=0)

    def air_check_saved_login(self) -> None:
        ip, token = load_credentials()
        if ip and token:
            self.air_connect(ip, token)
        else:
            self.frame_air_login.pack(pady=20, padx=10, fill="both")

    def air_start_login(self) -> None:
        self.btn_qr_gen.configure(state="disabled")
        self.lbl_air_status.configure(text="Generating QR...", text_color="white")
        threading.Thread(target=self._air_login_worker, daemon=True).start()

    def air_open_link(self) -> None:
        if self.air_engine.login_url:
            webbrowser.open(self.air_engine.login_url)

    def _air_login_worker(self) -> None:
        try:
            img_url, lp_url = self.air_engine.step_1_get_qr()
            if not img_url or not lp_url:
                raise RuntimeError("Failed to obtain QR login information.")

            self.after(0, lambda: self.btn_open_browser.configure(state="normal"))
            img_bytes = self.air_engine.step_2_download_img(img_url)
            pil_img = Image.open(io.BytesIO(img_bytes))
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(180, 180))
            self.after(0, lambda: self.qr_label.configure(image=ctk_img))
            self.after(
                0, lambda: self.lbl_air_status.configure(text="Scan QR with Mi Home App", text_color=COLOR_ACCENT)
            )

            if self.air_engine.step_3_poll(lp_url):
                self.after(
                    0,
                    lambda: self.lbl_air_status.configure(
                        text="Authenticated. Fetching token...", text_color=COLOR_GREEN
                    ),
                )
                if self.air_engine.step_4_service_token():
                    devices = self.air_engine.get_devices()
                    target = next((d for d in devices if d.get("localip") and d.get("token")), None)
                    if target:
                        save_credentials(target["localip"], target["token"])
                        self.after(0, lambda: self.air_connect(target["localip"], target["token"]))
                    else:
                        self.after(
                            0,
                            lambda: self.lbl_air_status.configure(
                                text="No supported device found", text_color=COLOR_RED
                            ),
                        )
        except Exception as exc:
            self.after(
                0,
                lambda: self.lbl_air_status.configure(
                    text=f"Login failed: {exc}", text_color=COLOR_RED
                ),
            )

    def air_connect(self, ip: str, token: str) -> None:
        if Device is None:
            self.lbl_air_status.configure(text="python-miio missing", text_color=COLOR_RED)
            return
        self.frame_air_login.pack_forget()
        self.frame_air_dash.pack(fill="both", expand=True, pady=0)
        self.frame_air_info.pack(fill="x", pady=10)
        threading.Thread(target=self._air_init_device, args=(ip, token), daemon=True).start()

    def _air_init_device(self, ip: str, token: str) -> None:
        try:
            self.air_device = Device(ip, token)
            self._air_sync_once()
        except Exception as exc:
            self.after(
                0,
                lambda: self.lbl_air_status.configure(text=f"Connection failed: {exc}", text_color=COLOR_RED),
            )

    def _air_sync_thread(self) -> None:
        threading.Thread(target=self._air_sync_once, daemon=True).start()

    def _air_sync_once(self) -> None:
        if not self.air_device:
            return
        try:
            props = [PROP_POWER, PROP_MODE, PROP_AQI, PROP_FAVORITE, PROP_FILTER]
            res = self.air_device.send("get_properties", props)
            self.after(0, lambda: self.air_update_ui(res))
        except Exception as exc:
            self.after(0, lambda: self.lbl_air_status.configure(text=f"Sync failed: {exc}", text_color=COLOR_RED))

    def air_update_ui(self, results: list[dict]) -> None:
        if not results:
            return

        # Power
        power_payload = results[0]
        is_on = power_payload.get("value", False) if power_payload.get("code") == 0 else False
        if is_on:
            self.btn_air_power.configure(
                fg_color=COLOR_POWER_ON, text_color=COLOR_POWER_ON_TEXT, hover_color="#F2F2F7"
            )
        else:
            self.btn_air_power.configure(
                fg_color=COLOR_POWER_OFF, text_color=COLOR_TEXT_SEC, hover_color="#48484A"
            )

        # Mode
        mode_payload = results[1]
        mode_val = mode_payload.get("value") if mode_payload.get("code") == 0 else 0
        mode_map = {0: "Auto", 1: "Silent", 2: "Manual"}
        current_mode = mode_map.get(mode_val, "Auto")
        self.seg_air_mode.set(current_mode)
        if current_mode == "Manual":
            self.frame_air_man.pack(fill="x", padx=15, pady=(0, 20))
        else:
            self.frame_air_man.pack_forget()

        # AQI
        aqi_payload = results[2]
        aqi = aqi_payload.get("value") if aqi_payload.get("code") == 0 else 0
        color = COLOR_GREEN if aqi < 30 else COLOR_ORANGE if aqi < 100 else COLOR_RED
        self.btn_aqi_val.configure(text=str(aqi), text_color=color)

        # Speed
        speed_payload = results[3]
        spd = speed_payload.get("value") if speed_payload.get("code") == 0 else 1
        self.sl_air_fan.set(spd)

        # Filter
        filter_payload = results[4]
        life = filter_payload.get("value") if filter_payload.get("code") == 0 else 0
        self.lbl_filter.configure(text=f"Filter Life: {life}%")

    def air_toggle(self) -> None:
        if not self.air_device:
            return

        def _task() -> None:
            try:
                res = self.air_device.send("get_properties", [PROP_POWER])
                curr = res[0]["value"]
                self.air_device.send("set_properties", [{"siid": 2, "piid": 1, "value": not curr}])
                self._air_sync_once()
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()

    def air_set_mode(self, mode: str) -> None:
        if not self.air_device:
            return
        val_map = {"Auto": 0, "Silent": 1, "Manual": 2}

        def _task() -> None:
            self.air_device.send("set_properties", [{"siid": 2, "piid": 4, "value": val_map[mode]}])
            self._air_sync_once()

        threading.Thread(target=_task, daemon=True).start()

    def air_set_speed(self, _event) -> None:
        if not self.air_device:
            return
        val = int(self.sl_air_fan.get())

        def _task() -> None:
            self.air_device.send("set_properties", [{"siid": 9, "piid": 11, "value": val}])
            self.air_device.send("set_properties", [{"siid": 2, "piid": 4, "value": 2}])
            self._air_sync_once()

        threading.Thread(target=_task, daemon=True).start()

    def air_logout(self) -> None:
        delete_credentials()
        self.air_device = None
        self.frame_air_dash.pack_forget()
        self.frame_air_info.pack_forget()
        self.frame_air_login.pack(pady=20, padx=10, fill="both")
        self.btn_qr_gen.configure(state="normal")
        self.btn_open_browser.configure(state="disabled")
        self.qr_label.configure(image=None)
        self.lbl_air_status.configure(text="Logged Out")


def run_app() -> None:
    app = SmartHomeApp()
    app.mainloop()

