// Emlak Scraper API tipleri

export interface ScrapeRequest {
  category: string;
  listing_type: string;
  subtype?: string;       // Alt tip ID'si
  subtype_path?: string;  // Alt tip URL path'i
  scraping_method?: HepsiemlakScrapingMethod;
  proxy_enabled?: boolean;
  cities?: string[];
  districts?: Record<string, string[]>;  // İl -> [İlçeler] mapping
  max_pages?: number;           // HepsiEmlak için sayfa limiti
  max_listings?: number;        // EmlakJet için ilan limiti
}

export interface ScrapeStartResponse {
  task_id: string;
  status: 'queued';
  message: string;
}

export type Platform = 'emlakjet' | 'hepsiemlak';

export type ListingType = 'satilik' | 'kiralik';

export type HepsiemlakScrapingMethod =
  | 'selenium'
  | 'scrapling_stealth_session'
  | 'scrapling_fetcher_session'
  | 'scrapling_dynamic_session'
  | 'scrapling_spider_fetcher_session'
  | 'scrapling_spider_dynamic_session'
  | 'scrapling_spider_stealth_session';

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
  date_iso?: string;
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
