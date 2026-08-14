# Device Port Monitor

Ubuntu GNOME 상단바에서 `/dev/ttyACM*`, `/dev/ttyUSB*`, `/dev/video*` 장치를
실시간으로 확인하는 독립형 데스크톱 앱이다.

## 기능

- 상단바에 `ACM n · USB n · VID n` 표시
- 상단바 아이콘 클릭 시 현재 장치 경로 표시
- 상단바 메뉴에서 모니터 종료
- 장치 연결·분리 시 데스크톱 알림 표시
- C/GLib 기반 상시 모니터(`/dev` 이벤트 기반, 반복 폴링 없음)
- Python/GTK 설정 UI는 설정창을 열 때만 실행
- 작은 GTK 설정창에서 로그인 자동 실행 저장
- 비정상 종료 시 systemd 사용자 서비스가 자동 재시작

## 지원 환경

- Ubuntu 22.04 이상
- GNOME Shell 및 AppIndicator 확장
- Debian 패키지(`.deb`)를 사용하는 x86_64/ARM64 Ubuntu

상시 모니터가 네이티브 C 실행 파일이므로 DEB와 AppImage는 CPU 아키텍처별로
빌드된다.

## 패키지 빌드

```bash
./build-deb.sh
```

결과 파일은 현재 CPU에 따라 `dist/device-port-monitor_1.2.0_amd64.deb` 또는
`dist/device-port-monitor_1.2.0_arm64.deb`이다.

AppImage 빌드:

```bash
./build-appimage.sh
```

결과 파일은 현재 CPU에 따라
`dist/Device_Port_Monitor-1.2.0-x86_64.AppImage` 또는
`dist/Device_Port_Monitor-1.2.0-aarch64.AppImage`이다. AppImage를 직접 실행하면
설정창이 열리고, 자동 실행을 켜면 현재 AppImage의 절대 경로가 사용자 자동 시작
설정에 저장된다. 따라서 자동 실행을 켠 뒤에는 AppImage 파일을 이동하지 않아야 한다.

## 설치와 제거

```bash
sudo apt install ./dist/device-port-monitor_1.2.0_amd64.deb
sudo apt remove device-port-monitor
```

설치한 뒤 앱 메뉴에서 **Device Port Monitor**를 실행하고
**Start automatically at login**을
켜면 된다. 설정은 각 Linux 사용자 계정에 따로 저장된다.

# Device Port Monitor (English)

An independent desktop application for monitoring `/dev/ttyACM*`,
`/dev/ttyUSB*`, and `/dev/video*` devices in real time from the Ubuntu GNOME
top bar.

## Features

- Displays `ACM n · USB n · VID n` in the top bar
- Shows current device paths when the top-bar icon is clicked
- Provides a Quit action in the top-bar menu
- Shows desktop notifications when devices are connected or disconnected
- Uses a lightweight C/GLib resident monitor based on `/dev` events, with no polling
- Runs the Python/GTK settings UI only while the settings window is open
- Saves the login autostart preference from a small GTK settings window
- Restarts automatically through the systemd user service after an unexpected exit

## Supported Environments

- Ubuntu 22.04 or later
- GNOME Shell with the AppIndicator extension
- x86_64/ARM64 Ubuntu distributions that support Debian packages (`.deb`)

Because the resident monitor is a native C executable, DEB and AppImage
packages are built separately for each CPU architecture.

## Building Packages

```bash
./build-deb.sh
```

Depending on the current CPU architecture, the output is
`dist/device-port-monitor_1.2.0_amd64.deb` or
`dist/device-port-monitor_1.2.0_arm64.deb`.

To build the AppImage:

```bash
./build-appimage.sh
```

Depending on the current CPU architecture, the output is
`dist/Device_Port_Monitor-1.2.0-x86_64.AppImage` or
`dist/Device_Port_Monitor-1.2.0-aarch64.AppImage`. Running the AppImage opens
the settings window. Enabling autostart saves the absolute path of the current
AppImage in the user's autostart configuration. Do not move the AppImage after
enabling autostart.

## Installation and Removal

```bash
sudo apt install ./dist/device-port-monitor_1.2.0_amd64.deb
sudo apt remove device-port-monitor
```

After installation, launch **Device Port Monitor** from the application menu
and enable **Start automatically at login**. Preferences are stored separately
for each Linux user account.
