# Tech Stack Audit 3: Real Estate Scraper

| Alan | Değer |
| --- | --- |
| Dosya | `docs/tech-stack-audit-3-2026-11-27.md` |
| Tarih | 2026-11-27 |
| Commit | `b886a0a` (`main`, temiz çalışma ağacı) |
| Mod | Yalnızca denetim (salt-okunur). Bu rapor dışında hiçbir dosya değiştirilmedi. |
| Hedef | Kullanıcı talebi: projedeki teknoloji yığınlarını tespit etme, güncel sürüm / EOL araştırması ve alternatif karşılaştırması (`tech-stack-optimizer` + `run_workflow`). |
| Kapsam | Tüm depo: `Frontend/`, `Backend/`, `Backend/go/`, `docker-compose.yml`, kök lockfile'lar (`requirements*.lock`) ve dokümantasyon (`docs/`). |
| Önceki Denetimler | `docs/tech-stack-audit-1-2026-11-03.md` (`7f8a9d8`), `docs/tech-stack-audit-2-2026-11-23.md` (`fe6bdf8`) |
| Kullanılan Uzmanlıklar | `tech-stack-optimizer`, `dependency-upgrade`, `security-auditor`, `docker-containerization`, `web-performance-optimization`, `ponytail-audit` (salt-okunur analiz adımları). |
| Tarayıcı Veri Tarihleri | `npm audit`: 2026-11-27 (`[measured]`). Web sürüm/EOL araştırması: 2026-11-27 (`[sourced]`). `pip-audit`, `npm outdated`, `go list -m -u all`: sandbox ağ/izin engeli nedeniyle atlandı (`[unverified]`). `bandit`, `osv-scanner`, `govulncheck`: kurulu değil. |

---

## 1. Karar (Decision)

- **Ana mimariyi koru (`keep current`).** `Next.js 16 + React 19` frontend, `FastAPI + SQLAlchemy 2 + PostgreSQL 16` API, `Celery + Redis 7.4` kuyruk, `Scrapling / Playwright / Selenium` worker ve `Go uTLS` proxy mimarisi projenin mevcut gereksinimlerine uygundur. Dil veya çerçeve değişikliği (ör. Celery → Taskiq, PostgreSQL → başka DB, Chart.js → Recharts/ECharts) önerilmez.
- **Kısa vadede uygulanması gereken hızlı kazanımlar (`adopt`):**
  1. **Terk edilmiş `passlib==1.7.4` + `bcrypt==4.0.1` göçü:** Python 3.13+ ile kırılan ve bakımı durmuş `passlib` yerine `pwdlib` (`argon2` + `bcrypt` doğrulama) veya doğrudan `bcrypt` (`5.0.0`) / `argon2-cffi` geçişi (`F3-01`).
  2. **Çoklu runtime ve manifest kaymalarının (drift) kapatılması:** Python (`3.11` worker / `3.13` API / `3.12` linter / `3.14` lokal) → `3.13` hedefinde hizalama; Node (`22-alpine` Docker / `@types/node ^20` / `24.11.1` lokal) → `22` veya `24 LTS` + `engines` hizalaması; Go (`go.mod 1.26.0` / `Dockerfile 1.27` / `-mod=mod`) → `1.27` + `-mod=readonly`; `eslint-config-next` (`16.0.10`) → `16.4.6` + `eslint@^10` (v9 EOL) (`F3-02`, `F3-03`, `F3-04`).
  3. **Frontend paket hijyeni ve düzeltilebilir zafiyetler:** `@types/three` ve `@types/d3-geo`'nun `devDependencies`'e taşınması; fix mevcut `brace-expansion`, `js-yaml`, `zod` zafiyetlerinin güncellenmesi (`F3-05`).
  4. **Konteyner sertleştirme ve Compose hijyeni:** `Backend/Dockerfile` ve `Backend/go/Dockerfile` için non-root `USER`, base imajlara `@sha256:` digest sabitlemesi, kaynak limitleri, dev frontend'e `profiles: ["dev"]` ve `mher/flower:2.0` → `2.2.0` hizalaması (`F3-06`, `F3-07`).
  5. **Worker `Chrome for Testing` (`145.x` → `158.x`) ve `pandas`/`openpyxl` lockfile hizalaması** (`F3-08`).
  6. **CI ve bağımlılık otomasyonu eksikliği:** `.github/workflows/` + `dependabot.yml` / `renovate.json` ve lockfile `--generate-hashes` (`F3-09`).
- **Ölçülü denemeler (`trial`):** `framer-motion` → `motion` paketi geçişi (`F3-10`), `three` + `postprocessing` (`Hyperspeed.tsx`) bundle/GPU izolasyonu (`F3-11`), `vitest` 4 → 5 (`F3-12`), `psycopg2-binary` → `psycopg[binary,pool]` (`3.3.9`) (`F3-13`), worker `seccomp:unconfined` yerine özel Chrome seccomp profili (`F3-14`), Redis → `Valkey` (BSD-3-Clause lisans uyumu gerekiyorsa) (`F3-15`), ve scraping çekirdeği (`scrapling 0.5.1`, `playwright 1.65.2`, `patchright 1.63.0`) yükseltmesi (`F3-16`).
- **Ertelenenler (`defer`):** `pandas 3.1.1` (CoW breaking change), `TypeScript 6.0 / 7.0 Beta`, `zerolog` → `log/slog`, `PostgreSQL 16` → `17/18`, `Celery` → `Taskiq/Dramatiq`.

---

## 2. Önceliklendirilmiş Karar Listesi

