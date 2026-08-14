# Device Port Monitor

Ubuntu GNOME 상단바에서 `/dev/ttyACM*`, `/dev/ttyUSB*`, `/dev/video*` 장치를
실시간으로 확인하는 독립형 데스크톱 앱이다.

## 기능

- 상단바에 `SER n · CAM n` 표시
- 상단바 아이콘 클릭 시 현재 장치 경로 표시
- 상단바 메뉴에서 모니터 종료
- 장치 연결·분리 시 데스크톱 알림 표시
- `/dev` 이벤트 기반 감시(반복 폴링 없음)
- 작은 GTK 설정창에서 로그인 자동 실행 저장
- 비정상 종료 시 systemd 사용자 서비스가 자동 재시작

## 지원 환경

- Ubuntu 22.04 이상
- GNOME Shell 및 AppIndicator 확장
- Debian 패키지(`.deb`)를 사용하는 x86_64/ARM64 Ubuntu

패키지는 Python 소스 기반 `Architecture: all`이므로 CPU 종류에 독립적이다.

## 패키지 빌드

```bash
./build-deb.sh
```

결과 파일은 `dist/device-port-monitor_1.1.0_all.deb`이다.

AppImage 빌드:

```bash
./build-appimage.sh
```

결과 파일은 현재 CPU에 따라
`dist/Device_Port_Monitor-1.1.0-x86_64.AppImage` 또는
`dist/Device_Port_Monitor-1.1.0-aarch64.AppImage`이다. AppImage를 직접 실행하면
설정창이 열리고, 자동 실행을 켜면 현재 AppImage의 절대 경로가 사용자 자동 시작
설정에 저장된다. 따라서 자동 실행을 켠 뒤에는 AppImage 파일을 이동하지 않아야 한다.

## 설치와 제거

```bash
sudo apt install ./dist/device-port-monitor_1.1.0_all.deb
sudo apt remove device-port-monitor
```

설치한 뒤 앱 메뉴에서 **장치 포트 모니터**를 실행하고 **로그인 시 자동 실행**을
켜면 된다. 설정은 각 Linux 사용자 계정에 따로 저장된다.

## 명령줄

```bash
# 설정창 열기
device-port-monitor --settings

# 현재 대상 장치 출력
device-port-monitor --print-status

# 모니터 서비스 상태와 로그
systemctl --user status device-port-monitor
journalctl --user -u device-port-monitor -f
```
