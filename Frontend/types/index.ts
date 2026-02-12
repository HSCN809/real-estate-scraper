// Emlak Scraper API tipleri

export interface ScrapeRequest {
  category: string;
  listing_type: string;
  subtype?: string;       // Alt tip ID'si
  subtype_path?: string;  // Alt tip URL path'i
  cities?: string[];
  districts?: Record<string, string[]>;  // İl -> [İlçeler] mapping
  max_pages?: number;           // HepsiEmlak için sayfa limiti
  max_listings?: number;        // EmlakJet için ilan limiti
}

export interface ScrapeResponse {
  status: string;
  message: string;
  data_count: number;
  output_files: string[];
  task_id?: string;  // Celery task ID for tracking
}

export type Platform = 'emlakjet' | 'hepsiemlak';

export type ListingType = 'satilik' | 'kiralik';

export interface Category {
  id: string;
  name: string;
}

export interface ScrapeResult {
  id: string;
  platform: string;
  category: string;
  listing_type?: string;
  subtype?: string;         // Alt kategori adı
  subtype_path?: string;    // Alt kategori path'i
  city?: string;
  district?: string;        // İlçe adı
  date: string;
  count: number;
  avg_price?: number | null;
  file_size?: number;
  file_size_mb?: number;
  status: string;
  files: {
    type: 'excel' | 'json';
    name: string;
    path: string;
  }[];
}

export const CATEGORIES: Record<Platform, Record<ListingType, Category[]>> = {
  emlakjet: {
    satilik: [],
    kiralik: [],
  },
  hepsiemlak: {
    satilik: [],
    kiralik: [],
  },
};


export const TURKISH_CITIES = [
  'Adana', 'Adıyaman', 'Afyonkarahisar', 'Ağrı', 'Aksaray', 'Amasya', 'Ankara', 'Antalya',
  'Artvin', 'Aydın', 'Balıkesir', 'Bartın', 'Batman', 'Bayburt', 'Bilecik', 'Bingöl',
  'Bitlis', 'Bolu', 'Burdur', 'Bursa', 'Çanakkale', 'Çankırı', 'Çorum', 'Denizli',
  'Diyarbakır', 'Düzce', 'Edirne', 'Elazığ', 'Erzincan', 'Erzurum', 'Eskişehir',
  'Gaziantep', 'Giresun', 'Gümüşhane', 'Hakkâri', 'Hatay', 'Iğdır', 'Isparta', 'İstanbul',
  'İzmir', 'Kahramanmaraş', 'Karabük', 'Karaman', 'Kars', 'Kastamonu', 'Kayseri',
  'Kırıkkale', 'Kırklareli', 'Kırşehir', 'Kilis', 'Kocaeli', 'Konya', 'Kütahya', 'Malatya',
  'Manisa', 'Mardin', 'Mersin', 'Muğla', 'Muş', 'Nevşehir', 'Niğde', 'Ordu', 'Osmaniye',
  'Rize', 'Sakarya', 'Samsun', 'Siirt', 'Sinop', 'Sivas', 'Şanlıurfa', 'Şırnak',
  'Tekirdağ', 'Tokat', 'Trabzon', 'Tunceli', 'Uşak', 'Van', 'Yalova', 'Yozgat', 'Zonguldak',
];
