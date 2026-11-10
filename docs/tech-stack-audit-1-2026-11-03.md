# Tech Stack Audit 1 — real-estate-scraper

| Alan | Değer |
| --- | --- |
| Dosya | `docs/tech-stack-audit-1-2026-11-03.md` |
| Tarih | 2026-11-02 / 2026-11-03 |
| Commit | `7f8a9d8` (`main`), temiz çalışma ağacı |
| Mod | **Audit** — bu rapor dışında hiçbir dosya değiştirilmedi |
| Hedef | "Bu projedeki her servis için code review yap ve tech-stack-optimizer uygula" |
| Kapsam | Tüm repo: `Backend/` (FastAPI API, Celery worker, scraper'lar, Go uTLS proxy), `Frontend/` (Next.js), `docker-compose.yml`, Dockerfile'lar, lockfile'lar, `.env.example`, README, `.github` (yok) |
| Önceki audit | Yok (ilk audit) |
| Kullanılan skill'ler | `code-review` (tüm servisler için uyarlandı), `tech-stack-optimizer` |
| Kullanılmayan skill'ler | `security-auditor` / `dependency-upgrade` yüklü ama çalıştırılmadı; güvenlik bulguları manuel doğrulandı. `docker-containerization` ve `github-actions-ci` yerine doğrudan inceleme yapıldı. |
| Tarama tarihleri | `npm audit`: 2026-11-03 registry. `pip-audit`: tamamlanamadı (aşağıda). `go vet ./...`: 2026-11-03, exit 0. Docker daemon erişilemez; container build doğrulaması yapılmadı. |

Kanıt etiketleri: `[observed]` = repodan doğrulandı (dosya:satır) · `[measured]` = lokal ölçüm/komut · `[sourced]` = dış kaynak (tarihli) · `[estimate]` = yön tahmini · `[hypothesis]` = doğrulanması gereken tahmin · `[unverified]` = kontrol edilemedi.

---

## 1. Karar

- **Mimariyi şimdilik koru; veri toplama stratejisini değiştir.** Go proxy + Celery + FastAPI + Next.js yığını teknik olarak çalışıyor ancak ürünün merkezindeki "Cloudflare'i atlatarak emlak sitelerinden çekme" yaklaşımı hukuki/izinsel olarak sürdürülemez ve hedeflerin ToS'unu ihlal ediyor (F-01). Bu, güvenlik açıklarından daha yüksek öncelikli bir risk. Resmi API / veri lisansı / işbirliği veya ToS'a uygun, robots.txt'e saygılı, parmak izi taklidi olmayan bir toplama modeline geçilmeli. Bu bir ürün/hukuk kararıdır; teknik audit verisi değildir ama yığını doğrudan belirler.
- **Hızlı kazanımlar (adopt):** yetkilendirme açıklarını kapatmak (F-02, F-03), spawn/dispatch sırası (F-04), rate limiting (F-05), CI pipeline'ı (F-06), compose/image sertleştirme (F-07..F-12), bağımlılık temizliği (F-13..F-16).
- **Ölçülü denemeler (trial):** üç tarayıcı-otomasyon yığınından birine inmek (F-17), Alembic baseline (F-18), passlib → argon2/bcrypt (F-19).
- **Ertele (defer):** Node 24 LTS geçişi, Postgres 18, Python 3.14 (F-26..F-28).
- **Koru (keep current):** Next.js 16.4.1, React 19, Tailwind 4, FastAPI 0.154, SQLAlchemy 2.1, Celery 5.6, Go 1.27, Postgres 16, Redis 7.4 (aktif destek penceresinde).

Kısa haliyle: **stack'i değiştirme, yığın içindeki yetkilendirme/dağıtım/CI açıklarını kapat, ama bypass ürünü olarak konumlandırmayı bırak.** Yeni altyapı yatırımı yapmadan önce legal review + resmi veri rotası kararı verilmeli.

## 2. Karar listesi

| # | ID | Etiket | Aksiyon | Efor | Hedefe bağ |
| --- | --- | --- | --- | --- | --- |
| 1 | F-01 | `adopt` + **insan kararı** | Bypass yerine resmi/lisanslı veri rotası; robots/ToS + legal review | M–L | Ürün/hukuk |
| 2 | F-02 | `adopt` | `DELETE /clear-results` ve silme uçlarını admin'e bağla | XS | Güvenlik |
| 3 | F-03 | `adopt` | Task'lere `user_id` ekle; oku/iptali sahibine sınırla (IDOR) | M | Güvenlik |
| 4 | F-04 | `adopt` | `create_queued_task` önce; dispatch fail olursa kaydı failed yap | S | Doğruluk |
| 5 | F-05 | `adopt` | Auth + scrape başlatma için Redis rate limit / kilitleme | S–M | Güvenlik |
| 6 | F-06 | `adopt` | CI: ruff/mypy/pytest, npm lint+typecheck+vitest, go test/vet, audit, docker build; Dependabot | M | DX/güvenlik |
| 7 | F-07 | `adopt` | DB/Redis/proxy/Flower portlarını `127.0.0.1`e bağla; iç ağa dokunma | XS | Güvenlik |
| 8 | F-08 | `adopt` | Flower parolası rotasyona; `mher/flower:2.0` (2023-08) → `2.2.0` (2026-11-02) | XS | Güvenlik |
| 9 | F-09 | `adopt` | API image'da `USER` non-root; `--proxy-headers`; healthcheck → `/health` (DB+Redis) | S | Güvenlik |
| 10 | F-10 | `adopt` | Compose'u dev/prod ayır; prod hedefinde hazır `Frontend/Dockerfile`'ı kullan; kök `.env` yerine `env_file` açıkça yaz | S | Güvenilirlik |
| 11 | F-11 | `adopt` | Base image'ları digest ile pinle + Dependabot docker | XS | Tekrarlanabilirlik |
| 12 | F-12 | `adopt` | Lockfile'lara hash ekle (`uv pip compile --generate-hashes`); worker 3.11 ↔ API 3.13 farkını hizala; `.python-version` ekle | S | Tekrarlanabilirlik |
| 13 | F-13 | `adopt` | `passlib==1.7.4` → argon2 veya doğrudan `bcrypt>=4.2`; 72-byte sınırını şemada uygula | S | Güvenlik |
| 14 | F-14 | `adopt` | Frontend paket temizliği: `framer-motion`/`motion` ikilisinden tekilleştir; `@types/*` dev'e; `eslint-config-next` 16.4.x'e; `npm audit fix` | S | Bakım |
| 15 | F-15 | `adopt` | Dead code temizliği (Aurora, ParticleBackground, BlurText, AnimatedList, kullanılmayan export/ölü kod Go proxy'de) | S | Bakım |
| 16 | F-16 | `adopt` | README'yi gerçeğe hizala (CLI değil API+Compose); `LICENSE` (MIT) ekle; docs/ADR için `docs/` kullan | XS | DX |
| 17 | F-17 | `trial` | 3 otomasyon yığınını (selenium + undetected-chromedriver, scrapling/patchright, Go uTLS proxy) ölçüp teke indir | M | Maliyet/kırılganlık |
| 18 | F-18 | `trial` | Alembic baseline + `PRAGMA foreign_keys=ON` (SQLite) + FK-safe silme | M | Veri bütünlüğü |
| 19 | F-19 | `trial` | JWT: kısa access token + refresh/jti revoke; `JWT_ALGORITHM` allowlist; startup'ta config doğrulama | M | Güvenlik |
| 20 | F-20 | `adopt` | Go proxy: body limitleri (`MaxBytesReader`/`context` bütçesi), XFF güven kısıtı, shutdown WaitGroup, unbounded pool → semaphore | M | Güvenlik/güvenilirlik |
| 21 | F-21 | `adopt` | Analytics/export'u SQL aggregate + `limit`/`page` doğrulaması + `joinedload` | S–M | Performans |
| 22 | F-22 | `adopt` | Frontend: güvenlik header'ı/CSP, `middleware.ts` ile server-side korumalı rota yönlendirme | S–M | Güvenlik |
| 23 | F-23 | `track` | npm audit süren 2 prod bulgusu (source-map-js high, fflate moderate) — fix bekliyor | XS | Güvenlik |
| 24 | F-24 | `defer` | Postgres 16 → 18 | — | Bakım |
| 25 | F-25 | `defer` | Node 22 → 24 (24 Active LTS, 2028-04'e kadar) | — | Bakım |
| 26 | F-26 | `defer` | Python 3.13 → 3.14 (bağımlılık desteği doğrulandıktan sonra) | — | Bakım |
| 27 | F-27 | `keep current` | Next.js 16.4.1 (16.4.x, 2026-10-14 güvenlik yamaları dahil), React 19, Tailwind 4 | — | — |
| 28 | F-28 | `keep current` | FastAPI / SQLAlchemy / Celery / Redis 7 / Postgres 16 | — | — |

## 3. Kapsam ve kapsam dışı

| Alan | Kapsama |
| --- | --- |
| Derin incelenen | 4 çalışma zamanı ekosistemi + compose + Dockerfile'lar + lockfile'lar + `.env.example` + auth akışı |
| Geniş incelenen | Tüm doğrudan bağımlılıklar; transitif bağımlılıklar scanner/lockfile üzerinden |
| İncelenmeyen | `Backend/data/` (district JSON), `Backend/scrapers/*/parsers` satır satır doğruluğu, `Fontend` görsel regresyonları, container image'ların trivy/hadolint taraması (araç yok / daemon kapalı), `pip-audit` tamamlanamadı (aşağıda §14) |
| Bilinçli dışarıda | Bypass mantığına "daha iyi çalışma" önerileri (izinsiz/paralel kullanım) |

## 4. Kısıtlar

| Kısıt | Değer | Kaynak |
| --- | --- | --- |
| Dağıtım | Tek host Docker Compose (dev-tipi) | `[observed]` `docker-compose.yml` |
| Kullanıcı | Çok kullanıcılı (register açık) ama tek-instance | `[observed]` `backend/auth/router.py:58`, `endpoint`lar global veri sunuyor |
| Veri hacmi | İlan + fiyat geçmişi; export 10.000 satır | `[observed]` export isteği `limit=10000` |
| Gizlilik | Emlak ilanı verileri kişisel veri içermez; ancak scrape hedefleri (EmlakJet/HepsiEmlak) ticari taraf | `[observed]` README |
| Latency hedefi | Belirtilmemiş | `[unknown]` |
| Ekip | Tek geliştirici görünümü (commit geçmişi HSCN) | `[observed]` git log |
| Lisans modeli | README "MIT License" diyor, `LICENSE` dosyası YOK; Thordata sponsorluğu | `[observed]` README.md:9-15,135-136 |
| Yasal rejim | Türk siteleri; ToS/FSEK veri tabanı hakkı riski | `[observed]` § F-01 |

## 5. Yığın envanteri

| Ekosistem | Konum | Yönetici | Lock | Runtime | Doğrudan dep (prod/dev) | Build/Test/Ship |
| --- | --- | --- | --- | --- | --- | --- |
| Python — API | `Backend/` | pip+uv | `requirements-api.lock` (3.13 hedefli, hash YOK) | python:3.13-slim | ~17 / 0 | uvicorn; `pytest.ini`; tests/ |
| Python — Worker | `Backend/` | pip+uv | `requirements.lock` (3.11 hedefli, hash YOK) | python:3.11-slim-bookworm | ~50 / 0 | Celery; Xvfb+Chrome-for-Testing |
| Go — Proxy | `Backend/go/` | Go modules | `go.sum` | go 1.27 | 2 / 2 | `go test`; static binary; alpine |
| TS — Frontend | `Frontend/` | npm 11 | `package-lock.json` v3 | node:22-alpine (compose), lokal node v24.11.1 | 24 / 14 | Next build; vitest; playwright |
| Containers | `Backend/Dockerfile*`, `Frontend/Dockerfile`, `docker-compose.yml` | Docker | image tags (digest yok) | — | — | compose up |
| CI | YOK | — | — | — | — | — |

Workspace yok; her ekosistem bağımsız.

## 6. Runtime ve toolchain hizalama

| Runtime | Bildirildiği yer | Değer | Destek durumu | Fark |
| --- | --- | --- | --- | --- |
| Python | `Backend/Dockerfile:3` | 3.13 | 3.13 güncel güvenlik fazında; 3.11 (worker) 2027-10'da EOL; 3.14 güncel stabil `[sourced]` [endoflife.date/python](https://endoflife.date/python) (2026-11-03) | **Worker 3.11 ayrı evrende** |
| Python | `Backend/Dockerfile.worker:3` | 3.11 | EOL 2027-10 | **Fark: F-12** |
| Python | `requirements.lock:2` marker | 3.11 | lock 3.11 için üretilmiş | — |
| Python | `requirements-api.lock:2` marker | 3.13 | — | — |
| Node | `docker-compose.yml:212`, `Frontend/Dockerfile:3` | 22 | Maintenance LTS, EOL **2027-04-30**; Node 24 = Active LTS, 2028-04-30 `[sourced]` [Node.js releases](https://nodejs.org/en/about/previous-releases) (2026-11-03) | **22 yaşlanıyor: F-25** |
| Node | `Frontend/package.json` (engines yok) | — | — | eklenmeli |
| Go | `go.mod:3`, `Backend/go/Dockerfile:4` | 1.27 | Desteklenen hat | — |
| Postgres | `docker-compose.yml:68` | 16-alpine | 16.x destekli (until ~2028-11) `[sourced]` endoflife.date | ok |
| Redis | `docker-compose.yml:89` | 7.4.11-alpine | 7.4 destekli | ok |
| Next.js | `package.json:23` | 16.4.1 | Aktif; 2026-10-14 güvenlik yamaları dahil `[sourced]` [nextjs.org/blog/nextjs-security-update-october-14-2026](https://nextjs.org/blog/nextjs-security-update-october-14-2026) | **yanlış alarm yok; 16.4.1 doğru** |

Aynı kütüphane farklı versiyonlarda:

| Kütüphane | worker | api | Değerlendirme |
| --- | --- | --- | --- |
| pandas | 2.1.3 | 2.3.3 | **Farklı evren** — aynı hesaplamalar iki koddaki numpy 1.26 / 2.5 ile farklı sonuç verebilir |
| numpy | 1.26.4 | 2.5.4 | pandas farkının nedeni |
| openpyxl | 3.1.2 | 3.1.5 | uyumsuz Export/Import paritesi riski |
| bcrypt / passlib | 4.0.1 / 1.7.4 | 4.0.1 / 1.7.4 | passlib 2020'den beri güncel değil |

## 7. Ekosistem sınırları

- Frontend ↔ API: httpOnly cookie (`/api/v1`), `credentials: 'include'`; `NEXT_PUBLIC_API_URL` all-public (harmless). `[observed]` `lib/api.ts`, `lib/auth-api.ts`.
- API ↔ Worker: Celery + Redis broker (`scraping` kuyruğu), task status Redis key'lerinde (`scrape_task:*`). `[observed]` `celery_app.py`, `core/task_status.py`.
- API ↔ DB: SQLAlchemy create_all; Postgres (psycopg2) prod, SQLite default. `[observed]` `database/connection.py`.
- Worker ↔ Go proxy: `GO_PROXY_URL` (compose `http://invisible-proxy:8080`), `PROXY_API_KEY` header. `[observed]` compose `real-estate-worker`.
- Worker ↔ dış web: selenium/undetected-chromedriver, scrapling/patchright (localhost camoufox?), Go uTLS — **üç ayrı yoldan**. `[observed]` `core/driver_manager.py`, `scrapers/*/scrapling_scraper.py`.
- Auth context: backend cookie + frontend `sessionStorage['auth_user']` kopyası (token DEĞİL, sadece profil). `[observed]` `contexts/AuthContext.tsx:20,28`.

## 8. Lens özeti

| Lens | Durum | Özet | Bulgular |
| --- | --- | --- | --- |
| Performans & concurrency | **Sorun** | Sync SQLAlchemy + sync Redis async handler'larda; tek uvicorn worker; N+1; export unbounded | F-05, F-21 |
| Gecikme & cache | Kısmi | React Query staleTime'ları makul; analytics her çağrıda ağır SQL | F-21 |
| Güvenlik | **Sorun** | AuthZ gaps (silme/OK), IDOR, no rate limit, JWT validation noktası, cookie SameSite=None, headers yok, XFF güven, unbounded bodies | F-02..F-05, F-08, F-13, F-19, F-20, F-22, H tablo |
| UX | Sorun | Client-only auth guard; public iken bile homepage 3D yükü (dynamic, yine de ağır) | F-22, F-15 |
| Kaynak verimliliği | Sorun | Worker image: Chrome-for-Testing + Xvfb + playwright chromium + patchright + selenium + scrapling — üstyapı | F-17 |
| Bakım | **Sorun** | İki task kopyası, lock farkları, ölü kod, eslint-config-next 16.0.10 ≠ next 16.4.1, framer-motion+motion ikili | F-12, F-14, F-15 |
| DX | Sorun | CI yok, README stale, pin yok, type-hint var ama coverage gate yok | F-06, F-16 |
| Lisans & uyum | **Sorun** | MIT ilan edilip LICENSE yok; Thordata reklamı; robots yok; ToS | F-01, F-16 |
| Dağıtım & paket | Sorun | Compose dev-tipi; prod Dockerfile (frontend) kullanılmıyor; bind mount; image digest yok | F-10, F-11 |

## 9. Genel bulgu tablosu

| Öncelik | Alan | Mevcut | Bulgular | Karar |
| --- | --- | --- | --- | --- |
| P0 | Hukuk/ürün | Bypass scrape'i ürün çekirdeği | F-01 | adopt + insan kararı |
| P0/P1 | API güvenliği | Register açık + hiç kimseye engel olmadan `DELETE /clear-results` | F-02, F-03, F-04, F-05 | adopt |
| P1 | Ops/Tauri/CI | CI yok; lockfile'lar hash'siz ve platforma gömülü; Python evreni ikiye bölünmüş | F-06, F-12 | adopt |
| P1 | Compose/image | PORT published; Flower 2.0 (2023) + zayıf parola; root API; healthcheck %100 yeşil olsa bile DB kopuk | F-07..F-11 | adopt |
| P2 | Bağımlılık hijyeni | passlib 1.7.4, pandas 2.1.3/2.3.3 farkı, @types prod'da, framer-motion+motion, eslint-config-next mismatch, npm audit 2 prod (fix var) | F-13, F-14, F-23 | adopt |
| P2 | Performans | N+1, sync-on-async, unbounded analytics/export | F-21 | adopt |
| P2 | Veri bütünlüğü | FK-unsafe deletes; Alembic yok; SQLite FK kapalı | F-18 | trial |
| P2 | Frontend güvenlik | CSP/headers yok; client-only guard; middleware yok | F-22 | adopt |
| P3 | Ölü ağırlık | Aurora/ParticleBackground/BlurText/AnimatedList; Go proxy ölü kod; worker'da selenium+patchright+uTLS üçlüsü | F-15, F-17 | adopt/trial |
| P3 | Runtime çağı | Node 22 (2027-04 EOL), Python 3.11 (worker) | F-25 | defer |
| P3 | Lisans/README | MIT iddia ama LICENSE yok; README CLI anlatıyor | F-16 | adopt |

## 10. Detaylı servis code review'ları

> Doğruluk notu: `Celery worker` ve `Frontend` subagent'ları "Free usage limit" ile durduruldu; bu iki servis ana asistan tarafından doğrudan dosya okumasıyla incelendi. Diğer iki servis (Go proxy, FastAPI) subagent raporlarına dayanır; her subagent dosyaları baştan okuyarak satır doğrulaması yaptı ([cevapçı session: ses_e6259a125ffe08681DnOJPnmzo, ses_e6259a121ffeo0h1ddOPEdqeMF]).

### 10.1 Go uTLS proxy (`Backend/go/`, 5 dosya + 3 test + 1 README)

Özet: hepsiemlak.com / emlakjet.com HTTPS hedeflerine, Chrome 120 TLS parmak izini taklit ederek JSON API üzerinden giden, istemci bazında cookie jar tutan, Cloudflare challenge'ını aynı oturumda tekrar deneyen proxy.

| ID | Sınıf | Bulgu |
| --- | --- | --- |
| G-01 | **High** | Parmak izi spoofing + challenge retry → ToS/anti-bot atlatması; README/compose bu niyeti açıkça yazıyor; "educational" disclaimer kodla çelişiyor. `[observed]` `Backend/go/README.md:1-3,7-8,322-335,448`, `config.go:69-73`, compose:22-23 |
| G-02 | **High** | `WriteTimeout` 30s ama istek en fazla 4 deneme × 30s + backoff sürebilir → yanıt write deadline'da kesilir, truncated JSON. `main.go:68-70`, `handler.go:384-443` |
| G-03 | **High** | `client_pool.go:256-279` Shutdown 10 sn sonra dönerken handler'lar hâlâ `Release` çağırabilir; kapalı kanal'a send → **panic**. `handler.go:369-371` |
| G-04 | **High** | POST body sınırsız JSON decode; upstream `io.ReadAll` sınırsız → memory DoS (%33 base64 şişmesi dahil). `handler.go:339,416` → `http.MaxBytesReader` (1–2 MiB) + `io.LimitReader` |
| G-05 | **High** | `X-Forwarded-For` koşulsuz güvenilir; rate limit auth öncesi, IP başına map → saldırgan sınırsız bucket → unauthenticated memory DoS + hedefe flood. `handler.go:242-248,63-93,154` |
| G-06 | **High** | Havuz boşken her istek yeni client+transport; toplam client cap'i yok → FD/conn/memory patlaması. `client_pool.go:159-167,188-253` |
| G-07 | Medium | Havuz dolunca en eski **hâlâ lease'lenmiş** client evict edilip `Client.Jar` değiştiriliyor → data race + cookie kaybı. `client_pool.go:87-92,104-122,146-155` |
| G-08 | Medium | `X-Proxy-Session` çağıran kontrollü, API key'e bağlı değil → oturum devralma. `handler.go:529-536`, `client_pool.go:63-94` |
| G-09 | Medium | `ProxyRequest.Timeout` parse edilip kullanılmıyor; transport hatası ve 403/503'te POST dahil **her şey** retry → non-idempotent duplicate + 4× amplifikasyon. `handler.go:135,320,350-352,363,384-443` |
| G-10 | Medium | `MOBILE_PROXY_URL` parse edilemezse hata yutulur, trafik **doğrudan** çıkar → sunucu IP'si sızar. Startup doğrula / fail-fast. `client_pool.go:216-224` |
| G-11 | Medium | `PROXY_READ_TIMEOUT`, `PROXY_WRITE_TIMEOUT`, `MAX_IDLE_CONNS*`, `IDLE_CONN_TIMEOUT`, `RATE_LIMIT`, `ALLOWED_ORIGINS` ve `USER_AGENT` **okunmuyor veya hardcoded** kullanılır → compose/README tuning'i etkisiz. `config.go:100-181`, `handler.go:118-125`, `main.go:68-70` |
| G-12 | Medium | `PROXY_API_KEY` boş = 401 (README "auth yok" diyor) — compose default boş. İlk `compose up` sonrası /proxy tüm çağrılarda 401; healthcheck yeşil olduğu için farkedilmez. Startup'ta key zorunlu kıl veya açık `ALLOW_NO_AUTH`. `config.go:87`, `handler.go:222-224`, README:163, compose:39 |
| G-13 | Medium | `GoProxyClient.post()` bytes body'yi `json=` ile gönderir → `TypeError` kesin. `go_proxy_client.py:28-29,124-126,195-198` |
| G-14 | Medium | Doküman/testler allowlist dışı `example.com`/`httpbin.org` kullanır; canlı testler `X-API-Key` göndermez → doküman bozuk. `go_proxy_client.py:372`, README:90,207,343, `tests/test_proxy_live.py:25-27` |
| G-15 | Medium | Port 8080 tüm host arayüzlerinde publish; düz HTTP; API key header/query düz metin. `127.0.0.1:8080:8080` bağla veya publish etme; TLS/mTLS. `compose:8-9` |
| G-16 | Medium | Hata yolunda ham `err.Error()` client'a döner; log tam URL; internal adres detayı sızabilir. Generic mesaj + request ID; URL'i redact et. `handler.go:407,411,451` |
| G-17 | Low | Çoklu `Set-Cookie`/`Vary` header'ları yalnız ilk değeriyle akar. `handler.go:503-506` → `map[string][]string` |
| G-18 | Low | API key query param kabul edilir; `==` karşılaştırma → log'a düşer + timing. Sadece header + `subtle.ConstantTimeCompare`. `handler.go:229-236` |
| G-19 | Low | UA map'inde Edge/Safari/random yok; `TLS_ROTATE_LIST` split trim yok. `tls_fingerprint.go:23-38,164-190`, `config.go:138-140` |
| G-20 | Low | `/` health route'u, pool stats, `CreateDialTLSContextFunc`, `getNextClientHelloID`, `GetRandomFingerprint`, `JA3Fingerprint`, `AllowedOrigins` ölü kod; "HTTP/2 enabled" yorumu yanlış (ALPN http/1.1'e sabit). `main.go:107-113`, `client_pool.go:244-245,282-291`, `tls_fingerprint.go:102,119-147,157,193-199`, `config.go:26,47` |
| G-21 | Low | Host allowlist testinde `req.Header.Get("Host")` assertion'ı etkisiz → regresyon testi "yeşil" kalır. `handler_test.go:129` |
| G-22 | Low | Hostname allowlist DNS/IP'yi pinlemiyor → subdomain takeover ile sınırlı SSRF. Çözülen public IP doğrulanmalı; port 443; alt alan politikası. `handler.go:278-307` |

**Go test kapsamı:** sadece saf yardımcılar (config, TLS ID/UA, URL allowlist, auth, rate limiter, session, pool reuse). Retry/timeout/body-limit/shutdown/eviction yolları ve `-race` yok. **İlk 3:** (1) lifecycle ve DoS (deadline+limit+shutdown), (2) edge (XFF, cap'li pool, port bağlama, key zorunluluğu), (3) F-01.

### 10.2 FastAPI API (`Backend/main.py`, `api/`, `auth/`, `database/`, `Dockerfile`)

Özet: cookie-JWT auth'lu, Celery queue'ya scrape task'i atan, sonuçları Postgres/SQLite'tan listeleyen ve Excel export eden API. Async görünür ama içi sync.

| ID | Sınıf | Bulgu |
| --- | --- | --- |
| A-01 | **Critical** | `DELETE /clear-results` sadece "giriş yapmış herhangi bir kullanıcı" ister (router-dep `get_current_user`, `endpoints.py:35`); register public ve `is_admin=False` sabit (`auth/router.py:58,89`). Yani **herhangi bir anonim ziyaretçi register olup tüm ilanları/ fiyat geçmişini/ session'ları/ output dosyalarını silebilir**. `endpoints.py:488-510`. Fix: admin gate + dry-run/onay; `delete_listing_group`/`delete_listing` dahil (`endpoints.py:745-828`) |
| A-02 | **High** | Task'lerde `user_id` yok; `/tasks/{id}`, `/tasks/active`, `/tasks/{id}/cancel` her kullanıcının task'ini okuyup iptal ediyor (IDOR). `endpoints.py:207-239`, `core/task_status.py:127-137,302-318` |
| A-03 | **High** | Dispatch sırası ters: `apply_async` (`endpoints.py:86`) → `create_queued_task` (`endpoints.py:87`). Hızlı worker önce `running` yazar, API sonra `queued` ile ezer → stuck "queued" veya status regresyonu. Önce kaydı yaz, dispatch fail olursa `failed` yap |
| A-04 | **High** | Register/login/scrape-start için rate limit / lockout yok → brute force, account enumeration, queue/resource exhaustion. `main.py:67-83` (sadece CORS), `auth/router.py:58,107`, `endpoints.py:140,169`. Redis-backed limiter (IP+username) + per-user concurrent cap |
| A-05 | **High** | Tüm handler'lar `async def` ama sync SQLAlchemy session + sync Redis (`task_status.py:302-306`) ve `connection.py:39-45` event loop'u bloke eder; `Dockerfile:26` tek uvicorn worker. Handler'ları `def` yap (threadpool) veya async SQLA/redis; pandas export'u thread'e; worker sayısı artır |
| A-06 | **High** | `get_listings` `Listing.location`'ı eager load etmez; `to_dict()` her satırda lazy-load → export `limit=10000` ile **10.000+ ek query** (N+1). `crud.py:396-441,270-275,93-97`, `models.py:113-133`, `endpoints.py:687-713`. `joinedload/selectinload` + streaming CSV/XLSX |
| A-07 | Medium | `page`/`limit` sınırsız; `limit=0` → `ZeroDivisionError`; `page=0` → negatif offset (Postgres 500). `endpoints.py:601-624`, `crud.py:436`. `Query(ge=1, le=200)` |
| A-08 | Medium | Delete yolları FK-safe değil: `price_history.listing_id` non-null, cascade yok; bulk group delete ORM'i bypass → Postgres FK violation; single delete SQLAlchemy NULL yazar → non-null ihlali; `clear_results` orphan `locations` bırakır. `endpoints.py:808,825`, `models.py:96-100,209` |
| A-09 | Medium | Alembic/migration **yok**; startup `create_all` sadece; `init_db.py:11` Postgres'te tanımsız `DATABASE_PATH` import eder → crash; SQLite FK kapalı; nullable unique constraint SQLite'ta duplicate location. `main.py:27-47`, `models.py:40`, `connection.py:25-29` |
| A-10 | Medium | Prod cookie `SameSite=None` + CSRF token yok; `POST /auth/logout`, `POST /tasks/{id}/cancel` body'siz simple request → CSRF ile logout/task cancel. `SameSite=Lax` + double-submit |
| A-11 | Medium | Container'da `__file__` = `/app/api/endpoints.py` → 3 `dirname` `project_root` = `/` → `output_dir=/outputs`; image `/app/outputs` yaratıp compose `./Backend:/app` mount ediyor → **clear_results silme işlemi Docker'da sıfır dosya siler** (sessiz başarısızlık). `endpoints.py:513-518`, `Dockerfile:13`. `core.config.output_dir`/`OUTPUT_DIR` kullan |
| A-12 | Medium | URL'siz listing her scrape'te `create_listing` yoluna düşer → duplicate satırlar; `create_listing`/`get_or_create_location` `IntegrityError`'da `db.rollback()` ile tüm batch'in pending insert'lerini atar. `crud.py:291-298,270-275,93-97`. Natural key + `begin_nested()` savepoint |
| A-13 | Medium | Price/city/stats analytics sınırsız yükleme (50k satır, tüm `Location`, tüm fiyatlar) → yüksek bellek + kocaman response. SQL aggregate + pagination + cache |
| A-14 | Medium | JWT secret sadece token **oluştururken** doğrulanır; app health/healthz'den "gece yarısı" 500 döner; access token 7 gün; logout sadece cookie'yi siler; `JWT_ALGORITHM` allowlist yok. Startup'ta config validate; kısa token + refresh/revocation |
| A-15 | Medium | Şema 100 char şifreye izin verir ama bcrypt ilk **72 byte**'ı kullanır; passlib sessiz keser; çok baytlı Türkçe şifrelerde aynı şifreyi üretir. `schemas.py:11,56` + `requirements-api.txt:7-8`. 72 byte cap veya argon2 |
| A-16 | Medium | Register check-then-insert; `IntegrityError` yakalanmaz → concurrent duplicate 500; username/email ayırt edici mesajlar; login eksik kullanıcıda bcrypt'i atlar → **enumeration**. `auth/router.py:66-93,124`. `IntegrityError` + generic mesaj + dummy hash |
| A-17 | Medium | `/` healthcheck hep 200: DB/Redis kopuk olsa bile compose "healthy"; `clear_results` 500 detayında ham exception (DB internals sızar). `main.py:89-91`, compose:137, `endpoints.py:508-510`. `/health` = DB+Redis |
| A-18 | Low | Container root; `--proxy-headers`/worker yok; `LOG_LEVEL`, `FASTAPI_HOST/PORT`, `DATABASE_PATH` deklare ama yok sayılır; `load_dotenv` yok (python-dotenv var); `get_current_active_admin`, `get_optional_user`, `TokenResponse`, `max_listings`, `aiosqlite` ölü; aiosqlite'ın yorum: "fastapi 0.154 için sync" |

**API test kapsamı:** 21 test dosyası var; API için fiilen `test_task_endpoints.py` (7 test, auth override + FakeRedis) + schema testleri. Listings/analytics/sessions/export/clear-results/auth-dependencies/IDOR/pagination/FK-deletes/CSRF/cookie-flags/Postgres/migration kapsamı YOK; coverage gate yok.

**İlk 3:** (1) A-01 + A-02 (yetki), (2) A-03 (dispatch atomikliği), (3) A-05+A-06+A-07 (event loop + N+1 + input bounds) birlikte — ve A-09 Alembic'e dokunmadan şema değişikliği yok.

### 10.3 Celery worker + scraper'lar (`celery_app.py`, `tasks/`, `scrapers/`, `core/`)

Özet: `scraping` kuyruğunda iki kopya task (`scrape_hepsiemlak`, `scrape_emlakjet`); selenium→undetected-chromedriver→scrapling/patchright→Go uTLS sırasıyla anti-bot stratejisi.

| ID | Sınıf | Bulgu |
| --- | --- | --- |
| W-01 | **High** | robots.txt hiç okunmuyor (`robots` grep'i: sıfır sonuç); `requirements.txt:18` "undetected-chromedriver # Cloudflare, Turnstile bypass"; `core/driver_manager.py:102-114` webdriver stealth yamaları; `scrapers/*/scrapling_scraper.py` `StealthySession(stealthy_headers=True)` + `AsyncStealthySession`; Go proxy'deki uTLS taklidi — **üç bağımsız anti-bot katmanı da korumasız hedefe karşı**. ToS + emek/veri tabanı hakkı (FSEK) riski |
| W-02 | **High** | `driver_manager.py:33-44` `_kill_zombie_chrome()`: `pkill -f chrome` → container dışı paylaşılan host'ta kullanıcının tüm Chrome'unu, container içinde ise **diğer task'in Chrome'unu** öldürür. Concurrency 1 ama yeniden başlatma yolunda kendi driver'ını da keser. Hedef PID grubuna sınırla |
| W-03 | Medium | Aynı ~100 satır iki task arasında kopyalanmış (yeni task eklenirse 3. kopya). Ortak baz scraper sınıfına indir |
| W-04 | Medium | Üç otomasyon yığını tek worker image'ında: Chrome-for-Testing + Xvfb + selenium + undetected + scrapling(patchright/playwright). Image ~GB, soğuk start yüksek, bakım üç kat. **Ölçüp teke indir** (F-17) |
| W-05 | Medium | `emlakjet` task'ında `max_pages` üst sınırsız (API `Query(le=...)` yok); `wait_between_pages=1.5s`, `wait_between_requests=0.3s` → hedef yükü; tespit riski |
| W-06 | Medium | Worker deps'te `flower==2.2.0` kurulmazdan önce `mher/flower` ayrı container'da koşuyor; worker'da flower **kullanılmıyor**; pandas 2.1.3 (numpy 1.26) worker evreni ↔ API 2.3.3 evreni → Excel çıktısı tutarsız parse edilebilir |
| W-07 | Medium | Görev fail olduğunda `raise` (acks_late) → Celery retry/kullanıcının yeniden başlatması yok; sadece UI'dan elle. Transient network için 0 retry; exponential backoff `retry_backoff=True`, `max_retries=2` değerlendirilebilir |
| W-08 | Medium | Redis'te her progress update'te payload (son 40 log dahil) baştan yazılır; loglar Redis'te 24 saat kalır ve URL'ler/fiyatlar içerebilir; `logs` kısmı sınırsız büyümez ama **LOG_FILE'a da yazılır** (`/tmp/scraper-logs` volume'suz) — disk dolması |
| W-09 | Medium | Task status TTL 24h (`TASK_STATUS_TTL_SECONDS=86400`); sonuç backend de aynı; `result_expires=86400` ok. Ancak `get_active_tasks` `SCAN` tüm `scrape_task:*` üzerinde + `GET` her biri → kullanıcı sayısı × task sayısı artınca O(n) hot read. Index key'i (`SET scrape_task:active task_id ...`) daha iyi |
| W-10 | Low | `CHROME_HEADLESS` default `False` + Xvfb (config `core/config.py:71-73`); `.env.example:31` true öneriyor → hangisinde karar verildiği belirsiz; compose `${CHROME_HEADLESS}` boş geçilirse False |
| W-11 | Low | `version_main=145` (undetected) ↔ Dockerfile `CHROME_VERSION=145.0.7632.46` elle senkron; drift-check CI'a eklenmeli |
| W-12 | Low | Live testler (`test_live_smoke`, `test_proxy_live`, `test_live_method_smoke`) internet'e çıkar; CI'da mock yok |

**Worker test kapsamı:** unit (config, parsers, pagination, http_status, task_status_store, validators) makul; Go/dispatch etkileşimi mock'lanmamış; pkill/driver lifecycle test edilmemiş.

**İlk 3:** (1) W-01/F-01 uyum rotası, (2) W-02 pkill sınırı + W-04 teke indirme ölçümü, (3) `max_pages` üst sınırı + retry/backoff.

### 10.4 Frontend (Next.js 16.4.1 + React 19.2.1)

| ID | Sınıf | Bulgu |
| --- | --- | --- |
| E-01 | Medium | **Güvenlik header'ı/CSP yok** — `next.config.ts:1-15` sadece `optimizePackageImports` + `optimizeCss`. Clickjacking/MIME sniff/XSS genişleme; `headers()` ile CSP/frame-ancestors/mime nosniff ekle (F-22) |
| E-02 | Medium | **Guard sadece client-side**; server middleware yok → korumalı HTML/JS herkese ship edilir; `AuthGuard` `useEffect` ile yönlendirir → kısa "flash" ve ilk paint'e kadar veri sızıntısı hissi. `components/auth/AuthGuard.tsx:18-30`, `ClientLayout.tsx:12-49`. `middleware.ts` ile cookie varlığı redirect ekle (token doğrulama backend'de kalır) |
| E-03 | Medium | Auth durumu `sessionStorage['auth_user']`'da JSON profil kopyası (XSS okur; 7 günlük cookie'ye karşı stale). Token değil ama minimum PII saklanmalı; `sessionStorage` yerine sadece `/auth/me` fetch + React Query |
| E-04 | Medium | `lib/api.ts` + `lib/auth-api.ts` ~11 fetch çağrısının hiçbirinde **timeout/AbortSignal yok**; 401 → merkezi logout/redirect yok; base URL 3 dosyada duplike; hata mesajları kullanıcıya ham `detail` |
| E-05 | Medium | **Animation stack iki kez**: `framer-motion` 12 dosyada, **`motion`** (aynı kütüphanenin yeni adı) 3 dosyada (`AnimatedList`, `BlurText`, `CountUp` — `from 'motion/react'`) → aynı bundle iki kez. Birine karar ver |
| E-06 | Medium | `@types/three` ve `@types/d3-geo` **`dependencies`**'te; `@types/node` ^20 ↔ Node 22/24. `@types/*` devDependencies'e taşı |
| E-07 | Low | `eslint-config-next@16.0.10` ↔ `next@16.4.1` uyumsuz; `@typescript/eslint` chain'i 5 high dahil 24 bulgunun kaynağı |
| E-08 | Low | **Ölü bileşenler** (hiçbir yerden import edilmiyor): `Aurora.tsx` (ogl), `ParticleBackground.tsx`, `BlurText.tsx`, `AnimatedList.tsx`; `Hyperspeed.tsx` sadece `/homepage`'de, `FloatingLines.tsx` three + dashboard'da — bundle'da 3D ağırlığı var ama `dynamic({ssr:false})` kullanılıyor (iyi); `app/results/page.tsx` 74 KB tek dosya, bölünmeli |
| E-09 | Low | `tsconfig.target ES2017` Next 16 için eski; `next-env.d.ts` VCS'te; `tsconfig.tsbuildinfo` çalışma ağacında; `Frontend/nul` (Windows artifact); `test-results/` artefaktı |
| E-10 | Low | `e2e/` Playwright var (login + disposable-user) ama `playwright.config.ts:291` → tek browser varsayımı ve CI job yok; `vitest.config.ts` include sadece `*.test.ts`, tsx testleri es geçiliyor |
| E-11 | **High (bağımlılık)** | `npm audit --omit=dev` 2026-11-03: **1 high (source-map-js 1.0.0–1.2.1)** + **1 moderate (fflate 0.8.0–0.8.2)**, ikisi de transitive, `fix=true`; toplam 24 bulgu (19 moderate + 5 high), çoğu eslint/vitest zinciri; eslint 4.0 major bump gerektirir → `npm audit fix` + `eslint-config-next@16.4.x` ile çoğu kapanır |
| E-12 | Low | Env-driven `NEXT_PUBLIC_*_MAX_PAGES=1000` kullanıcıya gösterilir; scraper doğrulaması backend'de tekrar yapılmalı (şu an backend güvenilir) |

**Frontend test:** 7 unit (api/auth-api/datetime/utils/types) + 2 e2e. Component testi yok; bundle budget yok.

**İlk 3:** (1) E-01 + E-02 (header/middleware), (2) E-05 + E-06 (paket hijyeni + audit fix), (3) E-08 (ölü ağırlık temizliği + results bölümleme).

### 10.5 Altyapı / compose / image'lar / secrets

| ID | Sınıf | Bulgu |
| --- | --- | --- |
| I-01 | **High** | **Tüm servis portları 0.0.0.0'da:** Postgres 5432, Redis 6379, proxy 8080, Flower 5555, API 8000, Frontend 3000. LAN/ev ağı erişimine açık; Redis auth'suz, Postgres zayıf varsayım (`postgres/postgres` örnek). `compose:9,77,92,111,191`. `127.0.0.1:...:...` bağla veya prod'da kaldır |
| I-02 | **High** | **Flower**: `mher/flower:2.0` → son push **2023-08-13** ([Docker Hub](https://hub.docker.com/v2/repositories/mher/flower/tags/2.0), 2026-11-03); `mher/flower:2.2.0` 2026-11-02'de taze; lockfile flower==2.2.0. Compose 2.0 kullanıyor + `.env` `FLOWER_BASIC_AUTH` uzunluk 14, placeholder-tipi (zayıf). 2.2.0'a çık, parolayı rotate et |
| I-03 | **High** | Frontend container **dev mode** (`node:22-alpine` + `npm install && npm run dev`, `NODE_ENV=development`, bind mount) — "production" imajı olan hazır `Frontend/Dockerfile` hiçbir yerde kullanılmıyor; build cache'i yok; cold start her seferinde `npm install` |
| I-04 | **High** | **CI yok** — `.github/workflows` yok; her ekosistemde lint/test/typecheck/build/audit sıfır otomatik gate; pin/hashes kontrolü yok; release/versiyonlama manuel |
| I-05 | Medium | **Hash'siz lockfile** (`uv pip compile` `--generate-hashes` olmadan) → supply-chain; ayrıca lockfile'lar Linux/x86_64'e gömülü; `pip-audit -r requirements-api.lock` **Windows'ta `uvloop` build hatasıyla düşüyor** (çıktı: `uvloop does not support Windows at the moment`); macOS/Windows geliştirmede doğrulama mümkün değil |
| I-06 | Medium | Image digest pin yok (`python:3.13-slim`, `node:22-alpine`, `postgres:16-alpine`, `redis:7.4.11-alpine`, `golang:1.27-alpine`, `alpine:3.24`, `mher/flower:2.0`) — tekrarlanabilir build yok |
| I-07 | Medium | `real-estate-api` **root** (Dockerfile'da USER yok); Go proxy **root** (`/root/`); worker non-root (appuser) ✔; compose `real-estate-worker` `security_opt: seccomp:unconfined` (Chrome ihtiyacı) — risk kabulü belgelenmeli |
| I-08 | Medium | Sağlık kontroller: API `/` her zaman 200 (DB yok sayılır); Flower healthcheck yok; frontend servisinde healthcheck yok; proxy worker `invisible-proxy` `service_healthy`'e bağlı — ama proxy `/` yanıtı 2xx olmayabilirse (wget exit) API hiç başlamaz (canlı doğrulanamadı) |
| I-09 | Medium | Compose **`.env`'e implicit bağlı** (`env_file` yok); environment değerleri elle `${VAR}` ile yazılmış; unutulan değişken sessiz boş kalır (`${CHROME_HEADLESS}` gibi); `FASTAPI_HOST`, `LOG_LEVEL` API'ye geçiyor ama uvicorn bunları kullanmıyor (ölü config) |
| I-10 | Medium | Kaynak limit yok: worker Chrome + `--concurrency=1` mem_limit siz → host OOM; `shm_size: 2gb` ✔ ama diğer servislerde limit yok |
| I-11 | Medium | **Backend bind mount** `./Backend:/app` üretim-tipi compose'da — kaynak kod değişikliği anında container'a düşer; imaj tek gerçek kaynak olmalı (override file kullan) |
| I-12 | Low | `real-estate-db` kullanıcısı `postgres`; parolası 16 char (placeholder değil ✔) ama rotate edilmeli; `POSTGRES_USER` compose'da healthcheck için gerekli ✔ |
| I-13 | Low | **gitignore iyi**: `.env`, lockmaker raporlar, `lighthouse*.json`, `gitleaks-report.json` ignore'lu; `.gitnexusignore` tek eşleşme; **.env git geçmişinde hiç yok** (`git log --all -- .env` boş; `-S 'JWT_SECRET_KEY='` 1 commit muhtemelen `.env.example`) |
| I-14 | Low | Working tree'de yok sayılı junk var ama ignore'lu: `gitleaks-report.json` (tek bulgu: `Backend/go/README.md:210` "your-secret-key" örneği — sahte), `lighthouse-login.json`, `Frontend/nul`, `Backend/database/real_estate.db`, `images/` — `git status --ignored` ile temizlenebilir |
| I-15 | **High (doküman/ürün)** | README bypass'u **ürün özelliği** olarak tanıtır; Thordata sponsorluk banner'ı; `README.md:9` "supported by Thordata"; `LICENSE` dosyası yok ("MIT License" iddiası); README "CLI: `pip install selenium pandas openpyxl && python main.py`" — uygulama artık FastAPI+Celery; `CLAUDE.md`=`AGENTS.md` kopyası |

### 10.6 Secret/Artifact hijyen özeti

| Kontrol | Sonuç |
| --- | --- |
| `.env` tracked mi? | Hayır (`[observed] git ls-files` ) — `.env` ignore ✔ |
| `.env` içinde placeholder? | `FLOWER_BASIC_AUTH` uzunluk 14, placeholder-tipi → **zayıf parola kullanılıyor** |
| Repo'da gerçek secret? | `gitleaks-report.json` tek bulgu = dokümandaki örnek key (sahte) |
| Git geçmişinde `.env`? | Yok |
| CI secret yönetimi | CI yok; `FLOWER_BASIC_AUTH`/`JWT_SECRET_KEY` manuel `.env` |
| `.env.example` | Gerçekçi değerler ama zayıf default'lar (`postgres/postgres`, `admin:admin123`, `your-secret-key`) — örneklerde "CHANGE_ME" vurgulanmalı |

## 11. Hızlı kazanımlar ve mimari değişiklikler

**Hızlı kazanımlar (düşük risk, küçük diff, bu raporla birlikte önerilebilir):**
F-02 (admin gate), F-04 (dispatch sırası), F-07 (port bağlama), F-08 (Flower 2.2.0 + parola), F-09 (non-root + `/health`), F-14 (paket hijyeni + audit fix), F-15 (ölü kod), F-16 (README/LICENSE), F-23 (npm audit fix; eslint major'u ayrıca test gerektirir), F-12 (lockfile hashes + `.python-version`).

**Ölçülü trial'lar:** F-17 (üç otomasyon yolunu birine indir — ölçüm: ilk başarılı sayfa başına maliyet/süre), F-18 (Alembic + FK-safe delete; regresyon: mevcut DB üstünde upgrade testi), F-19 (JWT refresh/revoke; frontend değişikliği gerekir).

**Mimari/stratejik:** F-01 (resmi veri rotası — ürün/hukuk kararı). Yeni altyapı yatırımı, bypass'ın kaldırılması netlik kazanmadan yapılmamalı.

**Mimari değişiklik önerilmez:** FastAPI, Celery, Next.js, Postgres, Redis kombinasyonu yük/kullanım için yeterli; hiçbir bulgu "rewrite" gerektirmiyor.

## 12. Önceki audit takibi

İlk audit — takip edilecek önceki öneri yok.

## 13. Lisans özeti

| Ekosistem | Durum | Yükümlülük |
| --- | --- | --- |
| JavaScript | Karışık transitif (dep tree bigint'lere MIT/ISC/Apache/BSD) | notice dosyası önerilir; `next`/`react` MIT ✔ |
| Python | Karışık (MIT/Apache/BSD/PSF + Apache-2.0 `scrapling`) | dağıtılan worker image'ı için NOTICE önerilir |
| Go | `utls` (`refraction-networking/utls` — BSD-3), `zerolog` (MIT) | notice önerilir |
| Ürün | **`LICENSE` dosyası yok**; README "MIT License" diyor; Thordata sponsorluğu beyanı var | LICENSE eklenmeli; sponsorship beyanı sponsorla uyumlu mu kontrol edilmeli |
| İçerik | Hedef sitelerin ilan veritabanı — **FSEK sui generis veritabanı hakkı / sözleşmeye aykırılık** şüphesi | legal review (F-01) |

Bu hukuki tavsiye değildir; uyum kararları yetkin danışmana bırakılmalıdır.

## 14. Doğrulama ve taramalar

| Komut / kontrol | Sonuç | Not |
| --- | --- | --- |
| `git ls-files` salgın taraması (.env, .next, db, cache) | Sadece `.gitnexusignore` eşleşti | Temiz |
| `git status` | 0 uncommitted | Temiz |
| `go vet ./...` (Backend/go) | exit 0 (toolchain go1.27 otomatik indirildi; lokal go 1.26.4) | Ok |
| `npm audit --omit=dev --json` (Frontend) | **2 bulgu** (1 high source-map-js, 1 moderate fflate) | 2026-11-03 registry; transitif; fix var |
| `npm audit --json` (tümü) | 24 bulgu (5 high, 19 moderate); çoğu eslint-config-next 16.0.10 zinciri; `zod`/`vite`/`minimatch`/`brace-expansion`/`js-yaml` kapsar | eslint 4.0 major'u 2026-11-03 itibariyle `isSemVerMajor:true` |
| `npm ls zod vite` | her ikisi de dev zinciri (eslint-config-next, vitest) | Prod dışı |
| `pip-audit -r requirements-api.lock` | **Çalıştırılamadı**: `uvloop does not support Windows at the moment` | Linux CI'da çalıştırılmalı |
| `pip-audit -r requirements.lock` | **Zaman aşımı (>300s)** | Tamamlanamadı; "temiz" SONUCU İDDİA EDİLEMEZ |
| `docker compose ps` | **Docker daemon erişilemez** | Container davranışı (health, port binding) doğrulanamadı |
| Docker image taraması (trivy/hadolint) | araç yok | Skipped — "pass" değil |
| Docker Hub `mher/flower` tag `2.0` | son push 2023-08-13 ✔ kanıtlandı; `2.2.0` 2026-11-02 | Web kaynağı |
| endoflife.date / nextjs.org / nodejs.org fetch | 2026-11-03 | §6 |

## 15. Açık sorular

1. Ürün/hukuk: F-01 için resmi veri rotası araştırılacak mı (EmlakJet/HepsiEmlak partner/API) yoksa proje iptal/yeniden kapsam mı?
2. Dağıtım hedefi nerede? (Tek VPS / gerçek prod / demo) — F-07, F-09, F-10 önceliklerini değiştirir.
3. Multi-tenant auth planlanıyor mu? F-03'ün kapsamı buna bağlı.
4. Scraper'ın hedef portallar için yazılı izni var mı? Yoksa F-01 "hemen dur" seviyesinde.
5. Windows geliştirmede mi kalınacak? pip-audit/lockfile akışı Linux CI gerektiriyor.
6. `pagination`/`listings` endpoint'leri gerçek kullanıcı yükünde mi; export sıklığı ne?
7. Lisans: MIT kesin mi; Thordata sponsorluğu ticari mi?
8. Python 3.14 worker geçişi (F-26) trigger'ı ne? (pandas/scrapling desteği)

## 16. Ek A — Düşük öncelikli gözlemler

| ID | Lens | Gözlem | Öneri |
| --- | --- | --- | --- |
| A-1 | DX | `test_proxy.py` kök dizinde, pytest suite dışında | Backend/tests'e taşı |
| A-2 | DX | `cleanup.ps1`, `subcategories.json`, `ilce_sinirlari.geojson` VCS'ten ignore'lu ama repo kökünde | Sil |
| A-3 | Observability | Yapılandırılmış log yok; `utils/logger` format belirsiz; Sentry/OTEL yok | trial: OTEL exporter |
| A-4 | Observability | Flower tek monitoring; API/worker metrikleri (Prometheus) yok | trial |
| A-5 | UX | `homepage` 3D Hyperspeed (postprocessing) mobilde ağır | `lighthouse` ölçümüyle `low-end` varyant |
| A-6 | UX | Form hata mesajları Türkçe ama tutarsız; 422 `detail` dizi parse var (ok) | i18n dosyası |
| A-7 | Performans | Worker concurrency=1, `task_time_limit=7200` — 2 saatlik "askıda kalan" task riski; soft limit 6900 | progress checkpoint + resume |
| A-8 | Veri | SQLite prod'da kullanılabilir mi? Compose Postgres. İki yol da desteklensin mi? | dokümante et |
| A-9 | Güvenlik | `JWT_SECRET_KEY` uzunluğu 64 ✔ ama `JWT_ALGORITHM` compose'dan geçiyor; allowlist `HS256` | F-19 |
| A-10 | Bakım | `requirements-api.txt` vs `requirements.txt` çiftlemesi; tek kaynak + extra-requirements pattern | küçük refactor |
| A-11 | Doküman | `Backend/go/README.md` tam bypass rehberi; `CONTRIBUTING`, `SECURITY.md` yok | ekle |
| A-12 | Doküman | `README.md:9` Thordata; `images/Thordata-Resim.png` | sponsorluk metnini hukuki gözden geçir |

## 17. Ek B — Reddedilen fikirler

| Fikir | Neden |
| --- | --- |
| Rewrite (başka framework'e geçiş) | Hiçbir bulgu bunu zorunlu kılmıyor; risk > fayda |
| Next.js yerine Remix/SvelteKit | Sorun framework değil, yetki/operasyon |
| Bun'a geçiş | Measured benefit yok; `npm install && npm run dev` zaten problem |
| PostgreSQL → Mongo | İlişkisel veri + analytics; uyumsuz |
| Redis → KeyDB/Valkey | 7.4 destek penceresinde; fayda yok |
| Celery → arq/Dramatiq | Çalışıyor; geçiş maliyeti yüksek; kazanç marjinal |
| Cloudflare bypass'ını "daha iyi" yapmak | İzinsiz/ToS — uygulanmayacak |
| GraphQL | REST + cookie yeterli; N+1 problemi GraphQL'le çözülmez (DataLoader gerekir) |

## 18. Sonuç

Tek cümle: **Yığın çalışıyor; ama yetki açığını ve CI/deployment disiplinini kapatmadan "production" değil, "demo" sayılır — ve bypass temeliyle büyütmek hukuki olarak savunulamaz.** Önce F-01 kararı, sonra F-02..F-12.

---

## Chat özeti

```text
Tech stack audit 1 yazıldı: docs/tech-stack-audit-1-2026-11-03.md
Karar: mimariyi koru, stack'i değiştirme; fakat bypass yerine resmi/lisanslı veri
rotasına geç (F-01 — ürün/hukuk kararı). 7 servisin code review'u raporda.
Critical/High (ilk dalga): A-01 clear-results yetkisiz silme, A-02 IDOR, A-03 dispatch
sırası, A-05 sync-on-async, F-01 bypass, F-06 CI yok, I-01 portlar 0.0.0.0,
I-03 frontend dev-mode container, I-02 Flower 2.0 (2023) + zayıf parola,
G-03..G-06 Go proxy DoS/panic, E-01/E-02 CSP+middleware.
npm audit: 2 prod bulgusu (fix var); pip-audit Windows'ta çalışmadı (uvloop) — Linux CI gerekli.
Hangi maddeleri implement edeyim? (örn. F-02..F-12 + F-14 + F-16)
```
