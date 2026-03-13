# HepsiEmlak Benchmark Metotlari

Bu klasordeki `simple_comparison.py`, benchmarkta aktif olarak 7 farkli yontemi ayni senaryoda karsilastirir.

## Test Konfigi
- Sehir: `Istanbul`
- Ilan tipi: `kiralik`
- Kategori: `konut`
- Sayfa: `6` (beklenen toplam ~`144` ilan, sayfa basi 24 ise)

## 7 Metot (Kisa Tanim)
1. `Selenium`
   - Klasik Selenium tarayici akisi ile scraping yapar.

2. `Scrapling + StealthySession`
   - Scrapling'in stealth browser modu ile daha guclu anti-bot uyumu hedefler.

3. `Scrapling + FetcherSession (non-stealth)`
   - Scrapling'in HTTP tabanli session akisi, genelde daha hafif ve hizli olur.

4. `Scrapling + DynamicSession`
   - Scrapling'in browser tabanli (dinamik) session'i ile sayfa yukleme yapar.

Spider crawl yapisi:
- Spider, ilk sayfadan (`start_url`) baslar ve sonraki sayfa linklerini otomatik takip eder.
- Boylece tek tek URL yazmadan cok sayfayi duzenli sekilde tarariz; ozellikle pagination olan sitelerde isi kolaylastirir.

5. `Scrapling + Spider + FetcherSession`
   - Spider'in otomatik link takip/kuyruk mantigini, hizli HTTP tabanli session ile birlestirir.

6. `Scrapling + Spider + AsyncDynamicSession`
   - Spider crawl yapisini, JavaScript agir sayfalar icin async dynamic browser session ile kullanir.

7. `Scrapling + Spider + AsyncStealthySession`
   - Spider crawl yapisini, anti-bot direncinin onemli oldugu durumlarda async stealth browser session ile kullanir.

Not:
- Benchmarkta 1-5 arasi yontemler senkron odaklidir.
- 6 ve 7. yontemler Spider tarafinda async session altyapisini kullanir.

## Calistirma
```bash
docker compose exec real-estate-worker sh -lc "cd /app && python scrapers/hepsiemlak/simple_comparison.py"
```

## Ciktilar
- JSON ozet: `Outputs/Comparison/simple_comparison_results.json`
- Excel ozet: `Outputs/Comparison/simple_comparison_summary.xlsx`
- Method bazli Excel detaylar: `Outputs/Comparison/method_details/*.xlsx`
  - Mumkun olan metotlarda ilanlar satir satir yazilir (ornegin 6 sayfa x 24 ise 144 satir).
