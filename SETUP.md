# LucAetheryn — Stellar Universe Profile

## 1. Upload ke GitHub
1. Buka repository profil `LucAetheryn/LucAetheryn`.
2. Extract ZIP ini di perangkat.
3. Upload seluruh isi folder `LucAetheryn_Stellar_Universe` ke root repository. Pastikan `README.md`, `assets/`, dan `.github/` berada langsung di root.
4. Commit perubahan.

## 2. Aktifkan workflow
Buka tab **Actions** pada repository. Jika GitHub meminta izin, pilih untuk mengizinkan Actions.
- Jalankan **Generate contribution snake** dengan tombol Run workflow.
- Jalankan **Generate profile summary cards** dengan tombol Run workflow.
- Workflow berikutnya berjalan terjadwal setiap hari.

Jika push ke branch `output` ditolak, buka Settings → Actions → General → Workflow permissions, lalu pilih **Read and write permissions** dan simpan.

## 3. Guestbook
Guestbook memakai Issue Form dan GitHub Actions. Pastikan Issues aktif pada repository. Pesan yang masuk harus memiliki judul `[Guestbook]` dan maksimal 240 karakter. Workflow hanya memproses issue yang cocok. Untuk menghindari spam, moderasi issue/label `guestbook` secara berkala.

## 4. Penting sebelum dipublikasikan
- Repository harus bernama persis `LucAetheryn` agar menjadi profile README.
- Pastikan username GitHub memang `LucAetheryn`.
- Statistik pihak ketiga dapat mengalami rate limit atau downtime. README tetap memiliki aset lokal jika layanan statistik tidak tersedia.
- Kartu proyek saat ini mengarah ke halaman profil GitHub, bukan ke repository proyek yang belum diberikan. Ganti `href` tiap kartu setelah URL repository atau website proyek tersedia.
- Tambahkan tautan LinkedIn, email, website, atau sosial lain hanya setelah URL yang benar sudah siap.
- Semua ilustrasi utama dalam `assets/` dibuat khusus untuk identitas Stellar Universe; jangan mengganti nama/path aset tanpa memperbarui README.
- GitHub README tidak menjalankan JavaScript. Animasi menggunakan SVG SMIL/CSS dan dapat berbeda dukungannya antar-renderer. Jika animasi tidak bergerak pada preview tertentu, buka profil setelah commit untuk memeriksa hasil GitHub.

## Struktur
- `assets/`: seluruh ilustrasi SVG custom.
- `assets/mobile/`: header dan section artwork khusus layar kecil.
- `assets/projects/`: tujuh kartu proyek.
- `.github/workflows/`: snake, profile summary cards, dan guestbook.
- `.github/ISSUE_TEMPLATE/`: formulir guestbook.
- `.github/scripts/`: pemroses guestbook.

## Kustomisasi cepat
Edit `README.md` untuk bio dan daftar stack. Edit file SVG terkait untuk mengubah visual. Gunakan warna brand:
- Cosmic Blue: `#06B6FF`
- Stellar Purple: `#7C3AED`
- Nebula Pink: `#EC4899`
- Space Dark: `#0F172A`
