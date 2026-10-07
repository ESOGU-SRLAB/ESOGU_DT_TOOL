# 🐳 ROS2 Docker Container - Windows Kullanım Rehberi

> **Deprecated optional local executor:** This directory documents the legacy
> local ROS 2 execution routes. It is not used by the STLC backend Dockerfile,
> Compose stack, headless generation API, or remote `ExecutionAdapter`.

Bu rehber, colcon_ws workspace'inizi Docker container'da Windows'ta çalıştırmanız için hazırlanmıştır.

## 📋 Gereksinimler

### 1. Docker Desktop (Windows)
- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) indir ve kur
- WSL2 backend'i aktif olmalı
- Settings → General → "Use the WSL2 based engine" ✅

### 2. VcXsrv (X Server - GUI için)
- [VcXsrv Windows X Server](https://sourceforge.net/projects/vcxsrv/) indir ve kur
- Bu, Gazebo ve RViz gibi GUI uygulamalarını Windows'ta göstermenizi sağlar

---

## 🚀 Kurulum Adımları

### Adım 1: VcXsrv'i Başlat

1. **XLaunch** programını çalıştır
2. Ayarları şöyle yap:
   - ✅ **Multiple windows** seç
   - ✅ Display number: **0** 
   - ✅ **Start no client** seç
   - ✅ **Disable access control** seç (ÖNEMLİ!)
   - ✅ **"Native opengl"** işaretli olsun
3. Finish'e tıkla

> 💡 **Not:** VcXsrv'i her Windows açılışında başlatmanız gerekecek (veya Startup'a ekleyin)

### Adım 2: Docker Image'i Build Et

PowerShell veya CMD'de `colcon_ws` dizinine git:

```powershell
cd C:\path\to\colcon_ws
```

Docker image'i build et:

```bash
docker build -t ros2_colcon_workspace:humble -f docker/Dockerfile .
```

⏱ Bu işlem **10-20 dakika** sürebilir (ilk seferinde).

### Adım 3: Container'ı Çalıştır

#### Otomatik Yöntem (PowerShell Script):

```powershell
cd docker
.\run_docker_windows.ps1
```

#### Manuel Yöntem:

PowerShell'de:

```powershell
# WSL IP adresini al
$WSL_HOST = (wsl hostname -I).Trim()
$env:DISPLAY = "${WSL_HOST}:0.0"

# Container'ı çalıştır
docker run -it --rm `
    --name ros2_moveit_container `
    --privileged `
    --net=host `
    -e DISPLAY=$env:DISPLAY `
    -e QT_X11_NO_MITSHM=1 `
    -e LIBGL_ALWAYS_SOFTWARE=1 `
    -e ROS_DOMAIN_ID=42 `
    -v ${PWD}/../src:/root/colcon_ws/src:rw `
    ros2_colcon_workspace:humble `
    bash
```

---

## 🎮 Container İçinde Kullanım

Container başladığında, ROS2 ortamı otomatik olarak hazır olacak:

### Test: GUI Çalışıyor mu?

```bash
# X11 test
xeyes
```

Eğer bir göz simgesi görüyorsanız, GUI çalışıyor! ✅

### Gazebo'yu Başlat

```bash
ros2 launch gazebo_ros gazebo.launch.py
```

### RViz'i Başlat

```bash
rviz2
```

### Workspace'i Yeniden Build Et

```bash
cd /root/colcon_ws
colcon build --symlink-install
source install/setup.bash
```

### Simülasyon Robot'u Başlat

```bash
# Örnek: RS005L Gazebo simülasyonu
ros2 launch rs005l_gazebo rs005l_gazebo.launch.py
```

### MoveIt2 ile Planlama

```bash
# Simülasyon için MoveIt
ros2 launch sim_robot_moveit_config demo.launch.py
```

---

## 📁 Dosya Yapısı

