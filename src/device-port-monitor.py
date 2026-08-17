#!/usr/bin/env python3
"""Monitor serial/video ports with a GTK settings UI and AppIndicator."""

import fcntl
import filecmp
import os
import shutil
import subprocess
import sys


APP_NAME = "Device Port Monitor"
SERVICE_NAME = "device-port-monitor.service"
APPIMAGE_PATH = os.environ.get("APPIMAGE", "")
APPDIR_PATH = os.environ.get("APPDIR", "")
WATCHED_NAMES = ("ttyACM", "ttyUSB", "video")
DEBOUNCE_MS = 300
SETTINGS_LOCK_FILE = None


def native_monitor_candidates():
    return (
        os.path.join(APPDIR_PATH, "usr", "bin", "device-port-monitor-monitor"),
        "/usr/lib/device-port-monitor/device-port-monitor-monitor",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".build",
            "device-port-monitor-monitor",
        ),
    )


def run_native_monitor():
    for candidate in native_monitor_candidates():
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            os.execv(candidate, [candidate, "--monitor"])
    print("Native monitor executable not found.", file=sys.stderr)
    return 1


def acquire_settings_instance_lock():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    lock_path = os.path.join(runtime_dir, "device-port-monitor-settings.lock")
    lock_file = None
    try:
        lock_file = open(lock_path, "a", encoding="utf-8")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return None
    except OSError as error:
        if lock_file is not None:
            lock_file.close()
        print(f"Unable to lock the settings window: {error}", file=sys.stderr)
        return False
    return lock_file


if __name__ == "__main__":
    if "--monitor" in sys.argv:
        raise SystemExit(run_native_monitor())
    if "--print-status" not in sys.argv:
        SETTINGS_LOCK_FILE = acquire_settings_instance_lock()
        if SETTINGS_LOCK_FILE is None:
            raise SystemExit(0)

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gdk, Gio, GLib, Gtk


def scan_devices():
    """Scan /dev once for the three device families covered by the usb alias."""
    devices = []
    try:
        with os.scandir("/dev") as entries:
            for entry in entries:
                if is_watched_name(entry.name):
                    devices.append(os.path.join("/dev", entry.name))
    except OSError as error:
        print(f"Unable to scan /dev: {error}", file=sys.stderr)
    return sorted(devices)


def categorize_devices(devices):
    return (
        [path for path in devices if path.startswith("/dev/ttyACM")],
        [path for path in devices if path.startswith("/dev/ttyUSB")],
        [path for path in devices if path.startswith("/dev/video")],
    )


