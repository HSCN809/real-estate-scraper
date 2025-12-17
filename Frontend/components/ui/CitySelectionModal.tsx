'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import TurkeyMap from 'turkey-map-react';
import { X, MapPin, Check, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// Region definitions with city names
const REGIONS: Record<string, string[]> = {
    'Marmara': ['İstanbul', 'Bursa', 'Kocaeli', 'Balıkesir', 'Tekirdağ', 'Sakarya', 'Edirne', 'Kırklareli', 'Çanakkale', 'Yalova', 'Bilecik'],
    'Ege': ['İzmir', 'Aydın', 'Denizli', 'Muğla', 'Manisa', 'Kütahya', 'Afyonkarahisar', 'Uşak'],
    'Akdeniz': ['Antalya', 'Adana', 'Mersin', 'Hatay', 'Kahramanmaraş', 'Osmaniye', 'Isparta', 'Burdur'],
    'İç Anadolu': ['Ankara', 'Konya', 'Kayseri', 'Eskişehir', 'Sivas', 'Yozgat', 'Aksaray', 'Niğde', 'Nevşehir', 'Kırşehir', 'Kırıkkale', 'Karaman', 'Çankırı'],
    'Karadeniz': ['Samsun', 'Trabzon', 'Ordu', 'Zonguldak', 'Tokat', 'Çorum', 'Amasya', 'Giresun', 'Rize', 'Artvin', 'Sinop', 'Kastamonu', 'Bartın', 'Karabük', 'Düzce', 'Bolu', 'Gümüşhane', 'Bayburt'],
    'Doğu Anadolu': ['Erzurum', 'Malatya', 'Elazığ', 'Van', 'Ağrı', 'Erzincan', 'Kars', 'Iğdır', 'Muş', 'Bitlis', 'Bingöl', 'Tunceli', 'Hakkâri', 'Ardahan'],
    'Güneydoğu Anadolu': ['Gaziantep', 'Şanlıurfa', 'Diyarbakır', 'Mardin', 'Batman', 'Siirt', 'Şırnak', 'Adıyaman', 'Kilis'],
};

// City name mapping (plate code to Turkish name)
const CITY_NAMES: Record<string, string> = {
    'Adana': 'Adana', 'Adiyaman': 'Adıyaman', 'Afyon': 'Afyonkarahisar', 'Agri': 'Ağrı',
    'Aksaray': 'Aksaray', 'Amasya': 'Amasya', 'Ankara': 'Ankara', 'Antalya': 'Antalya',
    'Artvin': 'Artvin', 'Aydin': 'Aydın', 'Balikesir': 'Balıkesir', 'Bartin': 'Bartın',
    'Batman': 'Batman', 'Bayburt': 'Bayburt', 'Bilecik': 'Bilecik', 'Bingol': 'Bingöl',
    'Bitlis': 'Bitlis', 'Bolu': 'Bolu', 'Burdur': 'Burdur', 'Bursa': 'Bursa',
    'Canakkale': 'Çanakkale', 'Cankiri': 'Çankırı', 'Corum': 'Çorum', 'Denizli': 'Denizli',
    'Diyarbakir': 'Diyarbakır', 'Duzce': 'Düzce', 'Edirne': 'Edirne', 'Elazig': 'Elazığ',
    'Erzincan': 'Erzincan', 'Erzurum': 'Erzurum', 'Eskisehir': 'Eskişehir', 'Gaziantep': 'Gaziantep',
    'Giresun': 'Giresun', 'Gumushane': 'Gümüşhane', 'Hakkari': 'Hakkâri', 'Hatay': 'Hatay',
    'Igdir': 'Iğdır', 'Isparta': 'Isparta', 'Istanbul': 'İstanbul', 'Izmir': 'İzmir',
    'Kahramanmaras': 'Kahramanmaraş', 'Karabuk': 'Karabük', 'Karaman': 'Karaman', 'Kars': 'Kars',
    'Kastamonu': 'Kastamonu', 'Kayseri': 'Kayseri', 'Kirikkale': 'Kırıkkale', 'Kirklareli': 'Kırklareli',
    'Kirsehir': 'Kırşehir', 'Kilis': 'Kilis', 'Kocaeli': 'Kocaeli', 'Konya': 'Konya',
    'Kutahya': 'Kütahya', 'Malatya': 'Malatya', 'Manisa': 'Manisa', 'Mardin': 'Mardin',
    'Mersin': 'Mersin', 'Mugla': 'Muğla', 'Mus': 'Muş', 'Nevsehir': 'Nevşehir',
    'Nigde': 'Niğde', 'Ordu': 'Ordu', 'Osmaniye': 'Osmaniye', 'Rize': 'Rize',
    'Sakarya': 'Sakarya', 'Samsun': 'Samsun', 'Siirt': 'Siirt', 'Sinop': 'Sinop',
    'Sivas': 'Sivas', 'Sanliurfa': 'Şanlıurfa', 'Sirnak': 'Şırnak', 'Tekirdag': 'Tekirdağ',
    'Tokat': 'Tokat', 'Trabzon': 'Trabzon', 'Tunceli': 'Tunceli', 'Usak': 'Uşak',
    'Van': 'Van', 'Yalova': 'Yalova', 'Yozgat': 'Yozgat', 'Zonguldak': 'Zonguldak',
    'Ardahan': 'Ardahan',
};

interface CitySelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    selectedCities: string[];
    onCitiesChange: (cities: string[]) => void;
}

