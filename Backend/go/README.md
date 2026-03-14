# Invisible Go Proxy - Cloudflare Bypass Solution

Advanced proxy server with uTLS fingerprint spoofing for bypassing Cloudflare protection on real estate scraping platforms.

## 🎯 Features

- **TLS Fingerprint Spoofing**: Uses uTLS library to mimic Chrome 120 browser fingerprints
- **Mobile Proxy Support**: Optional mobile/residential proxy integration
- **Connection Pooling**: Reusable HTTP connections for better performance
- **Intelligent Retry Logic**: Exponential backoff for Cloudflare challenges
- **Health Monitoring**: Built-in health checks and logging
- **Python Integration**: Easy-to-use Python client for scraping scripts

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Python        │────▶│  Go Proxy Server │────▶│  Cloudflare        │
│  Scrapling     │     │  (uTLS + Mobile) │     │  Hedef Site        │
│  Scraper       │     │  TLS Spoofing   │     │  (HepsiEmlak)     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                       127.0.0.1:8080           Mobil IP ile çıkış
```

## 📁 Project Structure

```
Backend/
├── go/                          # Go proxy server
│   ├── main.go                 # Server entry point
│   ├── config.go              # Configuration management
│   ├── tls_fingerprint.go     # uTLS parmak izi yönetimi
│   ├── handler.go            # HTTP proxy handler
│   ├── client_pool.go        # Reusable client connections
│   ├── Dockerfile            # Docker build file
│   ├── docker-compose.yml    # Docker Compose configuration
│   └── go.mod                # Go module dependencies
│
├── python_proxy/               # Python integration
│   └── go_proxy_client.py     # Python client for Go proxy
│
└── scrapers/hepsiemlak/
    ├── go_proxy_scraper.py    # HepsiEmlak scraper with Go proxy
    └── scrapling_scraper.py  # Original Scrapling scraper
```

## 🚀 Quick Start

### 1. Start Go Proxy Server (Docker - Recommended)

```bash
# Start the proxy server from project root compose
docker-compose up -d invisible-proxy

# Check logs
docker-compose logs -f invisible-proxy

# Stop the server
docker-compose down invisible-proxy
```

### 2. Start Go Proxy Server (Native Go - Development Only)

```bash
cd Backend/go

# Install dependencies
go mod download

# Run the server
go run main.go

# Or build and run
go build -o invisible-proxy
./invisible-proxy
```

### 3. Test the Proxy Server

```bash
# Test basic connectivity
curl http://127.0.0.1:8080/

# Test proxy with a simple URL
curl "http://127.0.0.1:8080/proxy?url=https://httpbin.org/user-agent"
```

### 4. Use in Python Scraping Scripts

#### Docker Environment (Auto-Detection)
```python
from Backend.python_proxy.go_proxy_client import CloudflareBypassClient
from Backend.scrapers.hepsiemlak.go_proxy_scraper import HepsiemlakGoProxyScraper

# In Docker, proxy URL is auto-detected from environment
# No need to specify proxy_url parameter
proxy_client = CloudflareBypassClient()  # Auto-detects http://invisible-proxy:8080
response = proxy_client.fetch_with_retry("https://www.hepsiemlak.com/istanbul-satilik")

# Full scraper usage (Docker compatible)
scraper = HepsiemlakGoProxyScraper(
    listing_type="kiralik",
    category="konut",
    selected_cities=["Istanbul"],
    selected_districts={"Istanbul": ["Kadikoy"]},
    # proxy_url is auto-detected in Docker
)

result = scraper.start_scraping(max_pages_per_city=2)
scraper.print_summary()
```

#### Local Development
```python
from Backend.python_proxy.go_proxy_client import CloudflareBypassClient
from Backend.scrapers.hepsiemlak.go_proxy_scraper import HepsiemlakGoProxyScraper

# For local development, you can still specify proxy_url
proxy_client = CloudflareBypassClient(proxy_url="http://127.0.0.1:8080")
response = proxy_client.fetch_with_retry("https://www.hepsiemlak.com/istanbul-satilik")

