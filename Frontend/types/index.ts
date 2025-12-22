// API types for Real Estate Scraper

export interface ScrapeRequest {
  category: string;
  listing_type: string;
  cities?: string[];
  districts?: string[];
  max_pages: number;
}

export interface ScrapeResponse {
  status: string;
  message: string;
  data_count: number;
  output_files: string[];
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
  city?: string;
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
    satilik: [
      { id: 'konut', name: 'Konut' },
      { id: 'arsa', name: 'Arsa' },
      { id: 'isyeri', name: 'İşyeri' },
      { id: 'turistik_tesis', name: 'Turistik Tesis' },
    ],
    kiralik: [
      { id: 'konut', name: 'Konut' },
      { id: 'arsa', name: 'Arsa' },
      { id: 'isyeri', name: 'İşyeri' },
    ],
  },
  hepsiemlak: {
    satilik: [
      { id: 'konut', name: 'Konut' },
      { id: 'arsa', name: 'Arsa' },
      { id: 'isyeri', name: 'İşyeri' },
      { id: 'devremulk', name: 'Devremülk' },
    ],
    kiralik: [
      { id: 'konut', name: 'Konut' },
      { id: 'arsa', name: 'Arsa' },
      { id: 'isyeri', name: 'İşyeri' },
    ],
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