| # | ID | Etiket | Aksiyon | Efor | Hedef / Mercek |
| --- | --- | --- | --- | --- | --- |
| 1 | F3-01 | `adopt` | `passlib==1.7.4` + `bcrypt==4.0.1` → `pwdlib` (`argon2`+`bcrypt`) veya `bcrypt 5.0.0` göçü | S–M | Güvenlik, Python 3.13+ uyumu |
| 2 | F3-02 | `adopt` | `eslint-config-next` (`16.0.10` → `16.4.6`) + `eslint` (`^9` EOL → `^10`) ve `@types/*` `devDependencies`'e taşıma | S | Güvenlik, Bakım |
| 3 | F3-03 | `adopt` | Node (`22` veya `24 LTS` + `engines` + `@types/node`) ve Python (`3.13` + `ruff.toml`/`mypy.ini`) runtime hizalaması | S–M | Tutarlılık, EOL |
| 4 | F3-04 | `adopt` | Go (`go.mod` `1.27` + `-mod=readonly`) ve `zerolog` (`v1.32.0` → `v1.35.1`) + `mher/flower:2.2.0` hizalaması | XS | Tutarlılık, Bakım |
| 5 | F3-06 | `adopt` | `Backend/Dockerfile` ve `Backend/go/Dockerfile` non-root `USER`, `@sha256:` digest sabitleme, `docker-compose.yml` kaynak limitleri ve `dev` profili ayrımı | M | Güvenlik, Dağıtım |
| 6 | F3-08 | `adopt` | `Chrome for Testing` (`145.0.7632.46` → `158.0.8127.88`) ve `pandas`/`openpyxl` manifest-lockfile eşitlemesi | S | Güvenlik, Scraping |
| 7 | F3-09 | `adopt` | `.github/workflows` CI (`ruff`, `mypy`, `pytest`, `vitest`, `pip-audit`, `npm audit`, `govulncheck`) + `dependabot.yml` + hash'li Python lockfile | M | Güvenlik, DX |
| 8 | F3-10 | `trial` | `framer-motion` → `motion` (`motion/react`) paket geçişi | XS | Bakım |
| 9 | F3-11 | `trial` | `three` + `postprocessing` (`Hyperspeed.tsx`) dinamik import / hafif CSS alternatifi ve chunk ölçümü | S | UX, Kaynak verimliliği |
| 10 | F3-12 | `trial` | `vitest` `4.1.10` → `5.1.2` (`@vitest/mocker` GHSA temizliği) | XS | Güvenlik, Test |
| 11 | F3-13 | `trial` | `psycopg2-binary` → `psycopg[binary,pool]` (`3.3.9`) geçiş denemesi | M | Performans, Bakım |
| 12 | F3-14 | `trial` | Worker `seccomp:unconfined` yerine özel Chrome seccomp profili | S | Konteyner güvenliği |
| 13 | F3-15 | `trial` / `keep current` | Redis 7.4 (RSALv2/SSPLv1) → Valkey 8.1/9.0 (BSD-3-Clause) *(açık kaynak lisans zorunluluğu varsa)* | S | Lisanslama |
| 14 | F3-16 | `trial` | `scrapling 0.5.1`, `playwright 1.65.2`, `patchright 1.63.0`, `bs4 4.15.0`, `fake-useragent 2.2.0` staging testi | M | Scraping kararlılığı |
| 15 | F3-17 | `defer` | `pandas 3.1.1`, `TypeScript 6/7`, `PostgreSQL 17/18`, `zerolog` → `log/slog`, `Celery` → `Taskiq` | — | Kapsam/maliyet koruması |
| 16 | F3-18 | `keep current` | `Next.js 16.4.6`, `React 19.2.1`, `Tailwind 4`, `TanStack Query 5`, `Chart.js 4`, `FastAPI`, `SQLAlchemy 2`, `utls 1.8.2` | — | Stabil çekirdek |

---

## 3. Kapsam ve Örtü (Scope and Coverage)

| Alan | Kapsam |
| --- | --- |
| Derinlemesine incelenen | Tüm çalışma zamanları (Node, Python, Go), `Frontend/package.json`, `requirements*.txt` / `.lock`, `Backend/go/go.mod`, tüm `Dockerfile*` dosyaları, `docker-compose.yml`, önceki 2 denetim raporu (`tech-stack-audit-1`, `tech-stack-audit-2`), güncel sürüm/EOL/alternatif araştırması. |
| Geniş ölçekte incelenen | `Frontend/` ve `Backend/` yapılandırmaları (`tsconfig.json`, `next.config.ts`, `eslint.config.mjs`, `ruff.toml`, `mypy.ini`, `bandit.yaml`, `pytest.ini`), ekosistem sınırları ve lisans dağılımı. |
| İncelenmeyen / Atlanan | Canlı `pip-audit`, `npm outdated`, `go list -m -u all` (sandbox ağ/cache engeli); `bandit`, `osv-scanner`, `govulncheck` (kurulu değil); canlı Docker çalışma zamanı ve yük testleri. |
| Bilinçli hariç tutulan | Uygulama kaynak kodunda değişiklik yapılmadı; WCAG erişilebilirlik denetimi kapsam dışı bırakıldı. |

---

## 4. Kısıtlar (Constraints)

| Kısıt | Değer | Dayanak |
| --- | --- | --- |
| Dağıtım | Docker Compose (6 servis + opsiyonel `--profile prod` standalone Next.js) + yerel gece çalıştırıcısı (`run_overnight_scraper.py`) | `[observed]` `docker-compose.yml:1-257` |
| Kullanıcı / Yetki | Çok kullanıcılı JWT cookie kimlik doğrulama; rol alanı var ancak admin kontrolü tüm silme uçlarında bağlı değil | `[observed]` `Backend/auth/dependencies.py:148`, `Backend/api/endpoints.py:55` |
| Scraping Hedefleri | HepsiEmlak ve EmlakJet; Cloudflare bypass için uTLS Go proxy + Selenium/Scrapling/Patchright | `[observed]` `docker-compose.yml:22-28`, `requirements.txt:17-48` |
| Veri Hacmi | 81 il, ilçe GeoJSON sınırları (~79,5 MB) ve on binlerce ilan satırı (PostgreSQL 16 + SQLite fallback) | `[observed]` `docs/tech-stack-audit-2-2026-11-23.md:105` |
| Lisans Modeli | `README.md:136` "MIT License" beyanı var; ancak kök dizinde `LICENSE` dosyası mevcut değil | `[observed]` `Test-Path LICENSE = False` |