# Or let auto-detection handle it
scraper = HepsiemlakGoProxyScraper(
    listing_type="kiralik",
    category="konut",
    selected_cities=["Istanbul"],
    selected_districts={"Istanbul": ["Kadikoy"]},
)

result = scraper.start_scraping(max_pages_per_city=2)
scraper.print_summary()
```

## ⚙️ Configuration

### Environment Variables

```bash
# Server Settings
PROXY_HOST=0.0.0.0                    # Server bind address
PROXY_PORT=8080                        # Server port
PROXY_READ_TIMEOUT=30                  # Read timeout (seconds)
PROXY_WRITE_TIMEOUT=30                 # Write timeout (seconds)

# Mobile Proxy (Optional)
MOBILE_PROXY_URL=socks5://user:pass@proxy.com:port
MOBILE_PROXY_USER=username
MOBILE_PROXY_PASS=password
USE_MOBILE_PROXY=true

# TLS Fingerprint
TLS_CLIENT_ID=HelloChrome_120           # Chrome version to mimic
USER_AGENT=Mozilla/5.0...             # Custom user agent

# Connection Pool
MAX_IDLE_CONNS=100                     # Max idle connections
MAX_IDLE_CONNS_PER_HOST=10             # Max per host
IDLE_CONN_TIMEOUT=90                   # Idle timeout (seconds)

# Retry Logic
MAX_RETRIES=3                          # Max retry attempts
RETRY_DELAY=1000                       # Retry delay (milliseconds)
DEBUG=false                            # Enable debug logging
```

### TLS Client IDs

Available Chrome fingerprints:
- `HelloChrome_120` (default)
- `HelloChrome_119`
- `HelloChrome_118`
- `HelloChrome_117`
- `HelloChrome_116`
- `HelloChrome_Auto` (automatic detection)
- `HelloFirefox_120`
- `HelloFirefox_117`
- `HelloFirefox_Auto`
- `HelloSafari_16_0`
- `HelloSafari_17_0`

## 🔧 API Endpoints

### GET `/` - Health Check
```bash
curl http://127.0.0.1:8080/
```
Response: `{"status":"ok","service":"invisible-proxy"}`

### GET `/proxy` - Simple Proxy Request
```bash
curl "http://127.0.0.1:8080/proxy?url=https://example.com"
```

### POST `/proxy` - Advanced Proxy Request
```bash
curl -X POST http://127.0.0.1:8080/proxy \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "method": "POST",
    "headers": {
      "X-Custom-Header": "value"
    },
    "body": "request data",
    "timeout": 30
  }'
```

## 📊 Monitoring

### Docker Logs
```bash
# View real-time logs
docker-compose logs -f invisible-proxy

# View last 100 lines
docker-compose logs --tail=100 invisible-proxy
```

### Health Check
```bash
# Check if server is healthy
curl http://127.0.0.1:8080/

# Docker health status
docker ps --filter name=invisible-proxy
```

### Performance Metrics
The proxy server tracks:
- Total requests (successful/failed)
- Cloudflare challenges encountered
- Connection pool usage
- Response times

## 🧪 Testing

### Test Proxy Connection
```bash
cd Backend/python_proxy
python go_proxy_client.py
```

### Test HepsiEmlak Scraper
```bash
cd Backend/scrapers/hepsiemlak
python go_proxy_scraper.py
```

### Performance Benchmark
```bash
# Run performance test
python -c "
from Backend.python_proxy.go_proxy_client import GoProxyClient
import time

client = GoProxyClient()
start = time.time()
response = client.fetch_page('https://httpbin.org/delay/1')
end = time.time()

print(f'Response time: {end - start:.2f}s')
print(f'Status: {response.status}')
print(f'Body length: {len(response.body)} bytes')
"
```

## 🛡️ Security & Best Practices

1. **Mobile Proxy Usage**: Always use residential/mobile proxies for production scraping
2. **Rate Limiting**: Implement delays between requests to avoid detection
3. **Cookie Persistence**: Maintain session cookies for authentication
4. **User Agent Rotation**: Periodically change user agents if needed
5. **Monitoring**: Keep logs of Cloudflare challenges and success rates

## 🐛 Troubleshooting

### Proxy Server Not Starting
```bash
# Check if port 8080 is in use
netstat -an | grep 8080