export function CitySelectionModal({
    isOpen,
    onClose,
    selectedCities,
    onCitiesChange,
}: CitySelectionModalProps) {
    const [hoveredCity, setHoveredCity] = useState<string | null>(null);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    const handleCityClick = (cityData: { name: string }) => {
        const turkishName = CITY_NAMES[cityData.name] || cityData.name;
        if (selectedCities.includes(turkishName)) {
            onCitiesChange(selectedCities.filter(c => c !== turkishName));
        } else {
            onCitiesChange([...selectedCities, turkishName]);
        }
    };

    const handleRegionSelect = (region: string) => {
        const regionCities = REGIONS[region] || [];
        const allSelected = regionCities.every(city => selectedCities.includes(city));

        if (allSelected) {
            // Deselect all cities in region
            onCitiesChange(selectedCities.filter(city => !regionCities.includes(city)));
        } else {
            // Select all cities in region
            const newCities = [...new Set([...selectedCities, ...regionCities])];
            onCitiesChange(newCities);
        }
    };

    const handleSelectAll = () => {
        const allCities = Object.values(CITY_NAMES);
        onCitiesChange(allCities);
    };

    const handleClearAll = () => {
        onCitiesChange([]);
    };

    const isRegionFullySelected = (region: string) => {
        const regionCities = REGIONS[region] || [];
        return regionCities.every(city => selectedCities.includes(city));
    };

    const isRegionPartiallySelected = (region: string) => {
        const regionCities = REGIONS[region] || [];
        return regionCities.some(city => selectedCities.includes(city)) && !isRegionFullySelected(region);
    };

    const cityWrapper = (cityComponent: React.ReactElement, cityData: { name: string }) => {
        const turkishName = CITY_NAMES[cityData.name] || cityData.name;
        const isSelected = selectedCities.includes(turkishName);

        if (isSelected) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const props = cityComponent.props as any;
            return React.cloneElement(cityComponent as React.ReactElement<any>, {
                style: { ...props.style, fill: 'rgba(16, 185, 129, 0.6)', stroke: '#10b981', strokeWidth: '2px' }
            });
        }
        return cityComponent;
    };

    if (!mounted) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    >
                        <div className="w-full max-w-6xl h-[90vh] overflow-auto bg-slate-900 border border-slate-700/50 rounded-2xl shadow-2xl">
                            {/* Header */}
                            <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
                                <div className="flex items-center gap-3">
                                    <MapPin className="w-6 h-6 text-sky-400" />
                                    <h2 className="text-xl font-bold text-white">Şehir Seçimi</h2>
                                    <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-sm font-medium">
                                        {selectedCities.length} şehir seçili
                                    </span>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Region Quick Select */}
                            <div className="p-4 border-b border-slate-700/50">
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        onClick={handleSelectAll}
                                        className="px-4 py-2 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 hover:bg-sky-500/30 transition-colors text-sm font-medium flex items-center gap-2"
                                    >
                                        <Check className="w-4 h-4" />
                                        Tümünü Seç
                                    </button>
                                    <button
                                        onClick={handleClearAll}
                                        className="px-4 py-2 rounded-lg bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30 transition-colors text-sm font-medium flex items-center gap-2"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Temizle
                                    </button>
                                    <div className="w-px bg-slate-700 mx-2" />
                                    {Object.keys(REGIONS).map(region => (
                                        <button
                                            key={region}
                                            onClick={() => handleRegionSelect(region)}
                                            className={cn(
                                                'px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                                                isRegionFullySelected(region)
                                                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                                    : isRegionPartiallySelected(region)
                                                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                                                        : 'bg-slate-800 text-slate-300 border-slate-600 hover:bg-slate-700'
                                            )}
                                        >
                                            {region}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Map Container */}
                            <div className="p-4 flex justify-center">
                                <div className="w-full max-w-4xl">
                                    <TurkeyMap
                                        hoverable={true}
                                        customStyle={{ idleColor: '#334155', hoverColor: '#0ea5e9' }}
                                        onClick={handleCityClick}
                                        showTooltip={true}
                                        cityWrapper={cityWrapper}
                                    />
                                </div>
                            </div>

                            {/* Hover Info */}
                            {hoveredCity && (
                                <div className="px-4 pb-2 text-center">
                                    <span className="text-slate-400">Seçmek için tıklayın: </span>
                                    <span className="text-white font-semibold">{hoveredCity}</span>
                                </div>
                            )}

                            {/* Selected Cities */}
                            {selectedCities.length > 0 && (
                                <div className="p-4 border-t border-slate-700/50">
                                    <p className="text-sm text-slate-400 mb-2">Seçilen Şehirler:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {selectedCities.sort().map(city => (
                                            <span
                                                key={city}
                                                className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-sm"
                                            >
                                                {city}
                                                <button
                                                    onClick={() => onCitiesChange(selectedCities.filter(c => c !== city))}
                                                    className="hover:text-red-400 transition-colors"
                                                >
                                                    <X className="w-3 h-3" />
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Footer */}
                            <div className="p-4 border-t border-slate-700/50 flex justify-end gap-3">
                                <button
                                    onClick={onClose}
                                    className="px-6 py-2 rounded-lg bg-slate-800 text-slate-300 border border-slate-600 hover:bg-slate-700 transition-colors font-medium"
                                >
                                    İptal
                                </button>
                                <button
                                    onClick={onClose}
                                    className="px-6 py-2 rounded-lg bg-sky-500 text-white hover:bg-sky-600 transition-colors font-medium"
                                >
                                    Seçimi Onayla
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>,
        document.body
    );
}
