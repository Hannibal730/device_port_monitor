<img src="https://github.com/user-attachments/assets/07993c55-2ca7-49ab-90b6-4a213da03644" width="400" alt="toolbar_widget" />

<img src="https://github.com/user-attachments/assets/40c9ef43-649b-45f8-9bd7-e6872158f989" width="400" alt="ui" />


# Device Port Monitor

Ubuntu GNOME 상단바에서 `/dev/ttyACM*`, `/dev/ttyUSB*`, `/dev/video*` 장치를
실시간으로 확인하는 가벼운 데스크톱 앱이다.

## 주요 기능

- 상단바에 `ACM n · USB n · VID n` 표시
- 상단바 아이콘을 클릭하면 현재 장치 경로 표시
- 장치 연결·분리 시 데스크톱 알림 표시
- 로그인 시 자동 실행 설정
- 이벤트 기반 C/GLib 모니터 사용(반복 폴링 없음)
- 설정창을 열 때만 Python/GTK UI 실행

## 지원 환경

- Ubuntu 22.04 이상
- GNOME Shell 및 AppIndicator 확장
- x86_64 또는 ARM64 시스템

일반적인 Intel 또는 AMD 노트북은 `amd64` DEB 또는 `x86_64` AppImage를 사용한다.
ARM64 컴퓨터는 `arm64` DEB 또는 `aarch64` AppImage를 사용한다.

## 설치 방법

### 방법 1: DEB 설치(권장)

다운로드한 DEB 파일이 있는 폴더에서 다음 명령을 실행한다.

```bash
sudo apt install ./device-port-monitor_1.2.0_amd64.deb
```

설치가 끝나면 앱 메뉴에서 **Device Port Monitor**를 실행한다.

### 방법 2: AppImage 사용

AppImage를 먼저 계속 보관할 폴더로 옮긴다. 그 폴더에서 다음 명령을 실행한다.

```bash
chmod +x Device_Port_Monitor-1.2.0-x86_64.AppImage
./Device_Port_Monitor-1.2.0-x86_64.AppImage
```

AppImage는 별도 설치 없이 설정창을 연다. 자동 실행을 켠 뒤에는 AppImage 파일을
이동하거나 이름을 변경하지 않아야 한다. 파일을 옮겨야 한다면 먼저 자동 실행을
끄고, 파일을 옮긴 다음 다시 실행하여 자동 실행을 켠다.

## 사용 방법

설정창에서 **Start automatically at login**을 켜면 다음 로그인부터 모니터가
자동으로 실행된다.

상단바 표시는 다음 장치 수를 의미한다.

- `ACM`: `/dev/ttyACM*`
- `USB`: `/dev/ttyUSB*`
- `VID`: `/dev/video*`

상단바 아이콘을 클릭하면 전체 장치 경로와 다음 메뉴가 표시된다.

- **Settings**: 설정창 열기
- **Quit**: 현재 모니터 종료

**Quit**으로 종료해도 자동 실행 설정은 유지되므로 다음 로그인 시 다시 실행된다.

## 제거 방법

DEB 설치판은 다음 명령으로 제거한다.

```bash
sudo apt remove device-port-monitor
```

AppImage는 설정창에서 자동 실행을 끄고 **Quit**을 선택한 다음 AppImage 파일을
삭제한다. 앱 메뉴와 아이콘까지 완전히 제거하려면 다음 명령을 실행한다.

```bash
rm -f ~/.config/autostart/device-port-monitor-appimage.desktop
rm -f ~/.local/share/applications/device-port-monitor.desktop
rm -f ~/.local/share/icons/hicolor/256x256/apps/device-port-monitor.png
```

---

# Device Port Monitor (English)

A lightweight desktop application for monitoring `/dev/ttyACM*`,
`/dev/ttyUSB*`, and `/dev/video*` devices in real time from the Ubuntu GNOME
top bar.

## Main Features

- Displays `ACM n · USB n · VID n` in the top bar
- Shows current device paths when the top-bar icon is clicked
- Shows desktop notifications when devices are connected or disconnected
- Provides a login autostart preference
- Uses an event-driven C/GLib monitor with no polling
- Runs the Python/GTK UI only while the settings window is open

## Supported Environments

- Ubuntu 22.04 or later
- GNOME Shell with the AppIndicator extension
- x86_64 or ARM64 systems

Most Intel and AMD laptops should use the `amd64` DEB or `x86_64` AppImage.
ARM64 computers should use the `arm64` DEB or `aarch64` AppImage.

## Installation

### Option 1: Install the DEB (recommended)

Run the following command from the folder containing the downloaded DEB file:

```bash
sudo apt install ./device-port-monitor_1.2.0_amd64.deb
```

After installation, launch **Device Port Monitor** from the application menu.

### Option 2: Use the AppImage

First move the AppImage to the folder where you intend to keep it. Run the
following commands from that folder:

```bash
chmod +x Device_Port_Monitor-1.2.0-x86_64.AppImage
./Device_Port_Monitor-1.2.0-x86_64.AppImage
```

The AppImage opens the settings window without installation. Do not move or
rename the AppImage after enabling autostart. To move it, disable autostart
first, move the file, run it again, and then re-enable autostart.

## Usage

Enable **Start automatically at login** in the settings window to start the
monitor automatically at the next login.

The top-bar counters represent the following devices:

- `ACM`: `/dev/ttyACM*`
- `USB`: `/dev/ttyUSB*`
- `VID`: `/dev/video*`

Click the top-bar icon to see all device paths and the following actions:

- **Settings**: Open the settings window
- **Quit**: Stop the current monitor

Using **Quit** does not change the autostart preference, so the monitor starts
again at the next login when autostart is enabled.

## Removal

Remove the DEB installation with:

```bash
sudo apt remove device-port-monitor
```

For the AppImage, disable autostart in the settings window, select **Quit**,
and then delete the AppImage file. To remove the application-menu entry and
icon as well, run:

```bash
rm -f ~/.config/autostart/device-port-monitor-appimage.desktop
rm -f ~/.local/share/applications/device-port-monitor.desktop
rm -f ~/.local/share/icons/hicolor/256x256/apps/device-port-monitor.png
```