# Try a different port
docker-compose down
# Edit docker-compose.yml: ports: ["8081:8080"]
docker-compose up -d
```

### Cloudflare Still Detecting Bot
```bash
# 1. Enable mobile proxy
MOBILE_PROXY_URL=socks5://your-mobile-proxy.com:port
MOBILE_PROXY_USER=username
MOBILE_PROXY_PASS=password

# 2. Try different Chrome fingerprint
TLS_CLIENT_ID=HelloFirefox_120

# 3. Increase delays in scraping scripts
time.sleep(random.uniform(2, 5))  # Instead of time.sleep(1)
```

### Python Connection Errors
```bash
# 1. Check if proxy server is running
curl http://127.0.0.1:8080/

# 2. Test proxy with simple request
curl "http://127.0.0.1:8080/proxy?url=https://httpbin.org/get"

# 3. Check Python dependencies
pip install requests beautifulsoup4
```

### Memory Issues
```bash
# Adjust connection pool settings
MAX_IDLE_CONNS=50           # Reduce from 100
MAX_IDLE_CONNS_PER_HOST=5   # Reduce from 10

# Restart Docker container
docker-compose restart
```

## 📈 Performance Tuning

### High-Throughput Configuration
```bash
# In docker-compose.yml
environment:
  - MAX_IDLE_CONNS=200
  - MAX_IDLE_CONNS_PER_HOST=20
  - IDLE_CONN_TIMEOUT=120
  - MAX_RETRIES=5
  - RETRY_DELAY=500
```

### Low-Latency Configuration
```bash
# In docker-compose.yml
environment:
  - PROXY_READ_TIMEOUT=15
  - PROXY_WRITE_TIMEOUT=15
  - MAX_RETRIES=2
  - RETRY_DELAY=500
```

## 🔄 Integration with Existing Scrapers

### Option 1: Replace Scrapling Completely
```python
# Use GoProxyScraper instead of ScraplingScraper
from Backend.scrapers.hepsiemlak.go_proxy_scraper import HepsiemlakGoProxyScraper

scraper = HepsiemlakGoProxyScraper(
    listing_type="kiralik",
    category="konut",
    selected_cities=["Istanbul"],
    proxy_url="http://127.0.0.1:8080",
)
```

### Option 2: Hybrid Approach (Use as Fallback)
```python
from Backend.scrapers.hepsiemlak.scrapling_scraper import HepsiemlakScraplingScraper
from Backend.scrapers.hepsiemlak.go_proxy_scraper import HepsiemlakGoProxyScraper

# Try Scrapling first, fallback to Go Proxy
try:
    scraper = HepsiemlakScraplingScraper(...)
    result = scraper.start_scraping()
except Exception as e:
    print(f"Scrapling failed: {e}, trying Go Proxy...")
    scraper = HepsiemlakGoProxyScraper(...)
    result = scraper.start_scraping()
```

## 📚 Additional Resources

- [uTLS Documentation](https://github.com/refraction-networking/utls)
- [Cloudflare Bypass Techniques](https://github.com/anuraaga/cloudflare-bypass)
- [Python Scraping Best Practices](https://docs.scrapy.org/en/latest/)

## 🤝 Contributing

When adding new features:
1. Update this README with usage examples
2. Add unit tests for new functionality
3. Document any breaking changes
4. Follow the existing code structure

## 📄 License

This project is part of the Real Estate Scraper system. Ensure compliance with target website's terms of service and robots.txt.

## ⚠️ Important Notes

- This tool is for educational and authorized scraping purposes only
- Always respect robots.txt and terms of service
- Implement appropriate rate limiting to avoid server overload
- Use ethical scraping practices
- Mobile proxy usage may incur additional costs

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Docker logs: `docker-compose logs invisible-proxy`
3. Test with simple URLs first before complex scraping
4. Monitor success rates and adjust configuration as needed

---

**Built with Go + uTLS for advanced Cloudflare bypass capabilities** 🛡️
