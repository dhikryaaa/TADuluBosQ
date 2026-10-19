# TADuluBosQ

TADuluBosQ adalah aplikasi Windows yang berjalan di system tray dan memantau proses yang ditentukan di `config.json`. Jika proses target dijalankan pada hari yang tidak dikecualikan, aplikasi akan:

1. Menjeda proses target sementara.
2. Menampilkan popup pengingat.
3. Menunggu countdown selesai sebelum tombol **Play Anyway** dapat digunakan.

## Cara kerja tombol

- **Cancel**: menghentikan proses target beserta child process-nya.
- **Play Anyway**: melanjutkan proses target.
- Tombol **X** pada popup diperlakukan seperti **Cancel**, sehingga proses tidak dibiarkan dalam keadaan paused.
- Aplikasi hanya memproses satu instance TADuluBosQ.
- Proses target yang sudah berjalan sebelum TADuluBosQ dimulai tidak langsung dijeda pada pemeriksaan pertama.

> Gunakan aplikasi ini hanya pada komputer dan proses yang Anda kendalikan. Menghentikan proses secara paksa dapat menyebabkan pekerjaan yang belum disimpan hilang.

## Persyaratan

- Windows
- Python Windows resmi 3.11 atau versi kompatibel
- `pip`

Hindari membuat virtual environment menggunakan Python MSYS2/MinGW. Python tersebut biasanya memakai folder `bin` dan dapat menyebabkan `psutil` atau `Pillow` dikompilasi dari source.

## Menjalankan dari source

Buka PowerShell di folder project:

```powershell
cd C:\Users\andhi\Documents\TADuluBosQ
```

Buat dan aktifkan virtual environment menggunakan Python Windows resmi:

