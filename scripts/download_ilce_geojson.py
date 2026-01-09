"""
Resmi İlçe Sınırları GeoJSON İndirici
Çevre, Şehircilik ve İklim Değişikliği Bakanlığı'ndan ilçe sınırlarını indirir.
"""

import json
import requests
from pathlib import Path
import urllib3

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Resmi veri kaynağı
GEOJSON_URL = "https://ulasav.csb.gov.tr/dataset/a55b288f-c58d-413e-83ca-969ff88101ee/resource/39bf591e-5bfe-4182-920f-81a8b065862c/download/ilce_sinirlari.geojson"


def download_geojson():
    """GeoJSON dosyasını indir ve kaydet"""
    script_dir = Path(__file__).parent
    output_file = script_dir / "ilce_sinirlari.geojson"
    
    print("=" * 60)
    print("🗺️  Resmi İlçe Sınırları GeoJSON İndirici")
    print("=" * 60)
    print(f"\n📥 URL: {GEOJSON_URL}")
    print("⏳ İndiriliyor...")
    
    try:
        # İndir
        response = requests.get(
            GEOJSON_URL,
            timeout=120,
            verify=False,  # SSL sertifika sorunlarını atla
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        response.raise_for_status()
        
        # JSON olarak parse et (geçerliliği kontrol için)
        print("🔍 JSON geçerliliği kontrol ediliyor...")
        data = response.json()
        
        feature_count = len(data.get('features', []))
        print(f"✅ {feature_count} ilçe bulundu!")
        
        # İlk feature'ı göster
        if feature_count > 0:
            props = data['features'][0].get('properties', {})
            print(f"\n📋 Örnek ilçe özellikleri:")
            for key, value in props.items():
                print(f"   {key}: {value}")
        
        # Dosyaya kaydet
        print(f"\n💾 Kaydediliyor: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        file_size = output_file.stat().st_size / (1024 * 1024)
        print(f"✅ Başarıyla kaydedildi! ({file_size:.2f} MB)")
        
        return output_file
        
    except requests.exceptions.RequestException as e:
        print(f"❌ İndirme hatası: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse hatası: {e}")
        # Raw veriyi de kaydedelim debug için
        raw_file = script_dir / "ilce_sinirlari_raw.txt"
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(response.text[:10000])
        print(f"   Raw veri (ilk 10KB) kaydedildi: {raw_file}")
        return None


if __name__ == "__main__":
    download_geojson()