---

## 5. Teknoloji Yığını Envanteri

| Ekosistem | Konum | Paket Yöneticisi | Lockfile | Runtime / Toolchain | Doğrudan Bağımlılıklar | Build, Test, Dağıtım |
| --- | --- | --- | --- | --- | --- | --- |
| **JavaScript / TypeScript** | `Frontend/` | `npm` (`11.14.1` lokal `[measured]`) | `Frontend/package-lock.json` (v3) `[observed]` | Lokal `Node v24.11.1` `[measured]`, Docker `node:22-alpine` `[observed]`, TS `^5` | 17 prod / 10 dev `[observed]` | `next build` (`standalone`), `vitest`, `@playwright/test`, `eslint` |
| **Python (API)** | `Backend/` + kök | `pip` / `uv` (`requirements-api.lock`) | `requirements-api.lock` (52 paket, hash yok) `[observed]` | Docker `python:3.13-slim` `[observed]`, Lokal `Python 3.14.0` `[measured]` | 17 `[observed]` | `uvicorn main:app`, `ruff 0.15.13`, `mypy`, `pytest` |
| **Python (Worker & Scraping)** | `Backend/` + kök | `pip` / `uv` (`requirements.lock`) | `requirements.lock` (93 paket, hash yok) `[observed]` | Docker `python:3.11-slim-bookworm` `[observed]`, Chrome `145.0.7632.46` | 36 `[observed]` | `Xvfb` + `celery -A celery_app worker` (`concurrency=2`), `playwright install chromium` |
| **Go (TLS Proxy)** | `Backend/go/` | `go modules` | `Backend/go/go.sum` `[observed]` | `go.mod`: `1.26.0`, Lokal: `go1.26.4` `[measured]`, Docker: `golang:1.27-alpine` | 2 doğrudan + 11 dolaylı `[observed]` | `CGO_ENABLED=0 go build`, `alpine:3.24` runner |
| **Veri & İzleme** | `docker-compose.yml` | Docker Hub imajları | Digest yok (floating tag) `[observed]` | `postgres:16-alpine`, `redis:7.4.11-alpine`, `mher/flower:2.0` | — | Compose bridge ağı (`real-estate-network`) |
| **CI / Otomasyon** | Yok | — | — | `.github/workflows/`, `dependabot.yml`, `renovate.json` yok `[observed]` | — | Manuel / yerel test komutları |

---

## 6. Çalışma Zamanı ve Araç Zinciri Hizalaması (Runtime & Toolchain Alignment)