```
colcon_ws/
├── docker/
│   ├── Dockerfile              # Docker image tanımı
│   ├── docker-compose.yml      # Docker Compose konfigürasyonu
│   ├── run_docker_windows.ps1  # Windows başlatma script'i
│   ├── run_docker_linux.sh     # Linux başlatma script'i
│   └── DOCKER_README.md        # Bu dosya
├── src/
│   └── [tüm ROS2 paketleriniz]
```

---

## 🔧 Sorun Giderme

### Problem: GUI Açılmıyor (Gazebo/RViz görünmüyor)

**Çözüm 1:** VcXsrv'in çalıştığından emin ol
```powershell
# Task Manager'da "vcxsrv.exe" kontrolü
```

**Çözüm 2:** Windows Firewall'da VcXsrv'e izin ver
- Windows Defender Firewall → Allow an app
- VcXsrv'i hem **Private** hem **Public** için aktif et

**Çözüm 3:** DISPLAY değişkenini manuel ayarla
```bash
# Container içinde:
export DISPLAY=$(ip route | grep default | awk '{print $3}'):0.0
```

### Problem: "Cannot connect to X server"

VcXsrv'de **"Disable access control"** seçeneğinin aktif olduğundan emin ol.

### Problem: Build hatası

```bash
# Container içinde:
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

### Problem: Container içinde kod değişiklikleri kaybolуyor

Volume mount'u kontrol et:
```bash
# Container içinde:
ls -la /root/colcon_ws/src/
```

Eğer dosyalar boşsa, volume mount yolunu düzelt.

---

## 💡 İpuçları

### Geliştirme Workflow'u

1. **VS Code'da düzenle** (Windows'ta)
2. **Container'da build et:**
   ```bash
   colcon build --packages-select <package_name>
   source install/setup.bash
   ```
3. **Container'da test et:**
   ```bash
   ros2 launch ...
   ```

### Birden Fazla Terminal

Container'a yeni terminal ekle:
```powershell
docker exec -it ros2_moveit_container bash
```

### Container'ı Arka Planda Çalıştır

```powershell
docker run -d `
    --name ros2_bg `
    ... # diğer parametreler
    ros2_colcon_workspace:humble `
    tail -f /dev/null
```

Bağlan:
```powershell
docker exec -it ros2_bg bash
```

---

## 🎯 Hızlı Komutlar

| Komut | Açıklama |
|-------|----------|
| `docker ps` | Çalışan container'ları listele |
| `docker stop ros2_moveit_container` | Container'ı durdur |
| `docker rm ros2_moveit_container` | Container'ı sil |
| `docker images` | Mevcut image'leri listele |
| `docker rmi ros2_colcon_workspace:humble` | Image'i sil |

---

## 🌐 Network Modları

Mevcut config **host mode** kullanıyor (en kolay):
- ✅ Gerçek robot ile direkt iletişim
- ✅ ROS2 topic'leri Windows'tan görülebilir

Alternatif: **bridge mode** (daha izole):
```yaml
# docker-compose.yml içinde
ports:
  - "11311:11311"  # ROS Master
  - "8080:8080"    # Custom port
```

---

## 📞 Ek Kaynaklar

- [ROS2 Docker Tutorial](https://docs.ros.org/en/humble/How-To-Guides/Run-2-nodes-in-single-or-separate-docker-containers.html)
- [VcXsrv Setup Guide](https://github.com/microsoft/WSL/issues/4106)
- [Docker Desktop Documentation](https://docs.docker.com/desktop/windows/)

---

## ✅ Kontrol Listesi

Setup'ınız doğru çalışıyorsa:

- [ ] VcXsrv çalışıyor (sistem tray'de gösterge var)
- [ ] Docker Desktop çalışıyor
- [ ] Container başlatıldı (`docker ps` ile görünüyor)
- [ ] `xeyes` komutu pencere açıyor
- [ ] `rviz2` açılıyor
- [ ] `gazebo` açılıyor
- [ ] `/root/colcon_ws/src` içinde dosyalarınız görünüyor

---

**🎉 Hazırsınız! Container'da geliştirmeye başlayabilirsiniz.**