def udev_properties(path):
    """Return udev metadata for a device without keeping helper processes alive."""
    try:
        result = subprocess.run(
            ["udevadm", "info", "--query=property", f"--name={path}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}

    properties = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value
    return properties


def clean_device_name(value):
    return (
        value.replace("\\x20", " ")
        .replace("\\x2c", ",")
        .replace("_", " ")
        .strip()
    )


def device_description(path):
    properties = udev_properties(path)

    if path.startswith("/dev/video"):
        product = clean_device_name(
            properties.get("ID_V4L_PRODUCT")
            or properties.get("ID_MODEL_FROM_DATABASE")
            or properties.get("ID_MODEL", "")
        )
        capabilities = properties.get("ID_V4L_CAPABILITIES", "")
        role = "Video capture" if ":capture:" in capabilities else "Camera metadata"
        return f"{product} · {role}" if product else role

    vendor = clean_device_name(
        properties.get("ID_VENDOR_FROM_DATABASE")
        or properties.get("ID_VENDOR", "")
    )
    model = clean_device_name(
        properties.get("ID_MODEL_FROM_DATABASE")
        or properties.get("ID_MODEL", "")
    )
    hardware = " ".join(part for part in (vendor, model) if part)
    role = (
        "USB ACM serial device"
        if path.startswith("/dev/ttyACM")
        else "USB serial adapter"
    )
    return f"{hardware} · {role}" if hardware else role


def is_watched_name(name):
    return name.startswith(WATCHED_NAMES)


def run_systemctl(*arguments):
    """Run systemctl for the current user's service manager."""
    return subprocess.run(
        ["systemctl", "--user", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def autostart_path():
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    filename = (
        "device-port-monitor-appimage.desktop"
        if APPIMAGE_PATH
        else "device-port-monitor.desktop"
    )
    return os.path.join(config_home, "autostart", filename)


def user_data_home():
    return os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))


def persistent_icon_path():
    return os.path.join(
        user_data_home(),
        "icons",
        "hicolor",
        "256x256",
        "apps",
        "device-port-monitor.png",
    )


def appimage_launcher_path():
    return os.path.join(user_data_home(), "applications", "device-port-monitor.desktop")


def write_text_if_changed(path, contents):
    try:
        with open(path, "r", encoding="utf-8") as current_file:
            if current_file.read() == contents:
                return
    except FileNotFoundError:
        pass
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as output_file:
        output_file.write(contents)
    os.replace(temporary, path)
    os.chmod(path, 0o644)


def quote_desktop_exec(value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    escaped = escaped.replace("`", "\\`")
    return f'"{escaped}"'


def appimage_autostart_is_enabled():
    path = autostart_path()
    try:
        with open(path, "r", encoding="utf-8") as desktop_file:
            contents = desktop_file.read()
    except FileNotFoundError:
        return False
    return (
        "X-Device-Port-Monitor-AppImage=true" in contents
        and f"X-AppImage-Path={APPIMAGE_PATH}" in contents
    )


def install_appimage_integration():
    """Install a persistent icon and app-menu launcher for this AppImage."""
    if not APPIMAGE_PATH:
        return

    source_icon = os.path.join(APPDIR_PATH, "device-port-monitor.png")
    icon_path = persistent_icon_path()
    launcher_path = appimage_launcher_path()
    os.makedirs(os.path.dirname(icon_path), exist_ok=True)
    os.makedirs(os.path.dirname(launcher_path), exist_ok=True)
    if not os.path.isfile(icon_path) or not filecmp.cmp(
        source_icon, icon_path, shallow=False
    ):
        shutil.copyfile(source_icon, icon_path)
        os.chmod(icon_path, 0o644)

    contents = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            "Name=Device Port Monitor",
            "Comment=Monitor ACM, USB serial, and video devices",
            f"Exec={quote_desktop_exec(APPIMAGE_PATH)} --settings",
            "Icon=device-port-monitor",
            "Terminal=false",
            "StartupNotify=true",
            "Categories=Utility;",
            "X-Device-Port-Monitor-AppImage=true",
            f"X-AppImage-Path={APPIMAGE_PATH}",
            "",
        ]
    )
    write_text_if_changed(launcher_path, contents)

    startup_path = autostart_path()
    try:
        with open(startup_path, "r", encoding="utf-8") as desktop_file:
            startup_contents = desktop_file.read()
    except FileNotFoundError:
        return
    if "X-Device-Port-Monitor-AppImage=true" not in startup_contents:
        return
    startup_lines = []
    for line in startup_contents.splitlines():
        if line.startswith(("Name[ko]=", "Comment[ko]=", "Keywords[ko]=")):
            continue
        if line.startswith("Exec="):
            line = f"Exec={quote_desktop_exec(APPIMAGE_PATH)} --monitor"
        elif line.startswith("Icon="):
            line = "Icon=device-port-monitor"
        elif line.startswith("X-AppImage-Path="):
            line = f"X-AppImage-Path={APPIMAGE_PATH}"
        startup_lines.append(line)
    write_text_if_changed(startup_path, "\n".join(startup_lines) + "\n")


def write_appimage_autostart(enabled):
    path = autostart_path()
    if not enabled:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return

    install_appimage_integration()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    contents = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            "Name=Device Port Monitor",
            f"Exec={quote_desktop_exec(APPIMAGE_PATH)} --monitor",
            "Icon=device-port-monitor",
            "Terminal=false",
            "StartupNotify=false",
            "X-GNOME-Autostart-enabled=true",
            "X-Device-Port-Monitor-AppImage=true",
            f"X-AppImage-Path={APPIMAGE_PATH}",
            "",
        ]
    )
    write_text_if_changed(path, contents)


def monitor_is_running():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    lock_path = os.path.join(runtime_dir, "device-port-monitor.lock")
    lock_file = open(lock_path, "a", encoding="utf-8")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return True
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()
    return False


def autostart_is_enabled():
    if APPIMAGE_PATH:
        return appimage_autostart_is_enabled()
    return run_systemctl("is-enabled", "--quiet", SERVICE_NAME).returncode == 0


