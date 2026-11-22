# Sistem Auto Poster — Liputan KabarKota (Full Otomatis via GitHub)

Paket ini menjalankan generator poster berita **secara otomatis penuh di GitHub** tanpa server/VPS berbayar:

1. **Otomatis Penuh (GitHub Actions):** Setiap **15 menit**, GitHub mengecek artikel terbaru di `liputankabarkota.com`, mengambil judul dan foto utamanya, memasangnya ke bingkai transparan `template.png`, lalu menyimpan hasilnya di folder `posters/` dan (opsional) **mengirim langsung ke Telegram Anda**.
2. **Galeri & Tombol 1-Klik di Blogger (GitHub Pages):** Semua poster yang sudah jadi otomatis tampil di halaman web GitHub Pages Anda agar tinggal 1 klik unduh dari HP, dan Anda juga bisa memasang tombol langsung di artikel Blogger.

---

## Cara Pasang (5 Menit)

### Langkah 1 — Upload ke GitHub
1. Buat repositori baru di GitHub (contoh: `auto-poster-kabarkota`, pilih **Public** agar GitHub Actions & GitHub Pages gratis penuh).
2. Ekstrak file ZIP ini di komputer/HP Anda, lalu upload **seluruh isinya** (termasuk folder `.github/workflows/auto-poster.yml`, `generate_posters.py`, `template.png`, `index.html`, dan `processed.json`) ke repositori tersebut.

### Langkah 2 — Aktifkan Izin & Jalankan Otomatis
1. Di repositori GitHub, buka **Settings → Actions → General**.
2. Pada bagian **Workflow permissions**, pilih **Read and write permissions**, lalu klik **Save**.
3. Buka tab **Actions** → klik **Auto Generate Poster Liputan KabarKota** → klik **Run workflow** untuk percobaan pertama.
   * Anda juga bisa mengisi kolom `article_url` saat klik **Run workflow** jika ingin langsung memproses satu link berita tertentu.
4. Setelah selesai, semua poster jadi akan otomatis muncul di folder `posters/`.

### Langkah 3 — Aktifkan GitHub Pages (Galeri HP & Generator Manual)
1. Buka **Settings → Pages**.
2. Pada **Branch**, pilih `main` dan folder `/ (root)`, lalu klik **Save**.
3. Buka alamat GitHub Pages Anda (misal `https://username.github.io/auto-poster-kabarkota/`).

### Langkah 4 (Opsional) — Kirim Poster Otomatis ke Telegram
Agar setiap berita baru langsung masuk ke HP Anda sebagai foto siap unggah ke IG/FB/TikTok:
1. Buat bot Telegram lewat `@BotFather` untuk mendapatkan **Bot Token**, dan cek **Chat ID** Anda lewat `@userinfobot` (atau ID grup/channel redaksi).
2. Di GitHub, buka **Settings → Secrets and variables → Actions → New repository secret**, lalu tambahkan dua secret:
   * `TELEGRAM_BOT_TOKEN`
   * `TELEGRAM_CHAT_ID`

### Langkah 5 (Opsional) — Tombol di Template Blogger
Buka **Blogger → Tema → Edit HTML**, tempelkan kode berikut di area postingan (`<b:includable id='post' ...>`), ganti `URL_GITHUB_PAGES_ANDA`:

```xml
<a expr:href='&quot;https://URL_GITHUB_PAGES_ANDA/?judul=&quot; + data:post.title + &quot;&amp;foto=&quot; + data:post.firstImageUrl'
   target='_blank'
   style='display:inline-block;padding:8px 14px;background:#0284c7;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;margin:8px 0;'>
  Buat Poster Berita
</a>
```
