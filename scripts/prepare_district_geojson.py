"""
Türkiye İlçe GeoJSON Hazırlama Scripti
Resmi ilçe sınırları GeoJSON dosyasını okuyup il bazında 81 dosyaya böler.
Kaynak: Çevre, Şehircilik ve İklim Değişikliği Bakanlığı
"""

import json
from pathlib import Path
from collections import defaultdict

# İl adı -> dosya adı eşleştirmesi
PROVINCE_TO_FILENAME = {
    "Adana": "adana", "Adıyaman": "adiyaman", "Afyonkarahisar": "afyonkarahisar",
    "Ağrı": "agri", "Aksaray": "aksaray", "Amasya": "amasya", "Ankara": "ankara",
    "Antalya": "antalya", "Ardahan": "ardahan", "Artvin": "artvin", "Aydın": "aydin",
    "Balıkesir": "balikesir", "Bartın": "bartin", "Batman": "batman", "Bayburt": "bayburt",
    "Bilecik": "bilecik", "Bingöl": "bingol", "Bitlis": "bitlis", "Bolu": "bolu",
    "Burdur": "burdur", "Bursa": "bursa", "Çanakkale": "canakkale", "Çankırı": "cankiri",
    "Çorum": "corum", "Denizli": "denizli", "Diyarbakır": "diyarbakir", "Düzce": "duzce",
    "Edirne": "edirne", "Elazığ": "elazig", "Erzincan": "erzincan", "Erzurum": "erzurum",
    "Eskişehir": "eskisehir", "Gaziantep": "gaziantep", "Giresun": "giresun",
    "Gümüşhane": "gumushane", "Hakkâri": "hakkari", "Hakkari": "hakkari", 
    "Hatay": "hatay", "Iğdır": "igdir", "Isparta": "isparta", 
    "İstanbul": "istanbul", "İzmir": "izmir", "Kahramanmaraş": "kahramanmaras", 
    "Karabük": "karabuk", "Karaman": "karaman", "Kars": "kars", "Kastamonu": "kastamonu", 
    "Kayseri": "kayseri", "Kırıkkale": "kirikkale", "Kırklareli": "kirklareli", 
    "Kırşehir": "kirsehir", "Kilis": "kilis", "Kocaeli": "kocaeli", "Konya": "konya",
    "Kütahya": "kutahya", "Malatya": "malatya", "Manisa": "manisa", "Mardin": "mardin",
    "Mersin": "mersin", "Muğla": "mugla", "Muş": "mus", "Nevşehir": "nevsehir",
    "Niğde": "nigde", "Ordu": "ordu", "Osmaniye": "osmaniye", "Rize": "rize",
    "Sakarya": "sakarya", "Samsun": "samsun", "Şanlıurfa": "sanliurfa", "Siirt": "siirt",
    "Sinop": "sinop", "Şırnak": "sirnak", "Sivas": "sivas", "Tekirdağ": "tekirdag",
    "Tokat": "tokat", "Trabzon": "trabzon", "Tunceli": "tunceli", "Uşak": "usak",
    "Van": "van", "Yalova": "yalova", "Yozgat": "yozgat", "Zonguldak": "zonguldak"
}


def split_geojson_by_province(input_file, output_dir):
    """
    GeoJSON'u il bazında dosyalara böl.
    Resmi veride: il_feature_name = İl adı, feature_name = İlçe adı
    """
    print(f"📂 Dosya okunuyor: {input_file}")
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    features = data.get("features", [])
    print(f"📊 Toplam {len(features)} ilçe bulundu")
    
    # İl bazında grupla
    provinces = defaultdict(list)
    unprocessed = []  # İşlenemeyen ilçeler
    
    for feature in features:
        props = feature.get("properties", {})
        province = props.get("il_feature_name") or ""
        district = props.get("feature_name") or ""
        feature_id = props.get("feature_id", "N/A")
        
        province = province.strip() if isinstance(province, str) else ""
        district = district.strip() if isinstance(district, str) else ""
        
        if province:
            # Province adını property'ye de ekle (tutarlılık için)
            feature["properties"]["province"] = province
            provinces[province].append(feature)
        else:
            # İşlenemeyen ilçeyi kaydet
            unprocessed.append({
                "district": district or "Bilinmeyen",
                "feature_id": feature_id,
                "province_raw": props.get("il_feature_name"),
                "all_props": list(props.keys())
            })
    
    # Çıktı dizinini oluştur
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Her il için ayrı dosya oluştur
    index_data = {}
    total_districts = 0
    
    for province in sorted(provinces.keys()):
        feats = provinces[province]
        
        # Dosya adını bul
        filename = PROVINCE_TO_FILENAME.get(province)
        if not filename:
            # Alternatif eşleştirme dene
            for p_name, p_file in PROVINCE_TO_FILENAME.items():
                if p_name.lower() == province.lower():
                    filename = p_file
                    break
        
        if not filename:
            filename = province.lower().replace(" ", "_").replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c").replace("İ", "i")
        
        file_path = output_path / f"{filename}.json"
        
        province_geojson = {
            "type": "FeatureCollection",
            "features": feats
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(province_geojson, f, ensure_ascii=False)
        
        # Index'e ekle
        district_names = sorted(set(f["properties"].get("feature_name", "Bilinmeyen") for f in feats))
        index_data[province] = {
            "file": f"{filename}.json",
            "count": len(feats),
            "districts": district_names
        }
        
        total_districts += len(feats)
        print(f"  ✅ {province}: {len(feats)} ilçe")
    
    # Index dosyasını oluştur
    index_path = output_path / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 Index dosyası: {index_path}")
    print(f"✅ Toplam işlenen ilçe: {total_districts}")
    
    # Debug: İşlenemeyen ilçeleri göster
    if unprocessed:
        print(f"\n⚠️  İşlenemeyen ilçeler: {len(unprocessed)}")
        print("-" * 50)
        for i, item in enumerate(unprocessed[:20]):  # İlk 20'yi göster
            print(f"  {i+1}. {item['district']}")
            print(f"      Feature ID: {item['feature_id']}")
            print(f"      İl (raw): {item['province_raw']}")
            print(f"      Props: {', '.join(item['all_props'][:5])}")
        if len(unprocessed) > 20:
            print(f"  ... ve {len(unprocessed) - 20} ilçe daha")
    else:
        print("\n✅ Tüm ilçeler başarıyla işlendi!")
    
    return index_data


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Yeni resmi dosya
    input_file = script_dir / "ilce_sinirlari.geojson"
    
    # Eski dosya da kabul et (fallback)
    if not input_file.exists():
        input_file = script_dir / "turkey-admin-level-6.geojson"
    
    output_dir = project_root / "Frontend" / "public" / "districts"
    
    print("=" * 60)
    print("🗺️  Türkiye İlçe GeoJSON Hazırlama Scripti")
    print("=" * 60)
    
    if not input_file.exists():
        print(f"❌ Dosya bulunamadı: {input_file}")
        print("   Önce download_ilce_geojson.py çalıştırın.")
        return
    
    print(f"\n📁 Çıktı dizini: {output_dir}")
    index_data = split_geojson_by_province(input_file, output_dir)
    
    print("\n" + "=" * 60)
    print(f"✅ Toplam {len(index_data)} il işlendi")
    print("=" * 60)


if __name__ == "__main__":
    main()