def set_autostart(enabled):
    if APPIMAGE_PATH:
        try:
            write_appimage_autostart(enabled)
            if enabled and not monitor_is_running():
                subprocess.Popen(
                    [APPIMAGE_PATH, "--monitor"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except OSError as error:
            return False, str(error)
        return True, ""

    if enabled:
        result = run_systemctl("enable", "--now", SERVICE_NAME)
    else:
        result = run_systemctl("disable", SERVICE_NAME)
    detail = (result.stderr or result.stdout).strip()
    return result.returncode == 0, detail


def application_icon_path():
    candidates = [
        persistent_icon_path(),
        os.path.join(APPDIR_PATH, "device-port-monitor.png"),
        "/usr/share/pixmaps/device-port-monitor.png",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return ""


class DevDirectoryWatcher:
    """Debounced GIO watcher shared by the indicator and settings window."""

    def __init__(self, callback):
        self.callback = callback
        self.refresh_source = 0
        dev_dir = Gio.File.new_for_path("/dev")
        self.file_monitor = dev_dir.monitor_directory(
            Gio.FileMonitorFlags.NONE, None
        )
        self.file_monitor.connect("changed", self._on_changed)

    def _on_changed(self, _monitor, file_obj, _other_file, _event_type):
        name = file_obj.get_basename() if file_obj else ""
        if not name or not is_watched_name(name):
            return

        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
        self.refresh_source = GLib.timeout_add(DEBOUNCE_MS, self._refresh)

    def _refresh(self):
        self.refresh_source = 0
        self.callback()
        return GLib.SOURCE_REMOVE

    def close(self):
        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
            self.refresh_source = 0
        self.file_monitor.cancel()


class SettingsWindow(Gtk.Window):
    """Small user-facing preferences window."""

    def __init__(self):
        super().__init__(title="Device Port Monitor")
        self.set_default_size(700, -1)
        self.set_resizable(True)
        self.set_border_width(20)
        icon_path = application_icon_path()
        if icon_path:
            self.set_icon_from_file(icon_path)
        else:
            self.set_icon_name("drive-removable-media-symbolic")
        self._syncing_switch = False
        self.device_descriptions = {}

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.add(content)

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Device Port Monitor</span>")
        title.set_xalign(0)
        content.pack_start(title, False, False, 0)

        description = Gtk.Label(
            label="Monitor ttyACM, ttyUSB, and video devices from the top bar."
        )
        description.set_xalign(0)
        description.set_line_wrap(True)
        content.pack_start(description, False, False, 0)

        startup_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        startup_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        startup_title = Gtk.Label(label="Start automatically at login")
        startup_title.set_xalign(0)
        startup_title.set_markup("<b>Start automatically at login</b>")
        startup_detail = Gtk.Label(
            label="Saved for this user. Enabling it starts the monitor now."
        )
        startup_detail.set_xalign(0)
        startup_detail.get_style_context().add_class("dim-label")
        startup_text.pack_start(startup_title, False, False, 0)
        startup_text.pack_start(startup_detail, False, False, 0)
        startup_box.pack_start(startup_text, True, True, 0)

        self.startup_switch = Gtk.Switch()
        self.startup_switch.set_valign(Gtk.Align.CENTER)
        startup_box.pack_end(self.startup_switch, False, False, 0)
        content.pack_start(startup_box, False, False, 0)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        content.pack_start(separator, False, False, 0)

        device_scroller = Gtk.ScrolledWindow()
        device_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        device_scroller.set_shadow_type(Gtk.ShadowType.NONE)
        device_scroller.set_propagate_natural_height(True)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() if display is not None else None
        if monitor is None and display is not None and display.get_n_monitors() > 0:
            monitor = display.get_monitor(0)
        screen_height = monitor.get_workarea().height if monitor is not None else 900
        device_scroller.set_max_content_height(max(280, int(screen_height * 0.52)))

        device_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.device_sections = {}
        for section_name in ("ACM", "USB", "VIDEO"):
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.IN)

            section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            section.set_margin_start(12)
            section.set_margin_end(12)
            section.set_margin_top(9)
            section.set_margin_bottom(10)

            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            section_title = Gtk.Label()
            section_title.set_markup(f"<b>{section_name}</b>")
            section_title.set_xalign(0)
            header.pack_start(section_title, True, True, 0)

            count_label = Gtk.Label(label="0")
            count_label.set_xalign(1)
            count_label.get_style_context().add_class("dim-label")
            header.pack_end(count_label, False, False, 0)
            section.pack_start(header, False, False, 0)
            section.pack_start(
                Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                False,
                False,
                0,
            )

            grid = Gtk.Grid(column_spacing=22, row_spacing=5)
            grid.set_column_homogeneous(False)
            section.pack_start(grid, False, False, 0)
            frame.add(section)
            device_list.pack_start(frame, False, False, 0)
            self.device_sections[section_name] = (count_label, grid)

        device_scroller.add(device_list)
        content.pack_start(device_scroller, True, True, 0)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        copyright_label = Gtk.Label()
        copyright_label.set_markup(
            "<small>Copyright (c) 2026 cds730@konkuk.ac.kr</small>"
        )
        copyright_label.set_xalign(0)
        copyright_label.set_valign(Gtk.Align.CENTER)
        copyright_label.get_style_context().add_class("dim-label")
        footer.pack_start(copyright_label, True, True, 0)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda _button: self.close())
        footer.pack_end(close_button, False, False, 0)
        content.pack_end(footer, False, False, 0)

        if not APPIMAGE_PATH:
            run_systemctl("daemon-reload")
        self._sync_service_state()
        self._sync_device_state()
        self.startup_switch.connect("notify::active", self._on_startup_changed)
        self.watcher = DevDirectoryWatcher(self._sync_device_state)
        self.connect("focus-in-event", self._on_focus)
        self.connect("destroy", self._on_destroy)

    def _sync_service_state(self):
        enabled = autostart_is_enabled()

        self._syncing_switch = True
        self.startup_switch.set_active(enabled)
        self._syncing_switch = False

    def _sync_device_state(self):
        devices = scan_devices()
        active_devices = set(devices)
        self.device_descriptions = {
            path: description
            for path, description in self.device_descriptions.items()
            if path in active_devices
        }
        acm, usb, video = categorize_devices(devices)
        for section_name, section_devices in (
            ("ACM", acm),
            ("USB", usb),
            ("VIDEO", video),
        ):
            self._update_device_section(section_name, section_devices)

    def _update_device_section(self, section_name, devices):
        count_label, grid = self.device_sections[section_name]
        count_label.set_text(str(len(devices)))
        for child in grid.get_children():
            grid.remove(child)

        device_header = Gtk.Label()
        device_header.set_markup("<small><b>Device</b></small>")
        device_header.set_xalign(0)
        device_header.get_style_context().add_class("dim-label")
        grid.attach(device_header, 0, 0, 1, 1)

        description_header = Gtk.Label()
        description_header.set_markup("<small><b>Description</b></small>")
        description_header.set_xalign(0)
        description_header.get_style_context().add_class("dim-label")
        grid.attach(description_header, 1, 0, 1, 1)

        if not devices:
            empty_label = Gtk.Label(label="No devices")
            empty_label.set_xalign(0)
            empty_label.get_style_context().add_class("dim-label")
            grid.attach(empty_label, 0, 1, 2, 1)
        else:
            for row, path in enumerate(devices, start=1):
                path_label = Gtk.Label(label=path)
                path_label.set_xalign(0)
                path_label.set_selectable(True)
                grid.attach(path_label, 0, row, 1, 1)

                description = self.device_descriptions.get(path)
                if description is None:
                    description = device_description(path)
                    self.device_descriptions[path] = description
                description_label = Gtk.Label(label=description)
                description_label.set_xalign(0)
                description_label.set_line_wrap(True)
                description_label.set_max_width_chars(48)
                description_label.set_hexpand(True)
                grid.attach(description_label, 1, row, 1, 1)

        grid.show_all()

    def _on_startup_changed(self, switch, _parameter):
        if self._syncing_switch:
            return

        success, detail = set_autostart(switch.get_active())
        if not success:
            self._show_error(detail or "Unable to update the autostart setting.")
        self._sync_service_state()

    def _on_focus(self, _window, _event):
        self._sync_service_state()
        return False

    def _show_error(self, detail):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Could not save the autostart setting.",
        )
        dialog.format_secondary_text(detail)
        dialog.run()
        dialog.destroy()

    def _on_destroy(self, _window):
        self.watcher.close()


def run_settings():
    if APPIMAGE_PATH:
        install_appimage_integration()
    window = SettingsWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
    return 0


def main():
    if "--print-status" in sys.argv:
        print("\n".join(scan_devices()))
        return 0
    if "--monitor" in sys.argv:
        return run_native_monitor()
    return run_settings()


if __name__ == "__main__":
    raise SystemExit(main())
