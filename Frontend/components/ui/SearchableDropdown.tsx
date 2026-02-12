'use client';

import { useState, useRef, useEffect } from 'react';
import { Search } from 'lucide-react';

interface SearchableDropdownProps {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
    options: string[];
    placeholder?: string;
    icon?: React.ReactNode;
    focusRingColor?: string;
}

export function SearchableDropdown({
    id,
    label,
    value,
    onChange,
    options,
    placeholder = 'Tümü',
    icon,
    focusRingColor = 'focus:ring-blue-500'
}: SearchableDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Arama metnine göre seçenekleri filtrele
    const filteredOptions = options.filter(opt =>
        opt.toLowerCase().includes(search.toLowerCase())
    );

    // Dışarı tıklama algılama
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setSearch('');
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Dropdown açılınca input'a odaklan
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    const handleSelect = (opt: string) => {
        onChange(opt);
        setIsOpen(false);
        setSearch('');
    };

    const displayValue = value === 'all' ? placeholder : value;

    return (
        <fieldset className="flex flex-col gap-1.5">
            <label htmlFor={id} className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                {icon}
                {label}
            </label>
            <div className="relative" ref={dropdownRef}>
                <button
                    type="button"
                    id={id}
                    onClick={() => setIsOpen(!isOpen)}
                    className={`px-3 py-1.5 text-sm rounded-lg border border-slate-700 bg-slate-800/50 text-gray-300 hover:text-gray-200 appearance-none cursor-pointer min-w-[140px] text-left flex items-center transition-all ${isOpen ? focusRingColor + ' ring-2 border-transparent' : ''}`}
                >
                    <span className={`flex-1 ${value === 'all' ? 'text-gray-400' : ''}`}>{displayValue}</span>
                    <svg className={`w-4 h-4 text-gray-400 transition-transform ml-2 flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {isOpen && (
                    <div className="absolute top-full left-0 mt-1 w-full min-w-[140px] bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
                        {/* Arama Girişi */}
                        <div className="p-2 border-b border-slate-700">
                            <div className="relative">
                                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                                <input
                                    ref={inputRef}
                                    type="text"
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    placeholder="Ara..."
                                    className="w-full pl-7 pr-2 py-1.5 text-sm bg-slate-900/50 border border-slate-600 rounded text-gray-300 placeholder-gray-500 focus:outline-none focus:border-slate-500"
                                />
                            </div>
                        </div>

                        {/* Seçenek Listesi */}
                        <div className="max-h-48 overflow-y-auto">
                            {/* "Tümü" seçeneği */}
                            <button
                                type="button"
                                onClick={() => handleSelect('all')}
                                className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-700 transition-colors ${value === 'all' ? 'bg-slate-700/50 text-white' : 'text-gray-300'}`}
                            >
                                {placeholder}
                            </button>

                            {filteredOptions.length > 0 ? (
                                filteredOptions.map(opt => (
                                    <button
                                        type="button"
                                        key={opt}
                                        onClick={() => handleSelect(opt)}
                                        className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-700 transition-colors ${value === opt ? 'bg-slate-700/50 text-white' : 'text-gray-300'}`}
                                    >
                                        {opt}
                                    </button>
                                ))
                            ) : (
                                <div className="px-3 py-2 text-sm text-gray-500 text-center">
                                    Sonuç bulunamadı
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </fieldset>
    );
}