| Runtime / Araç | Tanım Noktası | Değer | Destek / EOL Durumu (`2026-11-27`) | Sapma (Drift) |
| --- | --- | --- | --- | --- |
| **Node.js** | Lokal ortam `[measured]` | `v24.11.1` | Maintenance LTS, EOL **2028-04-30** `[sourced]` [endoflife.date/nodejs](https://endoflife.date/nodejs) | **Var (`F3-03`)** |
| **Node.js** | `Frontend/Dockerfile:3`, `docker-compose.yml:213` `[observed]` | `node:22-alpine` | Maintenance LTS, EOL **2027-04-30** `[sourced]` [endoflife.date/nodejs](https://endoflife.date/nodejs) | **Var (`F3-03`)** |
| **`@types/node`** | `Frontend/package.json:35` `[observed]` | `^20` | Node 20 EOL (2026-04-30) `[unverified — tam gün cross-check]`; `engines` yok | **Var (`F3-03`)** |
| **Python** | `Backend/Dockerfile:3`, `requirements-api.lock:2` `[observed]` | `3.13` | Security fixes, EOL **2029-10-31** `[sourced]` [devguide.python.org](https://devguide.python.org/versions/) | **Var (`F3-03`)** |
| **Python** | `Backend/Dockerfile.worker:3`, `requirements.lock:2` `[observed]` | `3.11` | Security fixes, EOL **2027-10-31** (11 ay kaldı) `[sourced]` [devguide.python.org](https://devguide.python.org/versions/) | **Var (`F3-03`)** |
| **Python (Analiz)** | `ruff.toml:1`, `mypy.ini:2` `[observed]` | `3.12` | Security fixes `[sourced]` | **Var (`F3-03`)** |
| **Python (Lokal)** | Lokal ortam `[measured]` | `3.14.0` | Bugfix, EOL **2030-10-31** `[sourced]` [devguide.python.org](https://devguide.python.org/versions/) | **Var (`F3-03`)** |
| **Go** | `Backend/go/go.mod:3` / Lokal / `Backend/go/Dockerfile:4` | `1.26.0` / `1.26.4` / `1.27` | Go politikası: son 2 majör sürüm (~1 yıl). `1.27` (Ağustos 2026) ~2027 sonuna kadar `[sourced]` [endoflife.date/go](https://endoflife.date/go) | **Var (`F3-04`)** |
| **PostgreSQL** | `docker-compose.yml:69` `[observed]` | `16-alpine` | EOL **2028-11-09** `[sourced]` [endoflife.date/postgresql](https://endoflife.date/postgresql) | — |
| **Redis** | `docker-compose.yml:90` `[observed]` | `7.4.11-alpine` | EOL **2029-12-01** `[sourced]` [endoflife.date/redis](https://endoflife.date/redis) | — |
| **Alpine Linux** | `Backend/go/Dockerfile:21` `[observed]` | `3.24` | EOL **2028-06-01** `[sourced]` [endoflife.date/alpine-linux](https://endoflife.date/alpine-linux) | — |

**Çoklu manifestlerde farklı sabitlenen kütüphaneler:**
- `pandas`: `requirements.txt:2` / `requirements.lock` = `2.1.3` vs `requirements-api.txt:14` / `requirements-api.lock` = `2.3.3` `[observed]` `[measured]`.
- `openpyxl`: `requirements.txt:3` / `requirements.lock` = `3.1.2` vs `requirements-api.txt:15` / `requirements-api.lock` = `3.1.5` `[observed]` `[measured]`.
- `flower`: `requirements.lock` = `2.2.0` vs `docker-compose.yml:189` = `mher/flower:2.0` `[observed]` `[measured]`.
- `next` vs `eslint-config-next`: `16.4.6` vs `16.0.10` (`Frontend/package.json:22,39`) `[observed]`.

---

## 7. Ekosistem Sınırları (Ecosystem Boundaries)

- **Frontend → API:** HTTP + cookie tabanlı JWT (`NEXT_PUBLIC_API_URL`). `Frontend/contexts/AuthContext.tsx:31,51` `sessionStorage['auth_user']` profil kopyası tutuyor; sunucu taraflı `middleware.ts` yok `[observed]`.
- **API → Worker (Celery/Redis):** `Backend/api/endpoints.py:106-107` önce `apply_async`, sonra `create_queued_task` çağırıyor (hızlı worker'da başlangıç yarışı riski) `[observed]`.
- **Worker → Chrome/Selenium:** `Backend/Dockerfile.worker:96` varsayılan `--concurrency=2` ayarlarken, `Backend/core/driver_manager.py:37,40` süreç grubu filtresi olmadan `pkill -f chrome` çalıştırıyor; eşzamanlı iki görev birbirinin tarayıcısını öldürebilir `[observed]` `[estimate]`.
- **Worker → Go Proxy:** `docker-compose.yml:40,129,167` `PROXY_API_KEY=${PROXY_API_KEY:-}` boş varsayılan geçerken, `Backend/go/handler.go:222-225` boş `APIKey` durumunda `/proxy` isteklerini `401` ile reddeder `[observed]`. Ayrıca tam HTTP gövdesi JSON içinde Base64 olarak taşınıyor (`handler.go:424`) `[observed]`.

---

## 8. Değerlendirme Mercekleri Özeti (Lens Summary)

| Mercek | Durum | Özet | İlgili Bulgular |
| --- | --- | --- | --- |
| **Performans ve eşzamanlılık** | Kısmen iyileşti / Açıklar var | Audit 2 iyileştirmeleri (cache, batch, session pool) uygulandı; `psycopg3`, Excel gereksiz `COUNT` ve `pkill -f chrome` çakışması açık | F3-13, Ek A |
| **Gecikme ve önbellekleme** | İyi / Kontrol altında | `results.cached_read`, ilçe GeoJSON LRU + pre-gzip + ETag ve `GZipMiddleware` aktif | — |
| **Güvenlik** | **Kritik/Yüksek bulgular** | `passlib` EOL, `npm audit` 5 prod / 32 toplam zafiyet, `Chrome 145` (13 sürüm eski), root Docker imajları, `seccomp:unconfined`, admin/IDOR açıkları | F3-01, F3-02, F3-05, F3-06, F3-08, F3-14 |
| **Kullanıcı deneyimi (UX)** | Orta bulgu | `three` + `postprocessing` (`Hyperspeed.tsx`) potansiyel büyük JS/GPU yükü | F3-11 |
| **Kaynak verimliliği** | Bulgu | Worker imajında çift tarayıcı (`Chrome 145` + `Playwright Chromium 153`), Compose kaynak limitlerinin yokluğu | F3-06, F3-08 |
| **Sürdürülebilirlik (Maintainability)** | Bulgular | 4'lü Python runtime drift'i, 3'lü Node/Go drift'i, `eslint` v9 EOL, `framer-motion` bakım modu | F3-02, F3-03, F3-04, F3-10 |
| **Geliştirici deneyimi (DX)** | Bulgu | CI pipeline (`.github/workflows`) ve Dependabot/Renovate yok; `README.md` eski CLI akışını anlatıyor | F3-09, Ek A |
| **Lisanslama ve uyumluluk** | Bulgu | Kök `LICENSE` dosyası eksik; Redis 7.4 `RSALv2/SSPLv1` vs Valkey `BSD-3-Clause`; `LGPL-3.0` (`@img/sharp-libvips-*`) | F3-15, Bölüm 13 |
| **Dağıtım ve paketleme** | Bulgular | Floating tag'ler (digest yok), dev Compose varsayılan olarak `npm install && npm run dev` çalıştırıyor | F3-06 |

---

## 9. Bulgular Özeti (Findings Overview)

| Öncelik | Alan | Mevcut Durum | Kanıt | Öneri | Beklenen Fayda | Maliyet / Risk | Güven |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **P1** | Auth / Kripto | `passlib==1.7.4` + `bcrypt==4.0.1` | `[observed]` `security.py:10`, `[sourced]` | `adopt`: `pwdlib` (`argon2`+`bcrypt`) veya `bcrypt 5.0` | Python 3.13+ uyumu, aktif bakım | Düşük-Orta (mevcut hash'ler doğrulanmalı) | Yüksek |
| **P1** | Konteyner Güvenliği | Root API/Go imajı, digest yok, limit yok, `seccomp:unconfined` | `[observed]` `Dockerfile*`, `docker-compose.yml` | `adopt`: non-root, `@sha256:`, limitler; `trial`: Chrome seccomp | Küçük saldırı yüzeyi, tekrarlanabilir build | Düşük-Orta | Yüksek |
| **P1** | Worker Tarayıcı | `Chrome 145.0.7632.46` (13 sürüm eski) + Chromium `153` | `[observed]` `Dockerfile.worker:51`, `[sourced]` | `adopt`: `158.0.8127.88`'e güncelle, tek tarayıcıyı değerlendir | Güvenlik yamaları, güncel TLS/UA parmak izi | Düşük | Yüksek |
| **P1** | CI & Lockfile | CI yok, Dependabot yok, Python lock hash'siz | `[observed]` repo kökü | `adopt`: GitHub Actions + Dependabot + hash'li lock | Otomatik CVE/lint/test kapısı | Orta | Yüksek |
| **P2** | Frontend Lint & Audit | `eslint ^9` (EOL), `eslint-config-next 16.0.10`, `@types/three` prod'da, 32 zafiyet | `[observed]`, `[measured]`, `[sourced]` | `adopt`: `eslint@^10` + `16.4.6`, `@types/*` dev'e, `npm audit` fixleri | EOL dışına çıkış, daha temiz prod audit | Düşük | Yüksek |
| **P2** | Runtime Drift | Python `3.11`/`3.12`/`3.13`/`3.14`; Node `20`/`22`/`24`; Go `1.26`/`1.27` | `[observed]`, `[measured]` | `adopt`: Python `3.13`, Node `22/24 LTS`, Go `1.27` hizalaması | Ortamlar arası tutarlılık | Düşük-Orta | Yüksek |
| **P2** | `three` / `Hyperspeed` | `three ^0.182.0` + `postprocessing` | `[observed]`, `[sourced]` (~700 KB+) | `trial`: dinamik import / hafif CSS alternatifi ölçümü | Daha küçük ilk yükleme ve düşük GPU yükü | Düşük-Orta | Orta |
| **P2** | `vitest` & `framer-motion` | `vitest 4.1.10` (2 GHSA), `framer-motion 12.23` (bakım modu) | `[measured]`, `[sourced]` | `trial`: `vitest 5.1.2` ve `motion` paketi | Zafiyet temizliği, aktif bakım | Çok düşük | Yüksek |
| **P2** | Redis Lisansı | `redis:7.4.11-alpine` (`RSALv2/SSPLv1`) | `[observed]`, `[sourced]` | `trial`: `Valkey 8.1/9.0` (`BSD-3-Clause`) *(lisans gerekirse)* | OSI onaylı açık kaynak uyumu | Düşük | Yüksek |
| **P3** | `psycopg2-binary` | `>=2.9.0` (senkron) | `[observed]`, `[sourced]` | `trial`: `psycopg[binary,pool]` (`3.3.9`) | Async/sync birleşik sürücü, daha düşük bellek | Orta | Orta |
| **P3** | Scraping Çekirdeği | `scrapling 0.4.15`, `playwright 1.56.0` | `[measured]`, `[sourced]` | `trial`: `scrapling 0.5.1` + `playwright 1.65.2` staging testi | Anti-bot uyumluluğu | Orta (`curl_cffi 0.17` breaking dikkat) | Orta |

---

## 10. Detaylı Bulgular, Güncel Sürümler ve Alternatif Karşılaştırmaları

### 10.1 Frontend (Next.js / React / UI / Test) — Güncel Sürüm & Alternatif Matrisi

| Paket | Mevcut | Güncel (2026-11-27) | Alternatifler & Karşılaştırma | Karar | Kaynak |
| --- | --- | --- | --- | --- | --- |
| **Next.js** | `^16.4.6` | `16.4.x` LTS | Remix / TanStack Start: gereksiz yeniden yazım | `keep current` | [nextjs.org](https://nextjs.org) |
| **React** | `19.2.1` | `19.3.1` | Minor güncelleme opsiyonel | `keep current` | [react.dev](https://react.dev) |
| **TypeScript** | `^5` | `6.0` / `7.0-7.1 Beta` | TS 7 (Go-native) henüz beta | `defer` | [typescriptlang.org](https://www.typescriptlang.org) |
| **Tailwind CSS** | `^4` | `4.3+` | CSS-first v4 hattı güncel | `keep current` | [tailwindcss.com](https://tailwindcss.com) |
| **ESLint + config** | `^9` / `16.0.10` | `10.15.0` / `16.4.6` | **v9 EOL.** Biome alternatifi mümkün ancak `eslint-config-next 16.4.6` + `eslint 10` en küçük fark | `adopt` | [eslint.org](https://eslint.org) |
| **TanStack Query** | `^5.90.21` | `5.108.4` | SWR / RTK Query'ye geçmeye gerek yok | `keep current` | [npmjs.com](https://www.npmjs.com/package/@tanstack/react-query) |
| **Chart.js** | `4.5.1` / `5.3.1` | `4.6.2` / `5.3.1` | Tree-shaken ~35–45 KB gzip (Recharts ~95–116 KB, ECharts ~135–190 KB); zaten lazy-load | `keep current` | [npmjs.com](https://www.npmjs.com/package/chart.js) |
| **framer-motion** | `^12.23.26` | `motion` (aktif) | `framer-motion` bakım modunda; `motion` (`motion/react`) birebir API | `trial` | [motion.dev](https://motion.dev) |
| **three + postprocessing** | `0.182.0` / `6.38.2` | `0.187.0` / `6.39.6` | ~700 KB+ JS yükü; `Hyperspeed.tsx` dekoratifse CSS/2D canvas | `trial` | [npmjs.com](https://www.npmjs.com/package/three) |
| **d3-geo + turkey-map** | `3.1.1` / `2.0.3` | `3.1.2` / `2.4.3` | Zaten lazy-load ediliyor | `keep current` | [npmjs.com](https://www.npmjs.com/package/turkey-map-react) |
| **vitest** | `^4.1.10` | `5.1.2` | v4 `@vitest/mocker` için 2 moderate GHSA içeriyor | `trial` | [npmjs.com](https://www.npmjs.com/package/vitest) |
| **@playwright/test** | `^1.62.1` | `1.65.1` | Rutin minor güncelleme | `keep current` | [npmjs.com](https://www.npmjs.com/package/@playwright/test) |

### 10.2 Python Backend & Scraping — Güncel Sürüm & Alternatif Matrisi

| Paket / Araç | Mevcut (Lock) | Güncel (2026-11-27) | Alternatifler & Risk Notu | Karar | Kaynak |
| --- | --- | --- | --- | --- | --- |
| **FastAPI / Uvicorn** | `0.154.0` / `0.54.0` | `0.165.0` / `0.54.0` | Litestar: geçiş maliyeti gereksiz | `keep current` | [pypi.org/project/fastapi](https://pypi.org/project/fastapi/) |
| **SQLAlchemy** | `2.1.5` | `2.1.9` | SQLModel ek soyutlama ekler | `keep current` | [sqlalchemy.org](https://www.sqlalchemy.org/) |
| **psycopg2-binary** | `>=2.9.0` | `2.9.13` | `psycopg[binary,pool]` (`3.3.9`): yerel async + daha düşük bellek | `trial` | [pypi.org/project/psycopg](https://pypi.org/project/psycopg/) |
| **pandas / openpyxl** | Worker `2.1.3`/`3.1.2`, API `2.3.3`/`3.1.5` | `3.1.1` / `3.1.5` | `3.x` CoW breaking change; `2.3.3` + `3.1.5`'e eşitle | `adopt` (eşitle) / `defer` (`3.x`) | [pandas.pydata.org](https://pandas.pydata.org/) |
| **passlib + bcrypt** | `1.7.4` + `4.0.1` | `passlib` terk / `bcrypt 5.0.0` | `passlib` 2020'den beri terk, Python 3.13 `crypt` yok. **`pwdlib` (`0.4.2`) + `argon2-cffi` (`25.1.0`)** veya `bcrypt 5.0.0` | `adopt` | [pypi.org/project/pwdlib](https://pypi.org/project/pwdlib/) |
| **PyJWT / multipart** | `2.15.1` / `0.0.32` | `2.15.1` / `0.0.34` | Güncel CVE yamalarının üzerinde | `keep current` | [snyk.io](https://snyk.io/) |
| **Celery / Flower** | `5.6.3` / `2.2.0` (Compose `2.0`) | `5.7.0` / `2.2.0` | `taskiq` (`0.13.0`), `dramatiq` (`2.2.1`), `arq` (`0.28.0`) — yeniden yazım gereksiz | `keep current` (`flower:2.2.0` `adopt`) | [docs.celeryq.dev](https://docs.celeryq.dev/) |
| **scrapling / curl_cffi** | `0.4.15` / `0.16.3` | `0.5.1` / `0.17.0` | `curl_cffi 0.17.0` breaking namespace değişikliği içerir; birlikte test edilmeli | `trial` | [pypi.org/project/scrapling](https://pypi.org/project/scrapling/) |
| **playwright / patchright** | `1.56.0` / `1.56.0` | `1.65.2` / `1.63.0` | Anti-bot uyumluluğu için staging testi | `trial` | [playwright.dev](https://playwright.dev/) |
| **selenium / undetected-cd** | `4.51.0` / `>=3.5.0` | `4.54.0` / `3.5.5` | `undetected-chromedriver` bakım hızı düşmüş; `patchright`/`scrapling` öne çıkıyor | `trial` (konsolidasyon) | [pypi.org/project/undetected-chromedriver](https://pypi.org/project/undetected-chromedriver/) |
| **Chrome for Testing** | `145.0.7632.46` | `158.0.8127.88` | 13 majör sürüm geride | `adopt` | [googlechromelabs.github.io](https://googlechromelabs.github.io/chrome-for-testing/) |
| **bs4 / fake-useragent / packaging** | `4.12.2` / `1.4.0` / `23.2` | `4.15.0` / `2.2.0` / `26.4` | Rutin yükseltme adayı | `trial` | [pypi.org](https://pypi.org/) |

### 10.3 Go Proxy ve Veri Servisleri — Güncel Sürüm & Alternatif Matrisi

| Bileşen | Mevcut | Güncel (2026-11-27) | Alternatifler & Not | Karar | Kaynak |
| --- | --- | --- | --- | --- | --- |
| **utls** | `v1.8.2` | `v1.8.2` | `bogdanfinn/tls-client` (`v1.18.x`) ek katman ekler; mevcut `utls` yeterli | `keep current` | [github.com/refraction-networking/utls](https://github.com/refraction-networking/utls) |
| **zerolog** | `v1.32.0` | `v1.35.1` | `log/slog` (stdlib) refaktör gerektirir; yama güncellemesi yeterli | `adopt` (`v1.35.1`) / `defer` (`slog`) | [deps.dev](https://deps.dev) |
| **PostgreSQL** | `16-alpine` | `17` / `18` | PG 16 EOL **2028-11-09**; acil geçiş gerekmez | `keep current` / `defer` | [endoflife.date/postgresql](https://endoflife.date/postgresql) |
| **Redis** | `7.4.11-alpine` | `8.2 / 8.4 / 8.6` | Redis 7.4 EOL **2029-12-01** (`RSALv2/SSPLv1`). **Valkey 8.1/9.0** (`BSD-3-Clause`) drop-in alternatif | `trial` (Valkey) / `keep current` | [endoflife.date/redis](https://endoflife.date/redis) / [valkey.io](https://valkey.io/) |

---

## 11. Hızlı Kazanımlar ve Mimari Değişiklikler

- **Hızlı kazanımlar (düşük risk, küçük diff):** `F3-02` (`eslint-config-next`, `@types/*`), `F3-04` (Go `1.27` + `-mod=readonly` + `zerolog v1.35.1` + `flower:2.2.0`), `F3-06` (non-root `USER`, kaynak limitleri, Compose `dev` profili), `F3-08` (`Chrome 158`, `pandas`/`openpyxl` eşitlemesi), `F3-10` (`motion` paketi), `F3-12` (`vitest 5`).
- **Ölçülü denemeler:** `F3-01` (`passlib` → `pwdlib` göçü), `F3-11` (`three` chunk ölçümü), `F3-13` (`psycopg3`), `F3-14` (Chrome seccomp), `F3-15` (Valkey), `F3-16` (scraping çekirdek yükseltmesi).
- **Mimari değişiklikler:** Önerilmiyor (mevcut 6 servisli mimari korunuyor).

---

## 12. Önceki Denetimlerin Takibi (`tech-stack-audit-1` ve `tech-stack-audit-2`)

### 12.1 Audit 1 (`7f8a9d8` → `b886a0a`)
- **Uygulandı / Güncellendi:** `F-27..F-28` (`next ^16.4.6` güncellemesi commit `f5cd17c`, backend çekirdeği korundu).
- **Kısmen Uygulandı (7 madde):** `F-10` (`real-estate-frontend-prod` eklendi ama dev profili hâlâ varsayılan), `F-14` (`motion`/`ogl` kaldırıldı, ama `@types/*` prod'da ve `eslint-config-next` `16.0.10`), `F-15` (`Aurora`/`ParticleBackground` silindi, ama `BlurText.tsx` ve `AnimatedList.tsx` hâlâ ölü kod), `F-18` (`clear_results` FK-safe, ama Alembic ve `PRAGMA foreign_keys=ON` yok), `F-19` (`_jwt_secret()` sertleştirildi, ama 7 günlük token ve refresh/jti eksik), `F-20` (`client_pool` recycle ve context iptali eklendi, ama `MaxBytesReader` ve XFF kısıtı yok), `F-21` (`selectinload` + SQL aggregate + Excel process izolasyonu var, ama `/listings` `page/limit` sınırı yok).
- **Hâlâ Açık (14 madde):** `F-01` (resmi API / `robots.txt`), `F-02` (admin yetki kontrolü), `F-03` (task IDOR / `user_id`), `F-04` (`apply_async` vs `create_queued_task` sırası), `F-05` (rate limit), `F-06` (CI & Dependabot yok), `F-07` (Compose portları `0.0.0.0`), `F-08` (`flower:2.0`), `F-09` (API root `USER` + `/health`), `F-11` (SHA256 digest yok), `F-12` (hash'siz lockfile + 3.11/3.13 drift), `F-13` (`passlib` + `bcrypt 4.0.1`), `F-16` (`README.md` + `LICENSE` yok), `F-17` (3 tarayıcı yığını konsolidasyonu), `F-22` (CSP/headers/`middleware.ts`), `F-23` (`npm audit` prod bulguları), `F-24..26` (ertelenen runtime yükseltmeleri).

### 12.2 Audit 2 (`fe6bdf8` → `b886a0a` Performans Takibi)
- **Uygulandı:** `2–3` (`results.cached_read` ve cache invalidation), `7` (`TaskStatusStore` `@lru_cache` Redis client + `SMEMBERS`/`MGET`), `8–9` (toplu DB lookup ve bellek azaltımı), `12` (ilçe GeoJSON LRU + pre-gzip + ETag + `GZipMiddleware`).
- **Kısmen Uygulandı:** `1` (`get_current_user` `def` + 15 sn cache, ama `get_current_active_admin`/`/auth/me` `async def`), `4` (indeksler var, `/listings` limit sınırı yok), `6` (concurrency=2 oldu, ama `apply_async` yarışı ve `pkill -f chrome` riski var), `10` (`requests.Session` havuzu eklendi, Base64 gövde sürüyor), `11` (`AbortSignal` eklendi, `startScrape`/`getStats` timeout yok), `13` (`motion` tekilleşti, masaüstü WebGL yükü sürüyor), `14` (`prod` profili eklendi).
- **Açık:** `5` (`_get_excel_rows` hâlâ kullanılmayan `COUNT` çalıştırıyor).

---

## 13. Lisanslama Özeti

> **Uyarı:** Bu bölüm teknik envanter ve paket meta verilerine dayanır; **hukuki tavsiye niteliği taşımaz**. Nihai uyumluluk kararları yetkin hukuk danışmanına bırakılmalıdır.

| Ekosistem / Katman | Tespit Edilen / Baskın Lisanslar | Gözlenen Yükümlülük / Risk |
| --- | --- | --- |
| **Proje Kökü** | `README.md:136` "MIT License" beyanı; **`LICENSE` dosyası YOK** `[observed]` | Lisans metni eksikliği dağıtım belirsizliği yaratır; `LICENSE` eklenmeli. |
| **Frontend (`package-lock.json`)** | `MIT` (404), `Apache-2.0` (36), `MPL-2.0` (25, dev-only), `ISC` (23), `LGPL-3.0-or-later` (10 + 4 karma — `@img/sharp-libvips-*`), `BSD-2/3` (10) `[measured]` | Standalone imajda `sharp` kullanılırsa `LGPL-3.0-or-later` yükümlülükleri doğabilir; `THIRD-PARTY-NOTICES` önerilir. |
| **Python (API & Worker)** | MIT / BSD / Apache-2.0 / PSF ağırlıklı `[unverified — `pip-licenses` çalıştırılmadı]` | Docker imajlarında telif bildirimleri korunmalı. |
| **Go Proxy** | `utls` (`BSD-3-Clause`), `zerolog` (`MIT`) `[sourced]` | Statik binary dağıtımında BSD-3/MIT metinleri korunmalı. |
| **Altyapı (Redis vs Valkey)** | `redis:7.4.11-alpine` (**RSALv2 / SSPLv1**, OSI onaylı değil); `postgres:16-alpine` (PostgreSQL License) `[sourced]` | Yönetilen ticari servis olarak sunulursa SSPLv1/RSALv2 inceleme gerektirir; **Valkey** (`BSD-3-Clause`) tam açık kaynak alternatiftir. |
| **Veri / İçerik** | EmlakJet / HepsiEmlak ilan verileri `[observed]` | ToS ve FSEK kapsamında yüksek hukuki risk (Audit 1 `F-01` hâlâ açık). |

---

## 14. Doğrulama ve Taramalar

| Komut / Kontrol | Sonuç | Tarih / Not |
| --- | --- | --- |
| `node -v` / `npm -v` (`Frontend/`) | `v24.11.1` / `11.14.1` `[measured]` | 2026-11-27 |
| `npm audit --omit=dev` (`Frontend/`) | **5 zafiyet** (2 moderate `fflate`, 3 high `source-map-js`) `[measured]` | 2026-11-27 |
| `npm audit` (`Frontend/`) | **32 zafiyet** (13 moderate, 19 high) `[measured]` | 2026-11-27 |
| `npm outdated` (`Frontend/`) | **Atlandı (`EPERM` cache hatası)** `[measured]` | Sandbox izin engeli; `search_web` ile telafi edildi |
| `python --version` / `ruff --version` | `Python 3.14.0` / `ruff 0.15.13` `[measured]` | 2026-11-27 |
| `pip-audit -r requirements*.lock` | **Atlandı (asılı kaldı / iptal edildi)** `[measured]` | Sandbox ağ engeli nedeniyle zaman aşımı |
| `bandit`, `osv-scanner`, `govulncheck` | **Atlandı (`NOT_INSTALLED`)** `[measured]` | Kurulu değil (geçer not değildir) |
| `go version` (`Backend/go/`) | `go1.26.4 windows/amd64` `[measured]` | 2026-11-27 |
| `go list -m -u all` (`Backend/go/`) | **Atlandı (`x509` TLS proxy hatası)** `[measured]` | Sandbox proxy engeli |
| `docker compose config --quiet` | **Atlandı (`Access is denied` + `--quiet` flag yok)** `[measured]` | Docker daemon/config erişimi kısıtlı |

---

## 15. Açık Sorular (`[unverified]`)

1. **`pip-audit`, `osv-scanner`, `govulncheck` sonuçları `[unverified]`:** Sandbox ağ kısıtı ve eksik araçlar nedeniyle Python ve Go kilit dosyalarındaki geçişli bağımlılıkların tam CVE taraması yapılamadı. Linux/CI ortamında çalıştırılmalıdır.
2. **`npm outdated` tam çözünmüş sürümleri `[unverified]`:** Yerel terminalde `npm outdated` ile lockfile'daki tüm güncel farklar doğrulanmalıdır.
3. **Worker Python `3.11` → `3.13` uyumluluğu `[unverified]`:** `requirements.lock` paketlerinin (`scrapling`, `patchright`, `curl_cffi`, `lxml`) Python 3.13 üzerinde sorunsuz derlenip çalıştığı test edilmelidir.
4. **`scrapling 0.5.1` & `curl_cffi 0.17.0` uyumu `[unverified]`:** `curl_cffi 0.17.0` namespace değişikliğinin `scrapling` ile uyumu doğrulanmalıdır.
5. **Canlı `pytest` / `vitest` / `next build` & `Hyperspeed.tsx` chunk boyutu `[unverified]`:** Salt-okunur denetim kapsamında bu test/build komutları yeniden çalıştırılmadı.

---

## Ek A. Düşük Öncelikli Gözlemler

| ID | Mercek | Gözlem | Önerilen Etiket |
| --- | --- | --- | --- |
| A-1 | Bakım | `Frontend/tsconfig.json:3` `"target": "ES2017"` eski | `adopt`: `ES2022` değerlendir |
| A-2 | Bakım | `BlurText.tsx` ve `AnimatedList.tsx` hâlâ ölü kod | `adopt`: sil (Audit 1 `F-15`) |
| A-3 | Performans | `Backend/api/endpoints.py:627` `_get_excel_rows` kullanılmayan `COUNT` sorgusu çalıştırıyor | `adopt`: `COUNT`suz sorguya geç |
| A-4 | Eşzamanlılık | `Backend/core/driver_manager.py:37,40` `pkill -f chrome` concurrency=2 ile çakışabilir | `adopt`: PID/profil bazlı kapatma |
| A-5 | DX | `README.md:93-112` hâlâ eski CLI kurulumunu anlatıyor; `LICENSE` dosyası yok | `adopt`: güncelle ve `LICENSE` ekle |
| A-6 | Temizlik | `aiosqlite==0.22.1` her iki Python lockfile'ında aktif kullanılmadan yer alıyor | `defer`: doğrulayıp kaldır |

## Ek B. Reddedilen Fikirler

| Fikir | Neden Reddedildi |
| --- | --- |
| Frontend'i Remix / TanStack Start'a taşımak | Next.js 16.4.6 Active LTS güncel; yeniden yazım maliyeti yüksek ve hedef yok |
| `chart.js` yerine Recharts veya ECharts'a geçmek | `chart.js` (~35–45 KB gzip) her ikisinden de hafif ve zaten lazy-load ediliyor |
| Celery yerine Taskiq / Dramatiq / Arq'ya geçmek | Mevcut `celery 5.6.3` + `flower 2.2` çalışıyor; yeniden yazım maliyeti yüksek |
| Go `utls` yerine `tls-client` sarmalayıcısına geçmek | `utls v1.8.2` güncel ve `HelloChrome_133` profilini doğrudan destekliyor |
| `pandas 3.1.1`'e hemen yükseltmek | Copy-on-Write varsayılanı mevcut DataFrame kodunu kırma riski taşıyor |