```powershell
& "C:\Path\Ke\Python\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Jika PowerShell memblokir script aktivasi:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Install dependency:

```powershell
python -m pip install --upgrade pip
python -m pip install psutil pystray pillow pyinstaller
```

Jalankan aplikasi:

```powershell
python main.py
```

Untuk menghentikan aplikasi, klik kanan ikon TADuluBosQ di system tray lalu pilih **Exit**.

## Mengubah konfigurasi game

File `config.json` harus berada di folder yang sama dengan `main.py` saat dijalankan dari source, atau di folder yang sama dengan `.exe` saat dijalankan sebagai aplikasi hasil build.

Contoh konfigurasi:

```json
{
  "poll_interval": 0.5,
  "skip_weekdays": [4, 5, 6],
  "targets": {
    "RiotClientServices.exe": {
      "title": "Is your Thesis finished yet?",
      "message": "It's not weekend yet blud, don't play VALORANT, GO FINISH YOUR THESIS!",
      "countdown": 5
    }
  }
}
```

### Opsi konfigurasi

#### `poll_interval`

Interval pemeriksaan proses dalam detik:

```json
"poll_interval": 0.5
```

Nilai yang lebih kecil mendeteksi proses lebih cepat, tetapi melakukan pemeriksaan lebih sering. Nilai `0.5` cocok untuk penggunaan umum.

#### `skip_weekdays`

Daftar nomor hari yang tidak memunculkan popup:

| Nomor | Hari |
|---:|---|
| 0 | Senin |
| 1 | Selasa |
| 2 | Rabu |
| 3 | Kamis |
| 4 | Jumat |
| 5 | Sabtu |
| 6 | Minggu |

Konfigurasi default:

```json
"skip_weekdays": [4, 5, 6]
```

Artinya popup tidak muncul pada Jumat, Sabtu, dan Minggu. Jika ingin popup muncul setiap hari, gunakan:

```json
"skip_weekdays": []
```

Contoh agar bebas pada Sabtu dan Minggu saja:

```json
"skip_weekdays": [5, 6]
```

#### `targets`

`targets` adalah object dengan nama file executable sebagai key. Nama file harus menyertakan `.exe`, misalnya:

```json
"targets": {
  "game.exe": {
    "title": "Waktunya fokus",
    "message": "Selesaikan tugasmu sebelum bermain.",
    "countdown": 10
  }
}
```

Nama executable tidak membedakan huruf besar dan kecil. Untuk mengetahui nama proses game:

1. Jalankan game.
2. Buka **Task Manager** dengan `Ctrl+Shift+Esc`.
3. Cari proses game pada tab **Details**.
4. Salin nama pada kolom **Name**, misalnya `game.exe`.

Beberapa game memiliki launcher dan proses game yang berbeda. Jika ingin memantau keduanya, tambahkan keduanya sebagai target:

```json
"targets": {
  "GameLauncher.exe": {
    "title": "Launcher terdeteksi",
    "message": "Tutup launcher atau lanjutkan dengan pilihan di bawah.",
    "countdown": 5
  },
  "Game.exe": {
    "title": "Game terdeteksi",
    "message": "Selesaikan pekerjaanmu terlebih dahulu.",
    "countdown": 5
  }
}
```

Setiap perubahan `config.json` memerlukan restart aplikasi agar konfigurasi baru dibaca.

## Build menjadi `.exe`

Build dari PowerShell di folder project:

```powershell
.\.venv\Scripts\Activate.ps1
pyinstaller --onefile --noconsole --name TADuluBosQ main.py
```

File hasil build berada di:

```text
dist\TADuluBosQ.exe
```

## Menempatkan aplikasi di folder tetap

Simpan `.exe` dan `config.json` pada folder yang tidak akan dipindahkan. Contoh:

```powershell
New-Item -ItemType Directory -Force C:\Tools\TADuluBosQ
Copy-Item dist\TADuluBosQ.exe C:\Tools\TADuluBosQ\
Copy-Item config.json C:\Tools\TADuluBosQ\
```

`config.json` wajib berada di samping `.exe`, karena aplikasi mencari konfigurasi dari folder executable saat dijalankan sebagai `.exe`.

Struktur folder yang benar:

```text
C:\Tools\TADuluBosQ\
├── TADuluBosQ.exe
└── config.json
```

## Setup autostart Windows

Cara paling mudah adalah menggunakan folder Startup:

1. Tekan `Win+R`.
2. Ketik `shell:startup`, lalu tekan `Enter`.
3. Klik kanan area kosong folder Startup.
4. Pilih **New > Shortcut**.
5. Masukkan lokasi:

   ```text
   C:\Tools\TADuluBosQ\TADuluBosQ.exe
   ```

6. Beri nama shortcut, misalnya `TADuluBosQ`.
7. Restart Windows atau jalankan shortcut tersebut untuk menguji.

Karena aplikasi memakai `--noconsole`, aplikasi akan berjalan di system tray tanpa membuka jendela console.

### Menonaktifkan autostart

Hapus shortcut `TADuluBosQ` dari folder Startup:

1. Tekan `Win+R`.
2. Ketik `shell:startup`, lalu tekan `Enter`.
3. Hapus shortcut TADuluBosQ.

Menghapus shortcut tidak menghapus `.exe` maupun `config.json`.

## Troubleshooting

### `Scripts\Activate.ps1` tidak ditemukan

Environment kemungkinan dibuat menggunakan Python MSYS2/MinGW. Environment Windows normal memiliki folder `Scripts`, bukan `bin`. Buat ulang environment menggunakan Python Windows resmi:

```powershell
Remove-Item -Recurse -Force .venv
& "C:\Path\Ke\Python\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### `Python.h` atau `zlib` tidak ditemukan saat install

Pip sedang mencoba compile package dari source, biasanya karena interpreter yang digunakan adalah Python MSYS2/MinGW. Pastikan perintah berikut menunjuk ke Python Windows:

```powershell
python -c "import sys, sysconfig; print(sys.executable); print(sysconfig.get_platform())"
```

Hasil yang diharapkan:

```text
...\Scripts\python.exe
win_amd64
```

### Popup tidak muncul

Periksa hal berikut:

- Nama executable di `targets` sama dengan nama proses di Task Manager.
- Hari ini tidak tercantum di `skip_weekdays`.
- Game dijalankan setelah TADuluBosQ aktif. Proses yang sudah berjalan saat aplikasi pertama kali dimulai dilewati pada pemeriksaan awal.
- `config.json` berada di folder yang sama dengan `main.py` atau `.exe`.
- Format JSON valid dan menggunakan tanda koma serta kutip ganda yang benar.

