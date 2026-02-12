# -*- coding: utf-8 -*-
"""SQLAlchemy ORM modelleri"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    ForeignKey, DateTime, Date, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Location(Base):
    """Normalize edilmiş il/ilce/mahalle tablosu"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    il = Column(String(100), nullable=False, index=True)
    ilce = Column(String(100), index=True)
    mahalle = Column(String(200))

    # İlişkiler
    listings = relationship("Listing", back_populates="location")

    __table_args__ = (
        UniqueConstraint('il', 'ilce', 'mahalle', name='uq_location'),
        Index('idx_locations_il_ilce', 'il', 'ilce'),
    )

    def __repr__(self):
        parts = [self.il]
        if self.ilce:
            parts.append(self.ilce)
        if self.mahalle:
            parts.append(self.mahalle)
        return f"<Location({', '.join(parts)})>"


class Listing(Base):
    """Ana ilan tablosu"""
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Temel bilgiler
    baslik = Column(Text, nullable=False)
    fiyat = Column(Float)  # Hesaplamalar için sayısal fiyat
    fiyat_text = Column(String(50))  # Orijinal fiyat metni (ör. "1.500.000 TL")

    # Platform ve Kategori
    platform = Column(String(20), nullable=False, index=True)  # 'emlakjet' / 'hepsiemlak'
    kategori = Column(String(50), nullable=False, index=True)  # 'konut', 'arsa', etc.
    ilan_tipi = Column(String(20), nullable=False, index=True)  # 'satilik' / 'kiralik'
    alt_kategori = Column(String(50))  # 'daire', 'villa', 'tarla', etc.

    # Lokasyon (FK)
    location_id = Column(Integer, ForeignKey("locations.id"), index=True)
    location = relationship("Location", back_populates="listings")

    # İlan detayları
    ilan_url = Column(Text, unique=True)  # Tekrar kontrolü için benzersiz kısıtlama
    ilan_tarihi = Column(Date)
    emlak_ofisi = Column(String(200))
    resim_url = Column(Text)

    # JSON olarak saklanan kategoriye özel detaylar
    details = Column(JSON)

    # Değişiklik tespiti için içerik hash'i (fiyat hariç)
    content_hash = Column(String(32), index=True)  # MD5 hash

    # Meta veriler
    scrape_session_id = Column(Integer, ForeignKey("scrape_sessions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    scrape_session = relationship("ScrapeSession", back_populates="listings")
    price_history = relationship("PriceHistory", back_populates="listing", order_by="desc(PriceHistory.changed_at)")

    __table_args__ = (
        Index('idx_listings_filter', 'platform', 'kategori', 'ilan_tipi', 'location_id'),
        Index('idx_listings_price', 'fiyat'),
        Index('idx_listings_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Listing(id={self.id}, baslik='{self.baslik[:30]}...', fiyat={self.fiyat})>"

    def to_dict(self) -> Dict[str, Any]:
        """API yanıtları için ilanı sözlüğe dönüştür"""
        return {
            "id": self.id,
            "baslik": self.baslik,
            "fiyat": self.fiyat,
            "fiyat_text": self.fiyat_text,
            "platform": self.platform,
            "kategori": self.kategori,
            "ilan_tipi": self.ilan_tipi,
            "alt_kategori": self.alt_kategori,
            "il": self.location.il if self.location else None,
            "ilce": self.location.ilce if self.location else None,
            "mahalle": self.location.mahalle if self.location else None,
            "ilan_url": self.ilan_url,
            "ilan_tarihi": self.ilan_tarihi.isoformat() if self.ilan_tarihi else None,
            "emlak_ofisi": self.emlak_ofisi,
            "resim_url": self.resim_url,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScrapeSession(Base):
    """Tarama oturumu takibi"""
    __tablename__ = "scrape_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tarama parametreleri
    platform = Column(String(20), nullable=False, index=True)
    kategori = Column(String(50), nullable=False)
    ilan_tipi = Column(String(20), nullable=False)
    alt_kategori = Column(String(50))

    # Hedef lokasyonlar (JSON olarak saklanır)
    target_cities = Column(JSON)  # ["Istanbul", "Ankara"]
    target_districts = Column(JSON)  # {"Istanbul": ["Kadikoy", "Besiktas"]}

    # Sonuçlar
    total_listings = Column(Integer, default=0)
    new_listings = Column(Integer, default=0)  # Yeni ilanlar (tekrar olmayanlar)
    duplicate_listings = Column(Integer, default=0)  # Atlanan tekrarlar
    successful_pages = Column(Integer, default=0)
    failed_pages_count = Column(Integer, default=0)

    # Zamanlama
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Durum
    status = Column(String(20), default="running", index=True)  # running, completed, failed, stopped
    error_message = Column(Text)

    # İlişkiler
    listings = relationship("Listing", back_populates="scrape_session")
    failed_page_records = relationship("FailedPage", back_populates="scrape_session")

    __table_args__ = (
        Index('idx_sessions_started', 'started_at'),
    )

    def __repr__(self):
        return f"<ScrapeSession(id={self.id}, platform={self.platform}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """API yanıtları için oturumu sözlüğe dönüştür"""
        return {
            "id": self.id,
            "platform": self.platform,
            "kategori": self.kategori,
            "ilan_tipi": self.ilan_tipi,
            "alt_kategori": self.alt_kategori,
            "target_cities": self.target_cities,
            "target_districts": self.target_districts,
            "total_listings": self.total_listings,
            "new_listings": self.new_listings,
            "duplicate_listings": self.duplicate_listings,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "error_message": self.error_message,
        }


class PriceHistory(Base):
    """İlan fiyat değişikliği geçmişi"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)

    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    price_change = Column(Float)  # new_price - old_price
    price_change_percent = Column(Float)  # ((new - old) / old) * 100

    changed_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    listing = relationship("Listing", back_populates="price_history")

    __table_args__ = (
        Index('idx_price_history_listing', 'listing_id'),
        Index('idx_price_history_changed', 'changed_at'),
    )

    def __repr__(self):
        return f"<PriceHistory(listing_id={self.listing_id}, {self.old_price} -> {self.new_price})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "listing_id": self.listing_id,
            "old_price": self.old_price,
            "new_price": self.new_price,
            "price_change": self.price_change,
            "price_change_percent": self.price_change_percent,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }


class FailedPage(Base):
    """Başarısız sayfa takibi"""
    __tablename__ = "failed_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scrape_session_id = Column(Integer, ForeignKey("scrape_sessions.id"), index=True)

    url = Column(Text, nullable=False)
    page_number = Column(Integer)
    city = Column(String(100))
    district = Column(String(100))

    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    scrape_session = relationship("ScrapeSession", back_populates="failed_page_records")

    __table_args__ = (
        Index('idx_failed_resolved', 'resolved'),
    )

    def __repr__(self):
        return f"<FailedPage(id={self.id}, url='{self.url[:50]}...', resolved={self.resolved})>"


class User(Base):
    """Kullanıcı modeli"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
